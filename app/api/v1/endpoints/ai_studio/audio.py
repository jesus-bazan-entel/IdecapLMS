"""
AI Studio - Audio TTS endpoints
Text-to-Speech generation using edge-tts
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import logging

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document, update_document, upload_file
from app.services.ai.tts_service import get_tts_service, AVAILABLE_VOICES

logger = logging.getLogger(__name__)

router = APIRouter()


class AudioStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# Request/Response schemas
class VoiceInfo(BaseModel):
    id: str
    name: str
    language: str
    gender: str


class AudioGenerateRequest(BaseModel):
    """Request to generate audio from text"""
    text: str
    voice_id: str = "es-ES-Standard-A"
    speed: float = 1.0  # 0.5 to 2.0
    pitch: float = 0.0  # -20.0 to 20.0
    title: Optional[str] = None
    lesson_id: Optional[str] = None


class AudioResponse(BaseModel):
    """Generated audio response"""
    id: str
    title: Optional[str] = None
    text: str
    voice_id: str
    voice_name: str
    status: str
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime
    lesson_id: Optional[str] = None
    error_message: Optional[str] = None


class AudioListResponse(BaseModel):
    """List of generated audios"""
    audios: List[AudioResponse]
    total: int


def _get_voice_info(voice_id: str) -> dict:
    """Get voice info from available voices"""
    for v in AVAILABLE_VOICES:
        if v["id"] == voice_id:
            return v
    return AVAILABLE_VOICES[0]


def _audio_to_response(audio_id: str, data: dict) -> AudioResponse:
    voice_id = data.get("voiceId", "es-ES-Standard-A")
    voice_info = _get_voice_info(voice_id)

    return AudioResponse(
        id=audio_id,
        title=data.get("title"),
        text=data.get("text", ""),
        voice_id=voice_id,
        voice_name=voice_info["name"],
        status=data.get("status", "pending"),
        audio_url=data.get("audioUrl"),
        duration_seconds=data.get("durationSeconds"),
        created_at=data.get("createdAt", datetime.utcnow()),
        lesson_id=data.get("lessonId"),
        error_message=data.get("errorMessage"),
    )


@router.get("/voices", response_model=List[VoiceInfo])
async def list_voices(
    language: Optional[str] = None,
    gender: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List available TTS voices
    """
    voices = AVAILABLE_VOICES

    if language:
        voices = [v for v in voices if language in v["language"]]

    if gender:
        voices = [v for v in voices if v["gender"] == gender]

    return [VoiceInfo(
        id=v["id"],
        name=v["name"],
        language=v["language"],
        gender=v["gender"]
    ) for v in voices]


@router.post("/generate", response_model=AudioResponse)
async def generate_audio(
    request: AudioGenerateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Generate audio from text using TTS (synchronous)
    Author or Admin only
    """
    # Validate voice
    voice_info = _get_voice_info(request.voice_id)

    # Validate text length
    if len(request.text) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text exceeds maximum length of 5000 characters"
        )

    if len(request.text.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty"
        )

    db = get_firestore()
    audio_id = str(uuid.uuid4())

    # Create audio document
    audio_data = {
        "title": request.title or f"Audio {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        "text": request.text,
        "voiceId": request.voice_id,
        "speed": request.speed,
        "pitch": request.pitch,
        "status": AudioStatus.GENERATING.value,
        "audioUrl": None,
        "durationSeconds": None,
        "lessonId": request.lesson_id,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
    }

    db.collection("generated_audio").document(audio_id).set(audio_data)
    logger.info(f"Starting audio generation for {audio_id}: {len(request.text)} chars")

    try:
        # Generate audio using TTS service
        tts = get_tts_service()
        audio_content = await tts.generate_audio(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed,
            pitch=request.pitch,
        )

        # Estimate duration
        duration = tts.estimate_duration(request.text, request.speed)

        # Upload to Firebase Storage
        audio_path = f"audio/{audio_id}.mp3"
        audio_url = await upload_file(
            file_content=audio_content,
            destination_path=audio_path,
            content_type="audio/mpeg"
        )

        # Update document with success
        db.collection("generated_audio").document(audio_id).update({
            "status": AudioStatus.COMPLETED.value,
            "audioUrl": audio_url,
            "durationSeconds": duration,
            "updatedAt": datetime.utcnow(),
        })

        logger.info(f"Audio generated successfully for {audio_id}")

    except Exception as e:
        logger.error(f"Audio generation failed for {audio_id}: {e}")
        db.collection("generated_audio").document(audio_id).update({
            "status": AudioStatus.FAILED.value,
            "errorMessage": str(e),
            "updatedAt": datetime.utcnow(),
        })

    # Return final state
    final_data = await get_document("generated_audio", audio_id)
    return _audio_to_response(audio_id, final_data)


@router.get("", response_model=AudioListResponse)
async def list_generated_audio(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated audio files
    """
    db = get_firestore()
    query = db.collection("generated_audio")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").limit(50).stream())

    audios = [_audio_to_response(doc.id, doc.to_dict()) for doc in docs]

    return AudioListResponse(
        audios=audios,
        total=len(audios)
    )


@router.get("/{audio_id}", response_model=AudioResponse)
async def get_audio(
    audio_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get generated audio by ID
    """
    audio_data = await get_document("generated_audio", audio_id)

    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )

    return _audio_to_response(audio_id, audio_data)


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio(
    audio_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete generated audio
    Author or Admin only
    """
    db = get_firestore()
    audio_ref = db.collection("generated_audio").document(audio_id)
    doc = audio_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this audio"
        )

    audio_ref.delete()
