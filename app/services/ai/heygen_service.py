"""
HeyGen Service
Avatar video generation using HeyGen API
"""
import logging
import httpx
from typing import Optional, List, Dict, Any
from enum import Enum

from app.config import settings

logger = logging.getLogger(__name__)

HEYGEN_API_BASE = "https://api.heygen.com"


class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HeyGenService:
    """Service for generating avatar videos with HeyGen API"""

    def __init__(self):
        self._api_key = settings.heygen_api_key
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure API key is configured"""
        if self._initialized:
            return
        if not self._api_key:
            raise ValueError("HeyGen API key not configured. Set HEYGEN_API_KEY environment variable.")
        self._initialized = True
        logger.info("HeyGen Service initialized")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers"""
        return {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def list_avatars(self) -> List[Dict[str, Any]]:
        """
        List available HeyGen avatars

        Returns:
            List of avatar objects with id, name, preview_image_url, etc.
        """
        self._ensure_initialized()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HEYGEN_API_BASE}/v2/avatars",
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            avatars = []
            # Process talking photos
            for avatar in data.get("data", {}).get("talking_photos", []):
                avatars.append({
                    "id": avatar.get("talking_photo_id"),
                    "name": avatar.get("talking_photo_name", "Talking Photo"),
                    "type": "talking_photo",
                    "preview_url": avatar.get("preview_image_url"),
                })

            # Process avatars
            for avatar in data.get("data", {}).get("avatars", []):
                avatars.append({
                    "id": avatar.get("avatar_id"),
                    "name": avatar.get("avatar_name", "Avatar"),
                    "type": "avatar",
                    "preview_url": avatar.get("preview_image_url"),
                    "gender": avatar.get("gender"),
                })

            return avatars

    async def list_voices(self, language: str = "pt") -> List[Dict[str, Any]]:
        """
        List available HeyGen voices

        Args:
            language: Language code filter (e.g., 'pt', 'es', 'en')

        Returns:
            List of voice objects
        """
        self._ensure_initialized()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HEYGEN_API_BASE}/v2/voices",
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            voices = []
            for voice in data.get("data", {}).get("voices", []):
                voice_lang = voice.get("language", "").lower()
                # Filter by language if specified
                if language and not voice_lang.startswith(language.lower()):
                    continue

                voices.append({
                    "id": voice.get("voice_id"),
                    "name": voice.get("name", voice.get("display_name", "Voice")),
                    "language": voice.get("language"),
                    "gender": voice.get("gender"),
                    "preview_url": voice.get("preview_audio"),
                    "support_pause": voice.get("support_pause", False),
                    "emotion_support": voice.get("emotion_support", False),
                })

            return voices

    async def generate_video(
        self,
        script: str,
        avatar_id: str,
        voice_id: str,
        title: str = "Generated Video",
        aspect_ratio: str = "16:9",
        background_color: str = "#FFFFFF",
        test_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a video with HeyGen

        Args:
            script: The text script for the avatar to speak
            avatar_id: HeyGen avatar ID
            voice_id: HeyGen voice ID
            title: Video title
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            background_color: Background color hex code
            test_mode: If True, generates a test video (watermarked, free)

        Returns:
            Video generation response with video_id
        """
        self._ensure_initialized()

        # Map aspect ratio to HeyGen dimension format
        dimension_map = {
            "16:9": {"width": 1920, "height": 1080},
            "9:16": {"width": 1080, "height": 1920},
            "1:1": {"width": 1080, "height": 1080},
        }
        dimensions = dimension_map.get(aspect_ratio, dimension_map["16:9"])

        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id,
                    },
                    "background": {
                        "type": "color",
                        "value": background_color,
                    },
                }
            ],
            "dimension": dimensions,
            "aspect_ratio": None,  # Using explicit dimensions
            "test": test_mode,
            "title": title,
        }

        logger.info(f"Generating HeyGen video: {title} with avatar {avatar_id}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEYGEN_API_BASE}/v2/video/generate",
                headers=self._get_headers(),
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                raise Exception(f"HeyGen API error: {data.get('error')}")

            video_id = data.get("data", {}).get("video_id")
            logger.info(f"HeyGen video generation started: {video_id}")

            return {
                "video_id": video_id,
                "status": VideoStatus.PENDING.value,
            }

    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Get video generation status

        Args:
            video_id: HeyGen video ID

        Returns:
            Status object with status, video_url, thumbnail_url, etc.
        """
        self._ensure_initialized()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HEYGEN_API_BASE}/v1/video_status.get",
                params={"video_id": video_id},
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                raise Exception(f"HeyGen API error: {data.get('error')}")

            status_data = data.get("data", {})
            heygen_status = status_data.get("status", "pending")

            # Map HeyGen status to our status
            status_map = {
                "pending": VideoStatus.PENDING.value,
                "processing": VideoStatus.PROCESSING.value,
                "completed": VideoStatus.COMPLETED.value,
                "failed": VideoStatus.FAILED.value,
            }

            return {
                "video_id": video_id,
                "status": status_map.get(heygen_status, VideoStatus.PENDING.value),
                "video_url": status_data.get("video_url"),
                "thumbnail_url": status_data.get("thumbnail_url"),
                "duration": status_data.get("duration"),
                "gif_url": status_data.get("gif_url"),
                "error": status_data.get("error"),
            }

    async def get_remaining_quota(self) -> Dict[str, Any]:
        """
        Get remaining API quota

        Returns:
            Quota information
        """
        self._ensure_initialized()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HEYGEN_API_BASE}/v1/video/get_remaining_quota",
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return data.get("data", {})


# Singleton instance
_heygen_service: Optional[HeyGenService] = None


def get_heygen_service() -> HeyGenService:
    """Get the HeyGen service singleton"""
    global _heygen_service
    if _heygen_service is None:
        _heygen_service = HeyGenService()
    return _heygen_service
