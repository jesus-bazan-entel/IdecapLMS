"""
AI Studio - Quizzes endpoints
Generate educational quizzes with Gemini AI
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import logging
import json

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document, update_document
from app.services.ai.gemini_service import get_gemini_service

router = APIRouter()
logger = logging.getLogger(__name__)


class QuizOption(BaseModel):
    """A quiz answer option"""
    id: str
    text: str
    is_correct: bool


class QuizQuestion(BaseModel):
    """A single quiz question"""
    id: str
    question: str
    type: str  # multiple_choice, true_false, fill_blank
    options: List[QuizOption]
    explanation: Optional[str] = None
    points: int = 1
    category: Optional[str] = None


class QuizGenerateRequest(BaseModel):
    """Request to generate a quiz"""
    topic: str
    num_questions: int = 10
    question_types: List[str] = ["multiple_choice", "true_false"]
    difficulty: str = "intermediate"  # beginner, intermediate, advanced
    language: str = "es"
    include_explanations: bool = True
    additional_context: Optional[str] = None
    lesson_id: Optional[str] = None


class QuizResponse(BaseModel):
    """Quiz response"""
    id: str
    title: str
    topic: str
    status: str
    questions: List[QuizQuestion]
    total_questions: int
    total_points: int
    difficulty: str
    time_limit_minutes: Optional[int] = None
    created_at: datetime
    lesson_id: Optional[str] = None
    error_message: Optional[str] = None


class QuizListResponse(BaseModel):
    """List of quizzes"""
    quizzes: List[QuizResponse]
    total: int


def _quiz_to_response(quiz_id: str, data: dict) -> QuizResponse:
    questions = data.get("questions", [])
    total_points = sum(q.get("points", 1) for q in questions)

    processed_questions = []
    for q in questions:
        options = [QuizOption(**opt) for opt in q.get("options", [])]
        processed_questions.append(QuizQuestion(
            id=q.get("id", ""),
            question=q.get("question", ""),
            type=q.get("type", "multiple_choice"),
            options=options,
            explanation=q.get("explanation"),
            points=q.get("points", 1),
            category=q.get("category"),
        ))

    return QuizResponse(
        id=quiz_id,
        title=data.get("title", ""),
        topic=data.get("topic", ""),
        status=data.get("status", "pending"),
        questions=processed_questions,
        total_questions=len(questions),
        total_points=total_points,
        difficulty=data.get("difficulty", "intermediate"),
        time_limit_minutes=data.get("timeLimitMinutes"),
        created_at=data.get("createdAt", datetime.utcnow()),
        lesson_id=data.get("lessonId"),
        error_message=data.get("errorMessage"),
    )


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Generate a quiz with Gemini AI
    Author or Admin only
    """
    if request.num_questions < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum 3 questions required"
        )

    if request.num_questions > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 30 questions allowed"
        )

    db = get_firestore()
    quiz_id = str(uuid.uuid4())

    # Create initial document
    quiz_data = {
        "title": f"Cuestionario: {request.topic[:50]}",
        "topic": request.topic,
        "difficulty": request.difficulty,
        "status": "generating",
        "questions": [],
        "timeLimitMinutes": request.num_questions * 2,  # 2 min per question
        "lessonId": request.lesson_id,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
        "errorMessage": None,
    }

    db.collection("generated_quizzes").document(quiz_id).set(quiz_data)

    try:
        gemini = get_gemini_service()

        difficulty_desc = {
            "beginner": "básico, con preguntas directas y claras",
            "intermediate": "intermedio, con preguntas que requieren comprensión",
            "advanced": "avanzado, con preguntas de análisis y aplicación"
        }

        type_instructions = []
        if "multiple_choice" in request.question_types:
            type_instructions.append("- Opción múltiple: 4 opciones, solo 1 correcta")
        if "true_false" in request.question_types:
            type_instructions.append("- Verdadero/Falso: 2 opciones")
        if "fill_blank" in request.question_types:
            type_instructions.append("- Completar: Oración con espacio en blanco y opciones")

        explanation_instruction = ""
        explanation_example = ""
        if request.include_explanations:
            explanation_instruction = 'Incluye un campo "explanation" explicando por qué la respuesta es correcta.'
            explanation_example = '"explanation": "Explicación de la respuesta correcta",'

        context_line = f"Contexto adicional: {request.additional_context}" if request.additional_context else ""
        language_name = "Español" if request.language == "es" else "Português" if request.language == "pt" else request.language

        prompt = f"""Genera exactamente {request.num_questions} preguntas de cuestionario sobre el tema: "{request.topic}"

Nivel de dificultad: {difficulty_desc.get(request.difficulty, difficulty_desc['intermediate'])}

Tipos de preguntas a incluir:
{chr(10).join(type_instructions)}

{context_line}

Idioma: {language_name}

Formato de respuesta (JSON válido):
{{
  "title": "Título descriptivo del cuestionario",
  "questions": [
    {{
      "id": "1",
      "question": "Texto de la pregunta",
      "type": "multiple_choice",
      "options": [
        {{"id": "a", "text": "Opción A", "is_correct": false}},
        {{"id": "b", "text": "Opción B", "is_correct": true}},
        {{"id": "c", "text": "Opción C", "is_correct": false}},
        {{"id": "d", "text": "Opción D", "is_correct": false}}
      ],
      {explanation_example}
      "points": 1,
      "category": "Categoría o subtema"
    }}
  ]
}}

Instrucciones:
1. Cada pregunta debe ser clara y sin ambigüedades
2. Para opción múltiple: exactamente 4 opciones, solo 1 correcta
3. Para verdadero/falso: type="true_false", 2 opciones
4. Las opciones incorrectas deben ser plausibles (no obviamente falsas)
5. {explanation_instruction}
6. Varía las categorías cuando sea posible
7. Asigna más puntos (2-3) a preguntas más difíciles
8. Para cursos de idiomas, incluye preguntas de vocabulario, gramática y comprensión

IMPORTANTE: Responde SOLO con el JSON válido, sin texto adicional."""

        response = await gemini.generate_text(prompt)

        # Parse JSON response
        try:
            # Clean the response
            json_text = response.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]

            result = json.loads(json_text.strip())

            questions = result.get("questions", [])
            title = result.get("title", f"Cuestionario: {request.topic[:50]}")

            # Ensure all questions have required fields
            processed_questions = []
            for i, q in enumerate(questions):
                options = q.get("options", [])
                processed_options = []
                for j, opt in enumerate(options):
                    processed_options.append({
                        "id": opt.get("id", chr(97 + j)),  # a, b, c, d
                        "text": opt.get("text", ""),
                        "is_correct": opt.get("is_correct", False),
                    })

                processed_questions.append({
                    "id": q.get("id", str(i + 1)),
                    "question": q.get("question", ""),
                    "type": q.get("type", "multiple_choice"),
                    "options": processed_options,
                    "explanation": q.get("explanation"),
                    "points": q.get("points", 1),
                    "category": q.get("category"),
                })

            # Update document with generated content
            db.collection("generated_quizzes").document(quiz_id).update({
                "title": title,
                "questions": processed_questions,
                "status": "completed",
                "completedAt": datetime.utcnow(),
            })

            logger.info(f"Generated {len(processed_questions)} quiz questions for {quiz_id}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            db.collection("generated_quizzes").document(quiz_id).update({
                "status": "failed",
                "errorMessage": "Error al procesar la respuesta de IA",
            })

    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        db.collection("generated_quizzes").document(quiz_id).update({
            "status": "failed",
            "errorMessage": str(e),
        })

    final_data = await get_document("generated_quizzes", quiz_id)
    return _quiz_to_response(quiz_id, final_data)


@router.get("", response_model=QuizListResponse)
async def list_quizzes(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated quizzes
    """
    db = get_firestore()
    query = db.collection("generated_quizzes")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").stream())

    quizzes = [_quiz_to_response(doc.id, doc.to_dict()) for doc in docs]

    return QuizListResponse(
        quizzes=quizzes,
        total=len(quizzes)
    )


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get quiz by ID
    """
    quiz_data = await get_document("generated_quizzes", quiz_id)

    if not quiz_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    return _quiz_to_response(quiz_id, quiz_data)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete quiz
    Author or Admin only
    """
    db = get_firestore()
    quiz_ref = db.collection("generated_quizzes").document(quiz_id)
    doc = quiz_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this quiz"
        )

    quiz_ref.delete()
