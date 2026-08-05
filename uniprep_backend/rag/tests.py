import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    DocumentChunk,
    GeneratedQuiz,
    GeneratedQuizQuestion,
    StudyMaterial,
)
from .services.ai_service import (
    InsufficientQuizMaterialError,
    MAX_QUIZ_COUNT_RETRIES,
    generate_quiz_ai,
)

User = get_user_model()

CHUNK_TEXT = (
    "Photosynthesis is the process by which green plants convert sunlight "
    "into chemical energy, producing oxygen and glucose from carbon dioxide "
    "and water inside chloroplasts."
)


def make_quiz_payload(count, prefix="Question"):
    """Builds a JSON string of `count` valid, distinct quiz questions."""
    return json.dumps([
        {
            "question_text": f"{prefix} {index}?",
            "choices": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Because A.",
        }
        for index in range(count)
    ])


class GenerateQuizAIServiceTests(TestCase):
    """Exact-count guarantee tests for generate_quiz_ai()."""

    def setUp(self):
        self.chunks = [CHUNK_TEXT] * 3

    @patch("rag.services.ai_service.call_openrouter")
    def test_exact_count_first_try(self, mock_call):
        mock_call.return_value = make_quiz_payload(5)

        result = generate_quiz_ai(self.chunks, count=5)

        self.assertEqual(len(result), 5)
        self.assertEqual(mock_call.call_count, 1)

    @patch("rag.services.ai_service.call_openrouter")
    def test_over_delivery_is_truncated(self, mock_call):
        mock_call.return_value = make_quiz_payload(12)

        result = generate_quiz_ai(self.chunks, count=10)

        self.assertEqual(len(result), 10)
        self.assertEqual(mock_call.call_count, 1)

    @patch("rag.services.ai_service.call_openrouter")
    def test_under_delivery_triggers_retry_and_tops_up(self, mock_call):
        mock_call.side_effect = [
            make_quiz_payload(3, prefix="First batch"),
            make_quiz_payload(2, prefix="Topup batch"),
        ]

        result = generate_quiz_ai(self.chunks, count=5)

        self.assertEqual(len(result), 5)
        self.assertEqual(mock_call.call_count, 2)

        texts = {item["question_text"] for item in result}
        self.assertEqual(len(texts), 5)

        # The retry prompt must ask for exactly the shortfall (2) and
        # tell the model which questions to avoid repeating.
        retry_prompt = mock_call.call_args_list[1].kwargs["prompt"]
        self.assertIn("EXACTLY 2", retry_prompt)
        self.assertIn("Do NOT repeat", retry_prompt)
        self.assertIn("First batch 0?", retry_prompt)

    @patch("rag.services.ai_service.call_openrouter")
    def test_persistent_under_delivery_raises_clear_error(self, mock_call):
        # Model keeps returning the same 3 questions; dedupe means
        # retries add nothing new.
        mock_call.return_value = make_quiz_payload(3)

        with self.assertRaises(InsufficientQuizMaterialError) as ctx:
            generate_quiz_ai(self.chunks, count=5)

        self.assertEqual(ctx.exception.requested, 5)
        self.assertEqual(ctx.exception.supported, 3)
        self.assertIn("3", str(ctx.exception))
        # 1 initial attempt + MAX_QUIZ_COUNT_RETRIES retries.
        self.assertEqual(mock_call.call_count, 1 + MAX_QUIZ_COUNT_RETRIES)

    @patch("rag.services.ai_service.call_openrouter")
    def test_invalid_items_are_filtered_and_duplicates_dropped(self, mock_call):
        payload = json.dumps([
            {  # valid
                "question_text": "Valid one?",
                "choices": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "x",
            },
            {  # duplicate of the first
                "question_text": "Valid one?",
                "choices": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "x",
            },
            {  # only 3 choices -> invalid
                "question_text": "Bad choices?",
                "choices": ["A", "B", "C"],
                "correct_answer": "A",
                "explanation": "x",
            },
            {  # correct_answer not among choices -> invalid
                "question_text": "Bad answer?",
                "choices": ["A", "B", "C", "D"],
                "correct_answer": "Z",
                "explanation": "x",
            },
            {  # valid
                "question_text": "Valid two?",
                "choices": ["A", "B", "C", "D"],
                "correct_answer": "B",
                "explanation": "x",
            },
        ])
        mock_call.return_value = payload

        with self.assertRaises(InsufficientQuizMaterialError) as ctx:
            generate_quiz_ai(self.chunks, count=3)

        # Only the two valid, distinct questions survive.
        self.assertEqual(ctx.exception.supported, 2)

    @patch("rag.services.ai_service.call_openrouter")
    def test_prompt_states_exact_count(self, mock_call):
        mock_call.return_value = make_quiz_payload(7)

        generate_quiz_ai(self.chunks, count=7)

        prompt = mock_call.call_args_list[0].kwargs["prompt"]
        self.assertIn("EXACTLY 7", prompt)


class GenerateMaterialQuizViewTests(TestCase):
    """End-to-end tests for the generate-quiz endpoint (AI mocked)."""

    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="studentpass123",
            role="student",
        )
        self.material = StudyMaterial.objects.create(
            owner=self.student,
            title="Biology Notes",
            file_type="pdf",
            processing_status=StudyMaterial.ProcessingStatus.COMPLETED,
        )
        self.client.force_authenticate(user=self.student)
        self.url = f"/api/rag/materials/{self.material.id}/generate-quiz/"
        self.quiz_url = f"/api/rag/materials/{self.material.id}/quiz/"

    def _create_chunks(self, count):
        for index in range(count):
            DocumentChunk.objects.create(
                material=self.material,
                qdrant_point_id=f"pt-{self.material.id}-{index}",
                chunk_text=f"{CHUNK_TEXT} (part {index})",
                chunk_index=index,
            )

    def _post_and_assert_exact(self, requested):
        response = self.client.post(self.url, {"question_count": requested})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), requested)
        self.assertEqual(response.data["requested_count"], requested)
        self.assertEqual(response.data["question_count"], requested)

        quiz = GeneratedQuiz.objects.get(id=response.data["quiz_id"])
        self.assertEqual(quiz.questions.count(), requested)
        return quiz

    @patch("rag.services.ai_service.call_openrouter")
    def test_request_5_returns_and_stores_exactly_5(self, mock_call):
        self._create_chunks(8)
        mock_call.return_value = make_quiz_payload(5)

        self._post_and_assert_exact(5)

    @patch("rag.services.ai_service.call_openrouter")
    def test_request_10_returns_and_stores_exactly_10(self, mock_call):
        self._create_chunks(10)
        # Model over-delivers 12; server must truncate to exactly 10.
        mock_call.return_value = make_quiz_payload(12)

        self._post_and_assert_exact(10)

    @patch("rag.services.ai_service.call_openrouter")
    def test_default_count_is_5(self, mock_call):
        self._create_chunks(8)
        mock_call.return_value = make_quiz_payload(5)

        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 5)

    @patch("rag.services.ai_service.call_openrouter")
    def test_short_material_with_high_count_returns_clear_error(
        self, mock_call
    ):
        # Only 3 short chunks; model can only ever produce 3 distinct
        # questions. Requesting 25 must fail clearly, not silently
        # return 3.
        self._create_chunks(3)
        mock_call.return_value = make_quiz_payload(3)

        response = self.client.post(self.url, {"question_count": 25})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["requested_count"], 25)
        self.assertEqual(response.data["supported_count"], 3)
        self.assertIn("3", response.data["detail"])
        self.assertIn("25", response.data["detail"])

        # Nothing should be stored on failure.
        self.assertEqual(GeneratedQuiz.objects.count(), 0)
        self.assertEqual(GeneratedQuizQuestion.objects.count(), 0)

    @patch("rag.services.ai_service.call_openrouter")
    def test_under_delivery_is_retried_until_exact(self, mock_call):
        self._create_chunks(8)
        mock_call.side_effect = [
            make_quiz_payload(4, prefix="First"),
            make_quiz_payload(2, prefix="Topup"),
        ]

        self._post_and_assert_exact(5)
        self.assertEqual(mock_call.call_count, 2)

    def test_invalid_question_counts_are_rejected(self):
        self._create_chunks(8)

        for bad_value in (0, -3, 31, 100, "abc", None):
            response = self.client.post(
                self.url,
                {"question_count": bad_value},
                format="json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                msg=f"question_count={bad_value!r} should be rejected",
            )
            self.assertIn("question_count", response.data["detail"])

        self.assertEqual(GeneratedQuiz.objects.count(), 0)

    @patch("rag.services.ai_service.call_openrouter")
    def test_boundary_count_30_is_accepted(self, mock_call):
        self._create_chunks(20)
        mock_call.return_value = make_quiz_payload(30)

        self._post_and_assert_exact(30)

    @patch("rag.services.ai_service.call_openrouter")
    def test_reopened_quiz_shows_same_count(self, mock_call):
        self._create_chunks(8)
        mock_call.return_value = make_quiz_payload(7)

        self._post_and_assert_exact(7)

        # Reopen the quiz later via the persisted-artifact endpoint.
        response = self.client.get(self.quiz_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 7)

    @patch("rag.services.ai_service.call_openrouter")
    def test_fallback_still_guarantees_exact_count(self, mock_call):
        # AI down entirely; fallback builds one question per chunk.
        self._create_chunks(10)
        mock_call.side_effect = Exception("OpenRouter down")

        response = self.client.post(self.url, {"question_count": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ai_status"], "fallback_generated")
        self.assertEqual(len(response.data["questions"]), 5)
        self.assertEqual(
            GeneratedQuiz.objects.get(
                id=response.data["quiz_id"]
            ).questions.count(),
            5,
        )

    @patch("rag.services.ai_service.call_openrouter")
    def test_fallback_short_material_returns_clear_error(self, mock_call):
        # AI down AND only 3 usable chunks; fallback cannot reach 5.
        self._create_chunks(3)
        mock_call.side_effect = Exception("OpenRouter down")

        response = self.client.post(self.url, {"question_count": 5})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["supported_count"], 3)
        self.assertIn("5", response.data["detail"])
        self.assertEqual(GeneratedQuiz.objects.count(), 0)
