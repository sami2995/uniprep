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
    create_basic_summary,
)

from .services.embedding_service import generate_embedding

from .services.qdrant_service import (
    upsert_chunk_embedding,
    search_similar_chunks
)
from .services.ai_service import (
    generate_rag_answer,
    generate_flashcards_ai,
    generate_quiz_ai,
)


ADMIN_ROLES = {"department_head", "system_admin", "admin"}


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

    combined_text = "\n".join(
        chunk.chunk_text
        for chunk in chunks[:5]
    )

    summary_text = create_basic_summary(combined_text)

    key_points = [
        line.strip()
        for line in summary_text.split(".")
        if len(line.strip()) > 30
    ][:5]

    summary, created = MaterialSummary.objects.update_or_create(
        material=material,
        defaults={
            "summary_text": summary_text,
            "key_points": key_points,
            "important_terms": [],
        },
    )

    return Response(
        {
            "message": "Summary generated successfully.",
            "material_id": material.id,
            "title": material.title,
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
        quiz_data = generate_quiz_ai(
            context_chunks=context_chunks,
            count=count
        )

    except Exception as e:
        quiz_data = create_fallback_quiz_from_chunks(
            chunks=context_chunks,
            count=count
        )
        ai_status = "fallback_generated"
        ai_error = str(e)

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

            created_questions.append({
                "id": quiz_question.id,
                "question_text": quiz_question.question_text,
                "choices": quiz_question.choices,
                "correct_answer": quiz_question.correct_answer,
                "explanation": quiz_question.explanation
            })

    return Response(
        {
            "message": "Quiz generated successfully.",
            "material_id": material.id,
            "title": material.title,
            "quiz_id": quiz.id,
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
        serializer = GeneratedQuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
