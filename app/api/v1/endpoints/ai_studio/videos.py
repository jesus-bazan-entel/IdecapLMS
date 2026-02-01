"""
AI Studio - Videos endpoints
Generate avatar videos with HeyGen API
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import logging

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document, update_document
from app.services.ai.heygen_service import get_heygen_service

router = APIRouter()
logger = logging.getLogger(__name__)


class VideoStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    GENERATING = "generating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoAspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


# Request/Response schemas
class VideoGenerateRequest(BaseModel):
    """Request to generate an avatar video"""
    script: str  # The text for the avatar to speak
    avatar_id: str  # HeyGen avatar ID
    voice_id: str  # HeyGen voice ID
    title: Optional[str] = None
    aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE
    background_color: str = "#FFFFFF"
    test_mode: bool = False  # Use test mode for free watermarked videos
    lesson_id: Optional[str] = None


class VideoUpdateRequest(BaseModel):
    """Request to update video metadata"""
    title: Optional[str] = None
    description: Optional[str] = None


class VideoResponse(BaseModel):
    """Video response"""
    id: str
    title: str
    script: str
    status: str
    avatar_id: str
    voice_id: str
    aspect_ratio: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    lesson_id: Optional[str] = None
    heygen_video_id: Optional[str] = None


class VideoListResponse(BaseModel):
    """List of videos"""
    videos: List[VideoResponse]
    total: int


class AvatarInfo(BaseModel):
    """Avatar information"""
    id: str
    name: str
    type: str
    preview_url: Optional[str] = None
    gender: Optional[str] = None


class VoiceInfo(BaseModel):
    """Voice information"""
    id: str
    name: str
    language: Optional[str] = None
    gender: Optional[str] = None
    preview_url: Optional[str] = None


class QuotaInfo(BaseModel):
    """API quota information"""
    remaining_quota: Optional[int] = None
    used_quota: Optional[int] = None


def _video_to_response(vid_id: str, data: dict) -> VideoResponse:
    return VideoResponse(
        id=vid_id,
        title=data.get("title", ""),
        script=data.get("script", data.get("prompt", "")),
        status=data.get("status", "pending"),
        avatar_id=data.get("avatarId", ""),
        voice_id=data.get("voiceId", ""),
        aspect_ratio=data.get("aspectRatio", "16:9"),
        video_url=data.get("videoUrl"),
        thumbnail_url=data.get("thumbnailUrl"),
        duration=data.get("duration"),
        error_message=data.get("errorMessage"),
        created_at=data.get("createdAt", datetime.utcnow()),
        completed_at=data.get("completedAt"),
        lesson_id=data.get("lessonId"),
        heygen_video_id=data.get("heygenVideoId"),
    )


async def _poll_heygen_status(video_id: str, heygen_video_id: str):
    """Background task to poll HeyGen for video status"""
    import asyncio

    heygen = get_heygen_service()
    db = get_firestore()

    max_attempts = 60  # Poll for up to 30 minutes (every 30 seconds)
    attempt = 0

    while attempt < max_attempts:
        try:
            status_data = await heygen.get_video_status(heygen_video_id)
            current_status = status_data.get("status")

            logger.info(f"HeyGen status for {video_id}: {current_status}")

            if current_status == "completed":
                # Video is ready
                db.collection("generated_videos").document(video_id).update({
                    "status": VideoStatus.COMPLETED.value,
                    "videoUrl": status_data.get("video_url"),
                    "thumbnailUrl": status_data.get("thumbnail_url"),
                    "duration": status_data.get("duration"),
                    "errorMessage": None,
                    "completedAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                })
                logger.info(f"Video {video_id} completed successfully")
                return

            elif current_status == "failed":
                # Video generation failed
                db.collection("generated_videos").document(video_id).update({
                    "status": VideoStatus.FAILED.value,
                    "errorMessage": status_data.get("error", "Video generation failed"),
                    "updatedAt": datetime.utcnow(),
                })
                logger.error(f"Video {video_id} failed: {status_data.get('error')}")
                return

            elif current_status == "processing":
                # Still processing
                db.collection("generated_videos").document(video_id).update({
                    "status": VideoStatus.PROCESSING.value,
                    "updatedAt": datetime.utcnow(),
                })

            # Wait before next poll
            await asyncio.sleep(30)
            attempt += 1

        except Exception as e:
            logger.error(f"Error polling HeyGen status for {video_id}: {e}")
            await asyncio.sleep(30)
            attempt += 1

    # Timeout - mark as failed
    db.collection("generated_videos").document(video_id).update({
        "status": VideoStatus.FAILED.value,
        "errorMessage": "Video generation timed out. Please try again.",
        "updatedAt": datetime.utcnow(),
    })
    logger.error(f"Video {video_id} timed out after {max_attempts} attempts")


@router.get("/avatars", response_model=List[AvatarInfo])
async def list_avatars(
    current_user: dict = Depends(get_current_user),
):
    """
    List available HeyGen avatars
    """
    try:
        heygen = get_heygen_service()
        avatars = await heygen.list_avatars()
        return [AvatarInfo(**avatar) for avatar in avatars]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing avatars: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch avatars from HeyGen"
        )


@router.get("/voices", response_model=List[VoiceInfo])
async def list_voices(
    language: str = "pt",
    current_user: dict = Depends(get_current_user),
):
    """
    List available HeyGen voices

    Args:
        language: Language code to filter voices (pt, es, en)
    """
    try:
        heygen = get_heygen_service()
        voices = await heygen.list_voices(language)
        return [VoiceInfo(**voice) for voice in voices]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch voices from HeyGen"
        )


@router.get("/quota", response_model=QuotaInfo)
async def get_quota(
    current_user: dict = Depends(require_author),
):
    """
    Get remaining HeyGen API quota
    Author or Admin only
    """
    try:
        heygen = get_heygen_service()
        quota = await heygen.get_remaining_quota()
        return QuotaInfo(
            remaining_quota=quota.get("remaining_quota"),
            used_quota=quota.get("used_quota"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch quota from HeyGen"
        )


@router.post("/generate", response_model=VideoResponse)
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_author),
):
    """
    Generate an avatar video with HeyGen
    Author or Admin only

    Note: Video generation is an async process that may take several minutes.
    Poll the status endpoint to check progress.
    """
    # Validate script length
    if len(request.script) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script exceeds maximum length of 5000 characters"
        )

    if len(request.script) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script must be at least 10 characters"
        )

    db = get_firestore()
    vid_id = str(uuid.uuid4())

    # Generate title if not provided
    title = request.title or f"Video: {request.script[:50]}..."

    # Create video document
    vid_data = {
        "title": title,
        "script": request.script,
        "avatarId": request.avatar_id,
        "voiceId": request.voice_id,
        "aspectRatio": request.aspect_ratio.value,
        "backgroundColor": request.background_color,
        "testMode": request.test_mode,
        "status": VideoStatus.PENDING.value,
        "videoUrl": None,
        "thumbnailUrl": None,
        "duration": None,
        "errorMessage": None,
        "lessonId": request.lesson_id,
        "heygenVideoId": None,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
        "completedAt": None,
    }

    db.collection("generated_videos").document(vid_id).set(vid_data)

    try:
        heygen = get_heygen_service()

        # Start video generation
        result = await heygen.generate_video(
            script=request.script,
            avatar_id=request.avatar_id,
            voice_id=request.voice_id,
            title=title,
            aspect_ratio=request.aspect_ratio.value,
            background_color=request.background_color,
            test_mode=request.test_mode,
        )

        heygen_video_id = result.get("video_id")

        # Update with HeyGen video ID
        db.collection("generated_videos").document(vid_id).update({
            "status": VideoStatus.GENERATING.value,
            "heygenVideoId": heygen_video_id,
            "updatedAt": datetime.utcnow(),
        })

        logger.info(f"Video {vid_id} started generating with HeyGen ID {heygen_video_id}")

        # Start background polling for status
        background_tasks.add_task(_poll_heygen_status, vid_id, heygen_video_id)

    except ValueError as e:
        # API key not configured
        db.collection("generated_videos").document(vid_id).update({
            "status": VideoStatus.FAILED.value,
            "errorMessage": str(e),
            "updatedAt": datetime.utcnow(),
        })
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating video: {e}")
        db.collection("generated_videos").document(vid_id).update({
            "status": VideoStatus.FAILED.value,
            "errorMessage": f"Error al generar video: {str(e)}",
            "updatedAt": datetime.utcnow(),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate video: {str(e)}"
        )

    # Return the current state
    final_data = await get_document("generated_videos", vid_id)
    return _video_to_response(vid_id, final_data)


@router.get("", response_model=VideoListResponse)
async def list_videos(
    lesson_id: Optional[str] = None,
    status_filter: Optional[VideoStatus] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated videos
    """
    db = get_firestore()
    query = db.collection("generated_videos")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    if status_filter:
        query = query.where("status", "==", status_filter.value)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").stream())

    videos = [_video_to_response(doc.id, doc.to_dict()) for doc in docs]

    return VideoListResponse(
        videos=videos,
        total=len(videos)
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get video by ID
    Use this endpoint to poll for video generation status
    """
    vid_data = await get_document("generated_videos", video_id)

    if not vid_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return _video_to_response(video_id, vid_data)


@router.get("/{video_id}/status")
async def get_generation_status(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get video generation status (lightweight endpoint for polling)
    """
    vid_data = await get_document("generated_videos", video_id)

    if not vid_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # If video is still generating, check HeyGen status
    heygen_video_id = vid_data.get("heygenVideoId")
    current_status = vid_data.get("status")

    if heygen_video_id and current_status in [VideoStatus.GENERATING.value, VideoStatus.PROCESSING.value]:
        try:
            heygen = get_heygen_service()
            status_data = await heygen.get_video_status(heygen_video_id)

            # Update local status if changed
            if status_data.get("status") == "completed":
                db = get_firestore()
                db.collection("generated_videos").document(video_id).update({
                    "status": VideoStatus.COMPLETED.value,
                    "videoUrl": status_data.get("video_url"),
                    "thumbnailUrl": status_data.get("thumbnail_url"),
                    "duration": status_data.get("duration"),
                    "completedAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                })
                vid_data = await get_document("generated_videos", video_id)
        except Exception as e:
            logger.error(f"Error checking HeyGen status: {e}")

    return {
        "id": video_id,
        "status": vid_data.get("status"),
        "error_message": vid_data.get("errorMessage"),
        "video_url": vid_data.get("videoUrl"),
        "thumbnail_url": vid_data.get("thumbnailUrl"),
        "duration": vid_data.get("duration"),
    }


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: str,
    request: VideoUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Update video metadata
    Author or Admin only
    """
    vid_data = await get_document("generated_videos", video_id)

    if not vid_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    update_data = {}

    if request.title is not None:
        update_data["title"] = request.title

    if request.description is not None:
        update_data["description"] = request.description

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("generated_videos", video_id, update_data)

    updated = await get_document("generated_videos", video_id)
    return _video_to_response(video_id, updated)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete video
    Author or Admin only
    """
    db = get_firestore()
    vid_ref = db.collection("generated_videos").document(video_id)
    doc = vid_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this video"
        )

    vid_ref.delete()


@router.post("/{video_id}/cancel")
async def cancel_generation(
    video_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Cancel video generation in progress
    Author or Admin only
    """
    vid_data = await get_document("generated_videos", video_id)

    if not vid_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    current_status = vid_data.get("status")
    if current_status not in [VideoStatus.PENDING.value, VideoStatus.QUEUED.value, VideoStatus.GENERATING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel video with status: {current_status}"
        )

    # Update status to failed with cancellation message
    await update_document("generated_videos", video_id, {
        "status": VideoStatus.FAILED.value,
        "errorMessage": "Generation cancelled by user",
        "updatedAt": datetime.utcnow(),
    })

    return {"message": "Video generation cancelled"}


@router.post("/{video_id}/regenerate", response_model=VideoResponse)
async def regenerate_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_author),
):
    """
    Regenerate video with same settings
    Author or Admin only
    """
    vid_data = await get_document("generated_videos", video_id)

    if not vid_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Reset status
    await update_document("generated_videos", video_id, {
        "status": VideoStatus.PENDING.value,
        "videoUrl": None,
        "thumbnailUrl": None,
        "duration": None,
        "errorMessage": None,
        "completedAt": None,
        "heygenVideoId": None,
        "updatedAt": datetime.utcnow(),
    })

    try:
        heygen = get_heygen_service()

        # Start video generation
        result = await heygen.generate_video(
            script=vid_data.get("script", vid_data.get("prompt", "")),
            avatar_id=vid_data.get("avatarId"),
            voice_id=vid_data.get("voiceId"),
            title=vid_data.get("title", "Regenerated Video"),
            aspect_ratio=vid_data.get("aspectRatio", "16:9"),
            background_color=vid_data.get("backgroundColor", "#FFFFFF"),
            test_mode=vid_data.get("testMode", False),
        )

        heygen_video_id = result.get("video_id")

        # Update with HeyGen video ID
        await update_document("generated_videos", video_id, {
            "status": VideoStatus.GENERATING.value,
            "heygenVideoId": heygen_video_id,
            "updatedAt": datetime.utcnow(),
        })

        # Start background polling
        background_tasks.add_task(_poll_heygen_status, video_id, heygen_video_id)

    except Exception as e:
        logger.error(f"Error regenerating video: {e}")
        await update_document("generated_videos", video_id, {
            "status": VideoStatus.FAILED.value,
            "errorMessage": f"Error al regenerar video: {str(e)}",
            "updatedAt": datetime.utcnow(),
        })

    updated = await get_document("generated_videos", video_id)
    return _video_to_response(video_id, updated)
