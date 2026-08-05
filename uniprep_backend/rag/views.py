from django.db import transaction

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import (
    StudyMaterial,
    DocumentChunk,
    AIChatSession,
    AIChatMessage,
    MaterialSummary,
    GeneratedFlashcard,
    GeneratedQuiz,
    GeneratedQuizQuestion,
    MaterialQuizAttempt,
    MaterialQuizAnswer,
)

from .serializers import (
    StudyMaterialSerializer,
    DocumentChunkSerializer,
    AIChatSessionSerializer,
    AIChatMessageSerializer,
    MaterialSummarySerializer,
    GeneratedFlashcardSerializer,
    GeneratedQuizSerializer,
    GeneratedQuizQuestionSerializer,
)

from .services.text_processor import (
    extract_text_from_pdf,
    extract_text_from_docx,
    chunk_text,
    generate_local_chunk_id,
)

from .services.embedding_service import generate_embedding

from .services.qdrant_service import (
    upsert_chunk_embedding,
    search_similar_chunks
)
from .services.ai_service import (
    InsufficientQuizMaterialError,
    generate_rag_answer,
    generate_flashcards_ai,
    generate_quiz_ai,
    generate_summary_ai,
    generate_summary_map_reduce,
    MAX_SUMMARY_CONTEXT_CHUNKS,
    MIN_SUMMARY_TEXT_LEN,
)


ADMIN_ROLES = {"department_head", "system_admin", "admin"}


def _quiz_viewer_is_privileged(user):
    """Whether the requesting user may see quiz correct answers pre-submit.

    Teachers and admins legitimately preview a generated quiz's correct
    answers (TeacherMaterialDetail quiz preview). Students must NOT see
    them before submitting their attempt, so the spoiler fields are
    stripped from student-facing quiz-fetch / generate responses and only
    revealed by the submit / review endpoints afterwards.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(
        getattr(user, "is_staff", False)
        or getattr(user, "role", "") in ADMIN_ROLES
        or getattr(user, "role", "") == "teacher"
    )


def _serialize_material_quiz_attempt(attempt, include_answers=True):
    """Stable payload shape for the submit and review- attempt endpoints.

    Returns per-question result entries only for questions the student
    actually answered (i.e. rows that exist). Unanswered questions are
    absent from ``answers``; the caller derives them from the full quiz
    question list. ``include_answers`` controls whether ``correct_answer``
    and ``explanation`` are exposed (always True: this payload is the
    post-submission review, so revealing answers is intended).
    """
    answers_payload = []
    for answer in attempt.answers.all().order_by("answered_at"):
        question = answer.question
        entry = {
            "question_id": answer.question_id,
            "selected_answer": answer.selected_answer,
            "is_correct": answer.is_correct,
            "confidence": answer.confidence,
            "answered": True,
            "correct_answer": "",
            "explanation": "",
        }
        if include_answers:
            if question is not None:
                entry["correct_answer"] = question.correct_answer
            entry["explanation"] = answer.explanation_shown
        answers_payload.append(entry)

    return {
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "status": attempt.status,
        "total_score": attempt.total_score,
        "submitted_at": attempt.submitted_at,
        "total_questions": attempt.quiz.questions.count(),
        "correct_count": sum(1 for a in answers_payload if a["is_correct"]),
        "wrong_count": sum(1 for a in answers_payload if not a["is_correct"]),
        "answered_count": len(answers_payload),
        "unanswered_count": attempt.quiz.questions.count() - len(answers_payload),
        "answers": answers_payload,
    }


def invalidate_material_artifacts(material):
    """Hard-invalidates all generated artifacts when a material is re-chunked."""
    MaterialSummary.objects.filter(material=material).delete()
    GeneratedFlashcard.objects.filter(material=material).delete()
    GeneratedQuiz.objects.filter(material=material).delete()
    AIChatSession.objects.filter(material=material).delete()


def create_fallback_flashcards_from_chunks(chunks, count=5):
    flashcards = []

    for chunk in chunks:
        text = chunk.strip()

        if len(text) < 80:
            continue

        flashcards.append({
            "front": f"What is the main idea of this section?",
            "back": text[:500]
        })

        if len(flashcards) >= count:
            break

    return flashcards
def create_fallback_quiz_from_chunks(chunks, count=5):
    quiz_questions = []

    for index, chunk in enumerate(chunks, start=1):
        text = chunk.strip()

        if len(text) < 80:
            continue

        correct_choice = text[:180]

        quiz_questions.append({
            "question_text": f"What is the main idea of section {index}?",
            "choices": [
                correct_choice,
                "This section mainly discusses unrelated historical facts.",
                "This section focuses only on entertainment topics.",
                "This section does not contain academic information."
            ],
            "correct_answer": correct_choice,
            "explanation": "This answer is based on the retrieved section from the uploaded material."
        })

        if len(quiz_questions) >= count:
            break

    return quiz_questions


class StudyMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return StudyMaterial.objects.all()

        return StudyMaterial.objects.filter(owner=user)

    def perform_create(self, serializer):
        user = self.request.user

        # Teachers may publish study materials only for topics assigned to them.
        if getattr(user, "role", None) == "teacher":
            from exit_exams.models import TeacherTopicAssignment
            topic = serializer.validated_data.get("topic")
            if topic is not None and not TeacherTopicAssignment.objects.filter(
                teacher=user, topic=topic, active=True
            ).exists():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    "Teachers can publish study materials only for assigned topics."
                )

        serializer.save(owner=self.request.user)


class DocumentChunkViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentChunkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return DocumentChunk.objects.all()

        return DocumentChunk.objects.filter(material__owner=user)


class AIChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = AIChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return AIChatSession.objects.all()

        return AIChatSession.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class AIChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = AIChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return AIChatMessage.objects.all()

        return AIChatMessage.objects.filter(session__student=user)


class MaterialSummaryViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return MaterialSummary.objects.all()

        return MaterialSummary.objects.filter(material__owner=user)


class GeneratedFlashcardViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedFlashcardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return GeneratedFlashcard.objects.all()

        return GeneratedFlashcard.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class GeneratedQuizViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedQuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return GeneratedQuiz.objects.all()

        return GeneratedQuiz.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class GeneratedQuizQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedQuizQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ADMIN_ROLES:
            return GeneratedQuizQuestion.objects.all()

        return GeneratedQuizQuestion.objects.filter(quiz__student=user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_study_material(request, material_id):
    user = request.user

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not material.file:
        return Response(
            {"detail": "This material has no uploaded file."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    material.processing_status = StudyMaterial.ProcessingStatus.PROCESSING
    material.error_message = ""
    material.save()

    try:
        file_path = material.file.path

        if material.file_type == StudyMaterial.FileType.PDF:
            extracted_text = extract_text_from_pdf(file_path)

        elif material.file_type == StudyMaterial.FileType.DOCX:
            extracted_text = extract_text_from_docx(file_path)

        else:
            material.processing_status = StudyMaterial.ProcessingStatus.FAILED
            material.error_message = "Only PDF and DOCX processing is supported now."
            material.save()

            return Response(
                {"detail": material.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(extracted_text.strip()) < 100:
            material.processing_status = StudyMaterial.ProcessingStatus.FAILED
            material.error_message = (
                "No readable text found. The file may be scanned or empty."
            )
            material.save()

            return Response(
                {"detail": material.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chunks = chunk_text(extracted_text)

        with transaction.atomic():
            DocumentChunk.objects.filter(material=material).delete()
            invalidate_material_artifacts(material)

            for index, chunk in enumerate(chunks, start=1):
                point_id = generate_local_chunk_id()

                document_chunk = DocumentChunk.objects.create(
                    material=material,
                    qdrant_point_id=point_id,
                    chunk_text=chunk,
                    chunk_index=index,
                    page_number=None,
                )

                embedding = generate_embedding(chunk)

                payload = {
                    "owner_id": material.owner.id,
                    "material_id": material.id,
                    "chunk_id": document_chunk.id,
                    "title": material.title,
                    "chunk_index": index,
                    "text": chunk,
                }

                upsert_chunk_embedding(
                    point_id=point_id,
                    vector=embedding,
                    payload=payload,
                )

            material.processing_status = StudyMaterial.ProcessingStatus.COMPLETED
            material.error_message = ""
            material.save()

        return Response(
            {
                "message": "Study material processed successfully.",
                "material_id": material.id,
                "title": material.title,
                "chunks_created": len(chunks),
                "status": material.processing_status,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        material.processing_status = StudyMaterial.ProcessingStatus.FAILED
        material.error_message = str(e)
        material.save()

        return Response(
            {
                "detail": "Processing failed.",
                "error": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def generate_material_summary(request, material_id):
    user = request.user

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        summary = MaterialSummary.objects.filter(material=material).first()
        if summary:
            serializer = MaterialSummarySerializer(summary)
            return Response({"summary": serializer.data}, status=status.HTTP_200_OK)
        return Response({"summary": None}, status=status.HTTP_200_OK)

    if material.processing_status != StudyMaterial.ProcessingStatus.COMPLETED:
        return Response(
            {"detail": "Material must be processed before generating summary."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    chunks = DocumentChunk.objects.filter(
        material=material
    ).order_by("chunk_index")

    if not chunks.exists():
        return Response(
            {"detail": "No chunks found for this material."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Use the FULL document, not just the first few chunks. The previous
    # implementation sliced to chunks[:5], silently dropping everything
    # past ~1-2 pages of source material.
    context_chunks = [chunk.chunk_text for chunk in chunks]

    ai_status = "ai_generated"
    ai_error = None

    summary_text = ""
    key_points = []
    important_terms = []

    try:
        if len(context_chunks) <= MAX_SUMMARY_CONTEXT_CHUNKS:
            result = generate_summary_ai(context_chunks, mode="full")
        else:
            result = generate_summary_map_reduce(context_chunks)

        summary_text = result.get("summary_text", "").strip()
        key_points = result.get("key_points", []) or []
        important_terms = result.get("important_terms", []) or []

        # Simple content validation: non-empty, reasonable length, not a
        # refusal. One retry, then degrade gracefully if still invalid.
        if not summary_text or len(summary_text) < MIN_SUMMARY_TEXT_LEN:
            retry_result = (
                generate_summary_map_reduce(context_chunks)
                if len(context_chunks) > MAX_SUMMARY_CONTEXT_CHUNKS
                else generate_summary_ai(context_chunks, mode="full")
            )
            summary_text = retry_result.get("summary_text", "").strip()
            key_points = retry_result.get("key_points", []) or []
            important_terms = retry_result.get("important_terms", []) or []

            if not summary_text or len(summary_text) < MIN_SUMMARY_TEXT_LEN:
                raise ValueError("Summary too short or empty after retry.")

    except Exception as ai_exception:
        # Graceful fallback: build a clearly-labeled degraded summary
        # from the retrieved chunks themselves, so the endpoint never
        # hard-crashes. Mirrors the ask_material_question fallback shape.
        preview_chunks = context_chunks[:5]
        preview = "\n\n".join(preview_chunks)[:2000]
        summary_text = (
            "An accurate summary could not be generated at this time. "
            "Below is an extract from the beginning of the material.\n\n"
            f"{preview}"
        )
        key_points = []
        important_terms = []
        ai_status = "fallback_from_retrieved_chunks"
        ai_error = str(ai_exception)

    summary, created = MaterialSummary.objects.update_or_create(
        material=material,
        defaults={
            "summary_text": summary_text,
            "key_points": key_points,
            "important_terms": important_terms,
        },
    )

    return Response(
        {
            "message": "Summary generated successfully.",
            "material_id": material.id,
            "title": material.title,
            "ai_status": ai_status,
            "ai_error": ai_error,
            "summary": {
                "id": summary.id,
                "summary_text": summary.summary_text,
                "key_points": summary.key_points,
                "important_terms": summary.important_terms,
                "generated_at": summary.generated_at,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask_material_question(request, material_id):
    user = request.user

    question = request.data.get("question", "").strip()

    if not question:
        return Response(
            {"detail": "Question is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if material.processing_status != StudyMaterial.ProcessingStatus.COMPLETED:
        return Response(
            {"detail": "Material must be processed before asking questions."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        query_embedding = generate_embedding(question)

        search_result = search_similar_chunks(
            query_vector=query_embedding,
            owner_id=material.owner.id,
            material_id=material.id,
            limit=5
        )

        points = getattr(search_result, "points", [])
        MIN_RELEVANCE_SCORE = 0.60

        relevant_points = [
            point for point in points
            if point.score is not None and point.score >= MIN_RELEVANCE_SCORE
        ]


        if not relevant_points:
            return Response(
                {
                    "message": "No relevant answer found.",
                    "material_id": material.id,
                    "question": question,
                    "answer": "I could not find this topic in your uploaded material.",
                    "ai_status": "no_relevant_context",
                    "sources": []
                },
                status=status.HTTP_200_OK
            )

        context_chunks = []
        sources = []

        for point in relevant_points:
            payload = point.payload or {}

            text = payload.get("text", "")

            if text:
                context_chunks.append(text)

            sources.append({
                "chunk_id": payload.get("chunk_id"),
                "chunk_index": payload.get("chunk_index"),
                "title": payload.get("title"),
                "score": point.score,
                "preview": text[:250]
            })

        try:
            answer = generate_rag_answer(
                question=question,
                context_chunks=context_chunks,
            )
            ai_status = "ai_generated"
            ai_error = None

        except Exception as ai_exception:
            top_context = context_chunks[0][:700] if context_chunks else ""
            answer = (
                "AI answer generation is currently unavailable, but relevant material "
                "was found. Based on the retrieved section, this topic is related to:\n\n"
                f"{top_context}\n\n"
                "Check the source previews below for the exact uploaded content."
            )
            ai_status = "fallback_from_retrieved_chunks"
            ai_error = str(ai_exception)

        session, _ = AIChatSession.objects.get_or_create(
            student=user,
            material=material,
            defaults={"title": f"Chat about {material.title}"}
        )

        AIChatMessage.objects.create(
            session=session,
            sender=AIChatMessage.Sender.USER,
            message=question
        )

        AIChatMessage.objects.create(
            session=session,
            sender=AIChatMessage.Sender.AI,
            message=answer
        )

        return Response(
            {
                "message": "Answer generated successfully.",
                "material_id": material.id,
                "chat_session_id": session.id,
                "question": question,
                "answer": answer,
                "ai_status": ai_status,
                "ai_error": ai_error,
                "sources": sources,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "detail": "RAG question answering failed.",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def generate_material_flashcards(request, material_id):
    user = request.user

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        flashcards = GeneratedFlashcard.objects.filter(
            student=user,
            material=material
        ).order_by("-created_at")
        serializer = GeneratedFlashcardSerializer(flashcards, many=True)
        return Response(
            {"flashcards": serializer.data},
            status=status.HTTP_200_OK
        )

    if material.processing_status != StudyMaterial.ProcessingStatus.COMPLETED:
        return Response(
            {"detail": "Material must be processed before generating flashcards."},
            status=status.HTTP_400_BAD_REQUEST
        )

    count = int(request.data.get("count", 5))

    chunks = DocumentChunk.objects.filter(
        material=material
    ).order_by("chunk_index")[:8]

    if not chunks:
        return Response(
            {"detail": "No chunks found for this material."},
            status=status.HTTP_400_BAD_REQUEST
        )

    context_chunks = [chunk.chunk_text for chunk in chunks]

    ai_status = "ai_generated"
    ai_error = None

    try:
        flashcards_data = generate_flashcards_ai(
            context_chunks=context_chunks,
            count=count
        )

    except Exception as e:
        flashcards_data = create_fallback_flashcards_from_chunks(
            chunks=context_chunks,
            count=count
        )
        ai_status = "fallback_generated"
        ai_error = str(e)

    created_flashcards = []

    with transaction.atomic():
        GeneratedFlashcard.objects.filter(
            student=user,
            material=material
        ).delete()

        for item in flashcards_data[:count]:
            front = item.get("front", "").strip()
            back = item.get("back", "").strip()

            if not front or not back:
                continue

            flashcard = GeneratedFlashcard.objects.create(
                student=user,
                material=material,
                front=front,
                back=back,
                difficulty="medium"
            )

            created_flashcards.append({
                "id": flashcard.id,
                "front": flashcard.front,
                "back": flashcard.back,
                "difficulty": flashcard.difficulty
            })

    return Response(
        {
            "message": "Flashcards generated successfully.",
            "material_id": material.id,
            "title": material.title,
            "ai_status": ai_status,
            "ai_error": ai_error,
            "flashcards": created_flashcards
        },
        status=status.HTTP_200_OK
    )
MIN_QUIZ_QUESTION_COUNT = 1
MAX_QUIZ_QUESTION_COUNT = 30
DEFAULT_QUIZ_QUESTION_COUNT = 5

# Maximum number of context chunks fed to the quiz prompt.
MAX_QUIZ_CONTEXT_CHUNKS = 20


class QuizQuestionCountMismatchError(Exception):
    """Internal safety net: stored question count did not match the request."""


def parse_quiz_question_count(raw_value):
    """
    Returns a valid question count, or None if the value is missing/invalid.
    """
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_material_quiz(request, material_id):
    user = request.user

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if material.processing_status != StudyMaterial.ProcessingStatus.COMPLETED:
        return Response(
            {"detail": "Material must be processed before generating quiz."},
            status=status.HTTP_400_BAD_REQUEST
        )

    raw_count = request.data.get(
        "question_count",
        request.data.get("count", DEFAULT_QUIZ_QUESTION_COUNT)
    )
    count = parse_quiz_question_count(raw_count)

    if count is None or not (
        MIN_QUIZ_QUESTION_COUNT <= count <= MAX_QUIZ_QUESTION_COUNT
    ):
        return Response(
            {
                "detail": (
                    f"question_count must be an integer between "
                    f"{MIN_QUIZ_QUESTION_COUNT} and {MAX_QUIZ_QUESTION_COUNT}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Larger requests need more source material to draw distinct
    # questions from; scale the context window with the count.
    chunk_limit = min(max(8, count), MAX_QUIZ_CONTEXT_CHUNKS)

    chunks = DocumentChunk.objects.filter(
        material=material
    ).order_by("chunk_index")[:chunk_limit]

    if not chunks:
        return Response(
            {"detail": "No chunks found for this material."},
            status=status.HTTP_400_BAD_REQUEST
        )

    context_chunks = [chunk.chunk_text for chunk in chunks]

    ai_status = "ai_generated"
    ai_error = None

    try:
        quiz_data = generate_quiz_ai(
            context_chunks=context_chunks,
            count=count
        )

    except InsufficientQuizMaterialError as e:
        return Response(
            {
                "detail": str(e),
                "requested_count": e.requested,
                "supported_count": e.supported,
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        quiz_data = create_fallback_quiz_from_chunks(
            chunks=context_chunks,
            count=count
        )
        ai_status = "fallback_generated"
        ai_error = str(e)

        if len(quiz_data) < count:
            return Response(
                {
                    "detail": (
                        f"AI quiz generation is currently unavailable, and "
                        f"the fallback generator can only produce "
                        f"{len(quiz_data)} question(s) from this material, "
                        f"but {count} were requested. Please try again "
                        f"later or request fewer questions."
                    ),
                    "requested_count": count,
                    "supported_count": len(quiz_data),
                    "ai_status": ai_status,
                    "ai_error": ai_error,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    try:
        with transaction.atomic():
            quiz = GeneratedQuiz.objects.create(
                student=user,
                material=material,
                title=f"Quiz from {material.title}"
            )

            created_questions = []

            for item in quiz_data[:count]:
                question_text = item.get("question_text", "").strip()
                choices = item.get("choices", [])
                correct_answer = item.get("correct_answer", "").strip()
                explanation = item.get("explanation", "").strip()

                if not question_text or not choices or not correct_answer:
                    continue

                if len(choices) != 4:
                    continue

                quiz_question = GeneratedQuizQuestion.objects.create(
                    quiz=quiz,
                    question_text=question_text,
                    choices=choices,
                    correct_answer=correct_answer,
                    explanation=explanation
                )

                question_payload = {
                    "id": quiz_question.id,
                    "question_text": quiz_question.question_text,
                    "choices": quiz_question.choices,
                }
                # Only reveal correct_answer/explanation to privileged
                # viewers (teachers/admins previewing the quiz). Students
                # never see these pre-submit; they are returned by the
                # submit and review endpoints after the attempt is scored.
                if _quiz_viewer_is_privileged(user):
                    question_payload["correct_answer"] = quiz_question.correct_answer
                    question_payload["explanation"] = quiz_question.explanation

                created_questions.append(question_payload)

            if len(created_questions) != count:
                raise QuizQuestionCountMismatchError(
                    f"Expected to store {count} questions, "
                    f"stored {len(created_questions)}."
                )

    except QuizQuestionCountMismatchError as e:
        return Response(
            {
                "detail": (
                    "Failed to generate the exact number of questions "
                    "requested. Please try again."
                ),
                "requested_count": count,
                "ai_error": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            "message": "Quiz generated successfully.",
            "material_id": material.id,
            "title": material.title,
            "quiz_id": quiz.id,
            "requested_count": count,
            "question_count": len(created_questions),
            "ai_status": ai_status,
            "ai_error": ai_error,
            "questions": created_questions
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_material_quiz(request, material_id):
    user = request.user

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    quiz = GeneratedQuiz.objects.filter(
        student=user,
        material=material
    ).order_by("-created_at").first()

    if quiz:
        include_answers = _quiz_viewer_is_privileged(user)
        serializer = GeneratedQuizSerializer(
            quiz,
            context={"include_answers": include_answers}
        )
        data = dict(serializer.data)

        # Attach the student's most recent completed attempt so a reopen
        # shows previous results instead of a blank quiz (mirrors the
        # persisted-artifact pattern used for summaries/flashcards/chat).
        latest_attempt = (
            MaterialQuizAttempt.objects.filter(quiz=quiz, student=user)
            .order_by("-submitted_at")
            .first()
        )
        if latest_attempt is not None:
            data["latest_attempt"] = _serialize_material_quiz_attempt(
                latest_attempt,
                include_answers=True
            )

        return Response(data, status=status.HTTP_200_OK)

    return Response({"quiz": None}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_material_chat(request, material_id):
    user = request.user

    try:
        if user.is_staff or user.role in ADMIN_ROLES:
            material = StudyMaterial.objects.get(id=material_id)
        else:
            material = StudyMaterial.objects.get(id=material_id, owner=user)

    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    session = AIChatSession.objects.filter(
        student=user,
        material=material
    ).order_by("-created_at").first()

    if session:
        messages = [
            {"role": message.sender, "text": message.message}
            for message in session.messages.all()
        ]
        return Response({"messages": messages}, status=status.HTTP_200_OK)

    return Response({"messages": []}, status=status.HTTP_200_OK)


def _resolve_material_for_user(user, material_id):
    """Resolve a StudyMaterial for the requesting user or raise DoesNotExist.

    Privileged viewers (staff / admin roles / teachers) may access any
    material; everyone else only their own.
    """
    if user.is_staff or user.role in ADMIN_ROLES:
        return StudyMaterial.objects.get(id=material_id)
    return StudyMaterial.objects.get(id=material_id, owner=user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_material_quiz(request, material_id):
    """Score a per-material practice quiz attempt authoritatively.

    Request body: { quiz_id, answers: [{ question_id, selected_answer, confidence }] }

    - Scoring is performed server-side by comparing the submitted
      ``selected_answer`` to the stored ``GeneratedQuizQuestion.correct_answer``.
      The frontend's idea of correctness is NOT trusted.
    - A MaterialQuizAnswer row is created ONLY for questions present in the
      submitted ``answers`` array. Skipped questions get no row; an absent row
      means "unanswered" (never a stored "wrong").
    - ``explanation_shown`` is snapshotted from the question at submission time
      so historical attempts survive later quiz regeneration / question edits.
    - The ``question`` FK uses SET_NULL, so regenerating a quiz does not
      silently destroy historical answers.

    total_score is computed as percentage correct out of TOTAL questions in
    the quiz (skipping costs you), consistent with Exit Exam scoring intent.
    Each submission creates a NEW MaterialQuizAttempt (history, not overwrite).
    """
    user = request.user

    try:
        material = _resolve_material_for_user(user, material_id)
    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    quiz_id = request.data.get("quiz_id")
    answers = request.data.get("answers", [])

    if not quiz_id:
        return Response(
            {"detail": "quiz_id is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not isinstance(answers, list):
        return Response(
            {"detail": "answers must be a list."},
            status=status.HTTP_400_BAD_REQUEST
        )

    quiz = None
    try:
        quiz = GeneratedQuiz.objects.get(id=quiz_id, material=material)
    except GeneratedQuiz.DoesNotExist:
        return Response(
            {"detail": "Quiz not found for this material."},
            status=status.HTTP_404_NOT_FOUND
        )

    # A student may only submit their own quiz's attempt. Privileged
    # viewers (teachers/admins) would not submit student quizzes, but we
    # still gate on ownership for safety.
    if quiz.student_id != user.id and not _quiz_viewer_is_privileged(user):
        return Response(
            {"detail": "You do not have permission to submit this quiz."},
            status=status.HTTP_403_FORBIDDEN
        )

    total_questions = quiz.questions.count()

    # Build a lookup of the questions that this quiz actually owns, keyed
    # by id, so submitted answers can be validated and scored.
    own_question_ids = set(quiz.questions.values_list("id", flat=True))

    # MaterialQuizAnswer.unique_together = (attempt, question) -> dedupe
    # any duplicate question_id in the submission to one entry (last wins).
    answers_by_question = {}
    for entry in answers:
        if not isinstance(entry, dict):
            continue
        qid = entry.get("question_id")
        if qid is None:
            continue
        try:
            qid = int(qid)
        except (TypeError, ValueError):
            continue
        if qid not in own_question_ids:
            continue
        selected_answer = entry.get("selected_answer")
        if selected_answer is None:
            selected_answer = ""
        answers_by_question[qid] = {
            "selected_answer": str(selected_answer),
            "confidence": str(entry.get("confidence", "") or ""),
        }

    correct_count = 0

    with transaction.atomic():
        attempt = MaterialQuizAttempt.objects.create(
            quiz=quiz,
            student=user,
            status="completed",
            total_score=0,
        )

        for qid, payload in answers_by_question.items():
            question = GeneratedQuizQuestion.objects.get(id=qid)
            is_correct = payload["selected_answer"] == question.correct_answer
            if is_correct:
                correct_count += 1
            MaterialQuizAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_answer=payload["selected_answer"],
                is_correct=is_correct,
                confidence=payload["confidence"],
                explanation_shown=question.explanation,
            )

        total_score = (
            round((correct_count / total_questions) * 100, 2)
            if total_questions else 0.0
        )
        attempt.total_score = total_score
        attempt.save(update_fields=["total_score"])

    attempt.refresh_from_db()
    return Response(
        _serialize_material_quiz_attempt(attempt, include_answers=True),
        status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_material_quiz_attempt(request, material_id, attempt_id):
    """Return a stored past per-material quiz attempt for review.

    Returns the same shape as the submit endpoint so the frontend can
    render a past attempt's results after the fact. Attempts are stored
    as history; this retrieves a specific attempt by id.
    """
    user = request.user

    try:
        material = _resolve_material_for_user(user, material_id)
    except StudyMaterial.DoesNotExist:
        return Response(
            {"detail": "Study material not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    attempt = (
        MaterialQuizAttempt.objects
        .select_related("quiz", "student")
        .filter(id=attempt_id, quiz__material=material)
        .first()
    )

    if attempt is None:
        return Response(
            {"detail": "Attempt not found for this material."},
            status=status.HTTP_404_NOT_FOUND
        )

    # A student may only review their own attempts; privileged viewers
    # (teachers/admins) may review any attempt on the material.
    if attempt.student_id != user.id and not _quiz_viewer_is_privileged(user):
        return Response(
            {"detail": "You do not have permission to view this attempt."},
            status=status.HTTP_403_FORBIDDEN
        )

    return Response(
        _serialize_material_quiz_attempt(attempt, include_answers=True),
        status=status.HTTP_200_OK
    )
