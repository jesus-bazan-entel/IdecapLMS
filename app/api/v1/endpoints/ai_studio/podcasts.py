"""
AI Studio - Podcasts endpoints
Generate multi-voice podcasts with AI scripts
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
from app.services.ai.gemini_service import get_gemini_service
from app.services.ai.tts_service import get_tts_service

logger = logging.getLogger(__name__)

router = APIRouter()


class PodcastStatus(str, Enum):
    PENDING = "pending"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_AUDIO = "generating_audio"
    COMPLETED = "completed"
    FAILED = "failed"


class PodcastStyle(str, Enum):
    CONVERSATIONAL = "conversational"
    LECTURE = "lecture"
    INTERVIEW = "interview"
    DEBATE = "debate"
    STORYTELLING = "storytelling"


# Voice configurations for podcast speakers
PODCAST_VOICES = [
    {"id": "host_male", "name": "Carlos (Presentador)", "voice_id": "es-ES-Standard-B", "role": "host"},
    {"id": "host_female", "name": "Ana (Presentadora)", "voice_id": "es-ES-Standard-A", "role": "host"},
    {"id": "guest_male", "name": "Miguel (Invitado)", "voice_id": "es-MX-Standard-B", "role": "guest"},
    {"id": "guest_female", "name": "Sofía (Invitada)", "voice_id": "es-MX-Standard-A", "role": "guest"},
    {"id": "expert_male", "name": "Diego (Experto)", "voice_id": "es-ES-Standard-D", "role": "expert"},
    {"id": "expert_female", "name": "María (Experta)", "voice_id": "es-ES-Standard-C", "role": "expert"},
]


# Request/Response schemas
class PodcastSegment(BaseModel):
    """Single segment of podcast script"""
    order: int
    speaker: str
    speaker_name: str
    text: str
    voice_id: str
    duration_estimate: Optional[float] = None  # seconds


class PodcastGenerateRequest(BaseModel):
    """Request to generate a podcast"""
    topic: str
    style: PodcastStyle = PodcastStyle.CONVERSATIONAL
    duration_minutes: int = 10  # Target duration
    language: str = "es"
    num_speakers: int = 2  # 1-4 speakers
    speaker_ids: List[str] = []  # Optional specific speakers
    additional_context: Optional[str] = None
    lesson_id: Optional[str] = None


class PodcastUpdateRequest(BaseModel):
    """Request to update a podcast"""
    title: Optional[str] = None
    segments: Optional[List[PodcastSegment]] = None


class PodcastResponse(BaseModel):
    """Podcast response"""
    id: str
    title: str
    topic: str
    status: str
    style: str
    target_duration_minutes: int
    actual_duration_seconds: Optional[float] = None
    segments: List[PodcastSegment] = []
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    created_at: datetime
    lesson_id: Optional[str] = None
    error_message: Optional[str] = None


class PodcastListResponse(BaseModel):
    """List of podcasts"""
    podcasts: List[PodcastResponse]
    total: int


class PodcastVoice(BaseModel):
    """Podcast voice option"""
    id: str
    name: str
    voice_id: str
    role: str


def _segment_from_dict(data: dict, order: int) -> PodcastSegment:
    return PodcastSegment(
        order=data.get("order", order),
        speaker=data.get("speaker", ""),
        speaker_name=data.get("speakerName", data.get("speaker_name", "")),
        text=data.get("text", ""),
        voice_id=data.get("voiceId", data.get("voice_id", "")),
        duration_estimate=data.get("durationEstimate", data.get("duration_estimate")),
    )


def _segment_to_dict(segment: PodcastSegment) -> dict:
    return {
        "order": segment.order,
        "speaker": segment.speaker,
        "speakerName": segment.speaker_name,
        "text": segment.text,
        "voiceId": segment.voice_id,
        "durationEstimate": segment.duration_estimate,
    }


async def _generate_podcast_script_task(pod_id: str, topic: str, style: str, duration_minutes: int, speakers: List[str], language: str, additional_context: Optional[str] = None):
    """Background task to generate podcast script with Gemini"""
    db = get_firestore()
    pod_ref = db.collection("podcasts").document(pod_id)

    try:
        # Update status to generating
        pod_ref.update({
            "status": PodcastStatus.GENERATING_SCRIPT.value,
            "updatedAt": datetime.utcnow(),
        })

        # Build speaker list for Gemini
        speaker_list = []
        for speaker_id in speakers:
            voice_info = next((v for v in PODCAST_VOICES if v["id"] == speaker_id), None)
            if voice_info:
                speaker_list.append({
                    "id": speaker_id,
                    "name": voice_info["name"].split(" (")[0],  # Extract name without role
                    "role": voice_info["role"],
                    "voice_id": voice_info["voice_id"],
                })

        # Generate script with Gemini
        gemini = get_gemini_service()
        segments_data = await gemini.generate_podcast_script(
            topic=topic,
            style=style,
            duration_minutes=duration_minutes,
            speakers=speaker_list,
            language=language,
            additional_context=additional_context,
        )

        # Process segments and add voice IDs
        processed_segments = []
        for i, seg in enumerate(segments_data):
            speaker_id = seg.get("speaker_id", "")
            voice_info = next((v for v in PODCAST_VOICES if v["id"] == speaker_id), None)

            processed_segments.append({
                "order": i + 1,
                "speaker": speaker_id,
                "speakerName": seg.get("speaker_name", ""),
                "text": seg.get("text", ""),
                "voiceId": voice_info["voice_id"] if voice_info else "es-ES-Standard-A",
                "durationEstimate": seg.get("duration_estimate", 30),
            })

        # Calculate total estimated duration
        total_duration = sum(s.get("durationEstimate", 30) for s in processed_segments)

        # Update document with generated script (keep status as generating, will update to completed after audio)
        pod_ref.update({
            "segments": processed_segments,
            "updatedAt": datetime.utcnow(),
        })

        logger.info(f"Podcast script generated successfully for {pod_id}, now generating audio...")

        # Automatically trigger audio generation (like NotebookLM - end-to-end generation)
        await _generate_podcast_audio_task(pod_id, processed_segments)

    except Exception as e:
        logger.error(f"Error generating podcast script for {pod_id}: {e}")
        pod_ref.update({
            "status": PodcastStatus.FAILED.value,
            "errorMessage": str(e),
            "updatedAt": datetime.utcnow(),
        })


async def _generate_podcast_audio_task(pod_id: str, segments: List[dict]):
    """Background task to generate podcast audio with TTS"""
    db = get_firestore()
    pod_ref = db.collection("podcasts").document(pod_id)

    try:
        # Update status to generating audio
        pod_ref.update({
            "status": PodcastStatus.GENERATING_AUDIO.value,
            "updatedAt": datetime.utcnow(),
        })

        # Prepare segments for TTS
        tts_segments = []
        for segment in segments:
            voice_id = segment.get("voiceId", "es-ES-Standard-A")
            text = segment.get("text", "")

            if text.strip():
                tts_segments.append({
                    "text": text,
                    "voice_id": voice_id,
                    "speed": 1.0,
                    "pitch": 0.0,
                })

        # Generate audio using TTS service
        tts = get_tts_service()
        audio_content = await tts.generate_audio_segments(tts_segments)

        # Calculate actual duration
        total_duration = sum(
            tts.estimate_duration(seg.get("text", ""))
            for seg in tts_segments
        )

        # Upload audio to Firebase Storage
        audio_path = f"podcasts/{pod_id}.mp3"
        audio_url = await upload_file(
            file_content=audio_content,
            destination_path=audio_path,
            content_type="audio/mpeg"
        )

        # Update document with audio URL
        pod_ref.update({
            "status": PodcastStatus.COMPLETED.value,
            "audioUrl": audio_url,
            "actualDurationSeconds": total_duration,
            "updatedAt": datetime.utcnow(),
        })

        logger.info(f"Podcast audio generated successfully for {pod_id}")

    except Exception as e:
        logger.error(f"Error generating podcast audio for {pod_id}: {e}")
        pod_ref.update({
            "status": PodcastStatus.FAILED.value,
            "errorMessage": str(e),
            "updatedAt": datetime.utcnow(),
        })


def _podcast_to_response(pod_id: str, data: dict) -> PodcastResponse:
    segments_data = data.get("segments", [])
    segments = [_segment_from_dict(s, i) for i, s in enumerate(segments_data)]

    # Generate transcript from segments
    transcript = None
    if segments:
        transcript = "\n\n".join([
            f"**{s.speaker_name}**: {s.text}"
            for s in segments
        ])

    return PodcastResponse(
        id=pod_id,
        title=data.get("title", ""),
        topic=data.get("topic", ""),
        status=data.get("status", "pending"),
        style=data.get("style", "conversational"),
        target_duration_minutes=data.get("targetDurationMinutes", data.get("duration_minutes", 10)),
        actual_duration_seconds=data.get("actualDurationSeconds", data.get("actual_duration_seconds")),
        segments=segments,
        audio_url=data.get("audioUrl"),
        transcript=transcript,
        created_at=data.get("createdAt", datetime.utcnow()),
        lesson_id=data.get("lessonId"),
        error_message=data.get("errorMessage"),
    )


@router.get("/voices", response_model=List[PodcastVoice])
async def list_voices(
    role: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List available podcast voices
    """
    voices = PODCAST_VOICES

    if role:
        voices = [v for v in voices if v["role"] == role]

    return [PodcastVoice(**v) for v in voices]


@router.get("/styles")
async def list_styles(
    current_user: dict = Depends(get_current_user),
):
    """
    List available podcast styles
    """
    return [
        {
            "id": "conversational",
            "name": "Conversacional",
            "description": "Diálogo natural entre presentadores sobre el tema",
            "recommended_speakers": 2
        },
        {
            "id": "lecture",
            "name": "Clase",
            "description": "Explicación educativa detallada por un experto",
            "recommended_speakers": 1
        },
        {
            "id": "interview",
            "name": "Entrevista",
            "description": "Un presentador entrevista a un experto",
            "recommended_speakers": 2
        },
        {
            "id": "debate",
            "name": "Debate",
            "description": "Discusión de diferentes perspectivas sobre el tema",
            "recommended_speakers": 3
        },
        {
            "id": "storytelling",
            "name": "Narrativo",
            "description": "Cuenta una historia relacionada con el tema",
            "recommended_speakers": 1
        },
    ]


@router.post("/generate", response_model=PodcastResponse)
async def generate_podcast(
    request: PodcastGenerateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Generate a podcast with AI (synchronous end-to-end generation like NotebookLM)
    Author or Admin only

    This endpoint waits for full generation (script + audio) before returning.
    Cloud Run timeout is set to 600 seconds to accommodate this.
    """
    if request.duration_minutes < 1 or request.duration_minutes > 60:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duration must be between 1 and 60 minutes"
        )

    if request.num_speakers < 1 or request.num_speakers > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of speakers must be between 1 and 4"
        )

    # Validate speaker IDs if provided
    valid_speaker_ids = [v["id"] for v in PODCAST_VOICES]
    for speaker_id in request.speaker_ids:
        if speaker_id not in valid_speaker_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid speaker_id: {speaker_id}"
            )

    db = get_firestore()
    pod_id = str(uuid.uuid4())

    # Select default speakers if not provided
    speakers = request.speaker_ids
    if not speakers:
        # Select appropriate speakers based on style and count
        if request.style == PodcastStyle.INTERVIEW:
            speakers = ["host_female", "expert_male"][:request.num_speakers]
        elif request.style == PodcastStyle.DEBATE:
            speakers = ["host_male", "expert_female", "guest_male"][:request.num_speakers]
        else:
            speakers = ["host_male", "host_female", "guest_male", "guest_female"][:request.num_speakers]

    # Create podcast document
    pod_data = {
        "title": f"Podcast: {request.topic[:50]}",
        "topic": request.topic,
        "style": request.style.value,
        "targetDurationMinutes": request.duration_minutes,
        "numSpeakers": request.num_speakers,
        "speakerIds": speakers,
        "language": request.language,
        "additionalContext": request.additional_context,
        "status": PodcastStatus.GENERATING_SCRIPT.value,
        "segments": [],
        "audioUrl": None,
        "actualDurationSeconds": None,
        "lessonId": request.lesson_id,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
    }

    db.collection("podcasts").document(pod_id).set(pod_data)
    logger.info(f"Starting podcast generation for {pod_id}: {request.topic}")

    # Synchronous end-to-end generation (wait for completion)
    # This ensures the task completes before Cloud Run scales down
    try:
        await _generate_podcast_script_task(
            pod_id=pod_id,
            topic=request.topic,
            style=request.style.value,
            duration_minutes=request.duration_minutes,
            speakers=speakers,
            language=request.language,
            additional_context=request.additional_context,
        )
    except Exception as e:
        logger.error(f"Podcast generation failed for {pod_id}: {e}")
        # Error is already logged and status updated in the task
        pass

    # Return the final state
    final_data = await get_document("podcasts", pod_id)
    return _podcast_to_response(pod_id, final_data)


@router.get("", response_model=PodcastListResponse)
async def list_podcasts(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated podcasts
    """
    db = get_firestore()
    query = db.collection("podcasts")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").stream())

    podcasts = [_podcast_to_response(doc.id, doc.to_dict()) for doc in docs]

    return PodcastListResponse(
        podcasts=podcasts,
        total=len(podcasts)
    )


@router.get("/{podcast_id}", response_model=PodcastResponse)
async def get_podcast(
    podcast_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get podcast by ID
    """
    pod_data = await get_document("podcasts", podcast_id)

    if not pod_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )

    return _podcast_to_response(podcast_id, pod_data)


@router.put("/{podcast_id}", response_model=PodcastResponse)
async def update_podcast(
    podcast_id: str,
    request: PodcastUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Update podcast script
    Author or Admin only
    """
    pod_data = await get_document("podcasts", podcast_id)

    if not pod_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )

    update_data = {}

    if request.title is not None:
        update_data["title"] = request.title

    if request.segments is not None:
        update_data["segments"] = [_segment_to_dict(s) for s in request.segments]
        # Reset audio URL when script changes
        update_data["audioUrl"] = None
        update_data["actualDurationSeconds"] = None

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("podcasts", podcast_id, update_data)

    updated = await get_document("podcasts", podcast_id)
    return _podcast_to_response(podcast_id, updated)


@router.delete("/{podcast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_podcast(
    podcast_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete podcast
    Author or Admin only
    """
    db = get_firestore()
    pod_ref = db.collection("podcasts").document(podcast_id)
    doc = pod_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this podcast"
        )

    # TODO: Delete audio file from storage if exists

    pod_ref.delete()


@router.post("/{podcast_id}/regenerate-script", response_model=PodcastResponse)
async def regenerate_script(
    podcast_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Regenerate podcast script with AI (synchronous)
    Author or Admin only
    """
    pod_data = await get_document("podcasts", podcast_id)

    if not pod_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )

    # Reset status
    await update_document("podcasts", podcast_id, {
        "status": PodcastStatus.GENERATING_SCRIPT.value,
        "segments": [],
        "audioUrl": None,
        "actualDurationSeconds": None,
        "updatedAt": datetime.utcnow(),
    })

    logger.info(f"Regenerating podcast script for {podcast_id}")

    # Synchronous regeneration
    try:
        await _generate_podcast_script_task(
            pod_id=podcast_id,
            topic=pod_data.get("topic", ""),
            style=pod_data.get("style", "conversational"),
            duration_minutes=pod_data.get("targetDurationMinutes", 10),
            speakers=pod_data.get("speakerIds", []),
            language=pod_data.get("language", "es"),
            additional_context=pod_data.get("additionalContext"),
        )
    except Exception as e:
        logger.error(f"Podcast regeneration failed for {podcast_id}: {e}")
        pass

    updated = await get_document("podcasts", podcast_id)
    return _podcast_to_response(podcast_id, updated)


@router.post("/{podcast_id}/generate-audio", response_model=PodcastResponse)
async def generate_audio(
    podcast_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Generate audio from existing script (synchronous)
    Author or Admin only
    """
    pod_data = await get_document("podcasts", podcast_id)

    if not pod_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )

    # Check if script exists
    if not pod_data.get("segments"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Podcast script is empty. Generate script first."
        )

    # Update status
    await update_document("podcasts", podcast_id, {
        "status": PodcastStatus.GENERATING_AUDIO.value,
        "audioUrl": None,
        "updatedAt": datetime.utcnow(),
    })

    logger.info(f"Generating audio for podcast {podcast_id}")

    # Synchronous audio generation
    segments = pod_data.get("segments", [])
    try:
        await _generate_podcast_audio_task(
            pod_id=podcast_id,
            segments=segments,
        )
    except Exception as e:
        logger.error(f"Audio generation failed for {podcast_id}: {e}")
        pass

    updated = await get_document("podcasts", podcast_id)
    return _podcast_to_response(podcast_id, updated)


@router.get("/{podcast_id}/transcript")
async def get_transcript(
    podcast_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get podcast transcript in text format
    """
    pod_data = await get_document("podcasts", podcast_id)

    if not pod_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )

    segments = pod_data.get("segments", [])
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript available"
        )

    # Generate transcript
    transcript_lines = []
    for segment in segments:
        speaker_name = segment.get("speakerName", segment.get("speaker_name", "Speaker"))
        text = segment.get("text", "")
        transcript_lines.append(f"{speaker_name}: {text}")

    return {
        "title": pod_data.get("title", ""),
        "transcript": "\n\n".join(transcript_lines)
    }
