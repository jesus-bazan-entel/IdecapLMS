"""
AI Studio - Flashcards endpoints
Generate educational flashcards with Gemini AI
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


class FlashcardItem(BaseModel):
    """A single flashcard"""
    id: str
    front: str  # Question or term
    back: str   # Answer or definition
    hint: Optional[str] = None
    category: Optional[str] = None


class FlashcardGenerateRequest(BaseModel):
    """Request to generate flashcards"""
    topic: str
    num_cards: int = 10
    difficulty: str = "intermediate"  # beginner, intermediate, advanced
    language: str = "es"
    include_hints: bool = True
    additional_context: Optional[str] = None
    lesson_id: Optional[str] = None


class FlashcardSetResponse(BaseModel):
    """Flashcard set response"""
    id: str
    title: str
    topic: str
    status: str
    cards: List[FlashcardItem]
    total_cards: int
    difficulty: str
    created_at: datetime
    lesson_id: Optional[str] = None
    error_message: Optional[str] = None


class FlashcardListResponse(BaseModel):
    """List of flashcard sets"""
    flashcard_sets: List[FlashcardSetResponse]
    total: int


def _flashcard_to_response(fc_id: str, data: dict) -> FlashcardSetResponse:
    cards = data.get("cards", [])
    return FlashcardSetResponse(
        id=fc_id,
        title=data.get("title", ""),
        topic=data.get("topic", ""),
        status=data.get("status", "pending"),
        cards=[FlashcardItem(**card) for card in cards],
        total_cards=len(cards),
        difficulty=data.get("difficulty", "intermediate"),
        created_at=data.get("createdAt", datetime.utcnow()),
        lesson_id=data.get("lessonId"),
        error_message=data.get("errorMessage"),
    )


@router.post("/generate", response_model=FlashcardSetResponse)
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Generate flashcards with Gemini AI
    Author or Admin only
    """
    if request.num_cards < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum 3 flashcards required"
        )

    if request.num_cards > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 30 flashcards allowed"
        )

    db = get_firestore()
    fc_id = str(uuid.uuid4())

    # Create initial document
    fc_data = {
        "title": f"Tarjetas: {request.topic[:50]}",
        "topic": request.topic,
        "difficulty": request.difficulty,
        "status": "generating",
        "cards": [],
        "lessonId": request.lesson_id,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
        "errorMessage": None,
    }

    db.collection("generated_flashcards").document(fc_id).set(fc_data)

    try:
        gemini = get_gemini_service()

        difficulty_desc = {
            "beginner": "básico, con conceptos fundamentales y vocabulario simple",
            "intermediate": "intermedio, con conceptos más elaborados",
            "advanced": "avanzado, con conceptos complejos y detalles técnicos"
        }

        hint_line = '"hint": "Pista para recordar",' if request.include_hints else ""
        hint_instruction = 'Incluye un campo "hint" con una pista útil para recordar la respuesta.' if request.include_hints else ""
        context_line = f"Contexto adicional: {request.additional_context}" if request.additional_context else ""
        language_name = "Español" if request.language == "es" else "Português" if request.language == "pt" else request.language

        prompt = f"""Genera exactamente {request.num_cards} tarjetas didácticas (flashcards) sobre el tema: "{request.topic}"

Nivel de dificultad: {difficulty_desc.get(request.difficulty, difficulty_desc['intermediate'])}

{context_line}

Idioma: {language_name}

Formato de respuesta (JSON válido):
{{
  "title": "Título descriptivo del set de tarjetas",
  "cards": [
    {{
      "id": "1",
      "front": "Pregunta o término (lado frontal)",
      "back": "Respuesta o definición (lado posterior)",
      {hint_line}
      "category": "Categoría o tema específico"
    }}
  ]
}}

Instrucciones:
1. Cada tarjeta debe tener un "front" claro y conciso (pregunta o término)
2. El "back" debe ser una respuesta completa pero no demasiado larga
3. {hint_instruction}
4. Agrupa las tarjetas por categorías cuando sea posible
5. Varía el tipo de preguntas: definiciones, ejemplos, comparaciones
6. Asegúrate de que el contenido sea educativo y preciso
7. Para cursos de idiomas, incluye pronunciación cuando sea relevante

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

            cards = result.get("cards", [])
            title = result.get("title", f"Tarjetas: {request.topic[:50]}")

            # Ensure all cards have required fields
            processed_cards = []
            for i, card in enumerate(cards):
                processed_cards.append({
                    "id": card.get("id", str(i + 1)),
                    "front": card.get("front", ""),
                    "back": card.get("back", ""),
                    "hint": card.get("hint"),
                    "category": card.get("category"),
                })

            # Update document with generated content
            db.collection("generated_flashcards").document(fc_id).update({
                "title": title,
                "cards": processed_cards,
                "status": "completed",
                "completedAt": datetime.utcnow(),
            })

            logger.info(f"Generated {len(processed_cards)} flashcards for {fc_id}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse flashcard JSON: {e}")
            db.collection("generated_flashcards").document(fc_id).update({
                "status": "failed",
                "errorMessage": "Error al procesar la respuesta de IA",
            })

    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        db.collection("generated_flashcards").document(fc_id).update({
            "status": "failed",
            "errorMessage": str(e),
        })

    final_data = await get_document("generated_flashcards", fc_id)
    return _flashcard_to_response(fc_id, final_data)


@router.get("", response_model=FlashcardListResponse)
async def list_flashcards(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated flashcard sets
    """
    db = get_firestore()
    query = db.collection("generated_flashcards")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").stream())

    flashcard_sets = [_flashcard_to_response(doc.id, doc.to_dict()) for doc in docs]

    return FlashcardListResponse(
        flashcard_sets=flashcard_sets,
        total=len(flashcard_sets)
    )


@router.get("/{flashcard_id}", response_model=FlashcardSetResponse)
async def get_flashcard_set(
    flashcard_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get flashcard set by ID
    """
    fc_data = await get_document("generated_flashcards", flashcard_id)

    if not fc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard set not found"
        )

    return _flashcard_to_response(flashcard_id, fc_data)


@router.delete("/{flashcard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard_set(
    flashcard_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete flashcard set
    Author or Admin only
    """
    db = get_firestore()
    fc_ref = db.collection("generated_flashcards").document(flashcard_id)
    doc = fc_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard set not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this flashcard set"
        )

    fc_ref.delete()
