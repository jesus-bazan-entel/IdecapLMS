"""
AI Studio - Presentations endpoints
Generate presentations with AI using Gemini
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import logging

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document, update_document
from app.services.ai.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

router = APIRouter()


class SlideType(str, Enum):
    TITLE = "title"
    CONTENT = "content"
    IMAGE = "image"
    QUOTE = "quote"
    SUMMARY = "summary"


class PresentationStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# Request/Response schemas
class SlideContent(BaseModel):
    """Single slide content"""
    order: int
    title: str
    content: Optional[str] = None
    bullet_points: List[str] = []
    type: SlideType = SlideType.CONTENT
    notes: Optional[str] = None


class PresentationGenerateRequest(BaseModel):
    """Request to generate a presentation"""
    topic: str
    num_slides: int = 10
    language: str = "es"
    additional_context: Optional[str] = None
    lesson_id: Optional[str] = None


class PresentationResponse(BaseModel):
    """Presentation response"""
    id: str
    title: str
    topic: str
    status: str
    slides: List[SlideContent] = []
    created_at: datetime
    lesson_id: Optional[str] = None
    error_message: Optional[str] = None


class PresentationListResponse(BaseModel):
    """List of presentations"""
    presentations: List[PresentationResponse]
    total: int


def _slide_from_dict(data: dict, order: int) -> SlideContent:
    return SlideContent(
        order=data.get("order", order),
        title=data.get("title", ""),
        content=data.get("content"),
        bullet_points=data.get("bulletPoints", data.get("bullet_points", [])),
        type=SlideType(data.get("type", "content")),
        notes=data.get("notes"),
    )


def _presentation_to_response(pres_id: str, data: dict) -> PresentationResponse:
    slides_data = data.get("slides", [])
    slides = [_slide_from_dict(s, i) for i, s in enumerate(slides_data)]

    return PresentationResponse(
        id=pres_id,
        title=data.get("title", ""),
        topic=data.get("topic", ""),
        status=data.get("status", "pending"),
        slides=slides,
        created_at=data.get("createdAt", datetime.utcnow()),
        lesson_id=data.get("lessonId"),
        error_message=data.get("errorMessage"),
    )


@router.post("/generate", response_model=PresentationResponse)
async def generate_presentation(
    request: PresentationGenerateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Generate a presentation with AI (synchronous)
    Author or Admin only
    """
    if request.num_slides < 3 or request.num_slides > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of slides must be between 3 and 20"
        )

    db = get_firestore()
    pres_id = str(uuid.uuid4())

    # Create presentation document
    pres_data = {
        "title": f"Presentación: {request.topic[:50]}",
        "topic": request.topic,
        "numSlides": request.num_slides,
        "language": request.language,
        "additionalContext": request.additional_context,
        "status": PresentationStatus.GENERATING.value,
        "slides": [],
        "lessonId": request.lesson_id,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
    }

    db.collection("presentations").document(pres_id).set(pres_data)
    logger.info(f"Starting presentation generation for {pres_id}: {request.topic}")

    try:
        # Generate slides with Gemini
        gemini = get_gemini_service()
        slides = await gemini.generate_presentation_slides(
            topic=request.topic,
            num_slides=request.num_slides,
            language=request.language,
            additional_context=request.additional_context,
        )

        # Process slides for storage
        processed_slides = []
        for i, slide in enumerate(slides):
            processed_slides.append({
                "order": slide.get("order", i + 1),
                "title": slide.get("title", f"Slide {i + 1}"),
                "content": slide.get("content"),
                "bulletPoints": slide.get("bullet_points", []),
                "type": slide.get("type", "content"),
                "notes": slide.get("notes"),
            })

        # Update document with success
        db.collection("presentations").document(pres_id).update({
            "title": f"Presentación: {request.topic[:50]}",
            "status": PresentationStatus.COMPLETED.value,
            "slides": processed_slides,
            "updatedAt": datetime.utcnow(),
        })

        logger.info(f"Presentation generated successfully for {pres_id}: {len(processed_slides)} slides")

    except Exception as e:
        logger.error(f"Presentation generation failed for {pres_id}: {e}")
        db.collection("presentations").document(pres_id).update({
            "status": PresentationStatus.FAILED.value,
            "errorMessage": str(e),
            "updatedAt": datetime.utcnow(),
        })

    # Return final state
    final_data = await get_document("presentations", pres_id)
    return _presentation_to_response(pres_id, final_data)


@router.get("", response_model=PresentationListResponse)
async def list_presentations(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated presentations
    """
    db = get_firestore()
    query = db.collection("presentations")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").limit(50).stream())

    presentations = [_presentation_to_response(doc.id, doc.to_dict()) for doc in docs]

    return PresentationListResponse(
        presentations=presentations,
        total=len(presentations)
    )


@router.get("/{presentation_id}", response_model=PresentationResponse)
async def get_presentation(
    presentation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get presentation by ID
    """
    pres_data = await get_document("presentations", presentation_id)

    if not pres_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation not found"
        )

    return _presentation_to_response(presentation_id, pres_data)


@router.delete("/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_presentation(
    presentation_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete presentation
    Author or Admin only
    """
    db = get_firestore()
    pres_ref = db.collection("presentations").document(presentation_id)
    doc = pres_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this presentation"
        )

    pres_ref.delete()
