"""
Storage Service
File upload/download with Firebase Storage
"""
import logging
import uuid
from typing import Optional, BinaryIO
from datetime import datetime, timedelta

from app.core.firebase_admin import get_storage
from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for file storage operations"""

    def __init__(self):
        self._bucket = None

    def _get_bucket(self):
        """Get Firebase Storage bucket"""
        if self._bucket is None:
            self._bucket = get_storage()
        return self._bucket

    async def upload_file(
        self,
        file_data: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload a file to Firebase Storage

        Args:
            file_data: File content as bytes
            destination_path: Path in storage (e.g., "audio/file.mp3")
            content_type: MIME type of the file
            metadata: Optional metadata dict

        Returns:
            Public URL of the uploaded file
        """
        bucket = self._get_bucket()

        try:
            blob = bucket.blob(destination_path)
            blob.upload_from_string(
                file_data,
                content_type=content_type,
            )

            if metadata:
                blob.metadata = metadata
                blob.patch()

            # Make the file publicly accessible
            blob.make_public()

            return blob.public_url

        except Exception as e:
            logger.error(f"Error uploading file to {destination_path}: {e}")
            raise

    async def upload_stream(
        self,
        file_stream: BinaryIO,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file stream to Firebase Storage

        Args:
            file_stream: File-like object
            destination_path: Path in storage
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded file
        """
        bucket = self._get_bucket()

        try:
            blob = bucket.blob(destination_path)
            blob.upload_from_file(file_stream, content_type=content_type)
            blob.make_public()

            return blob.public_url

        except Exception as e:
            logger.error(f"Error uploading stream to {destination_path}: {e}")
            raise

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from Firebase Storage

        Args:
            file_path: Path of the file in storage

        Returns:
            True if deleted successfully
        """
        bucket = self._get_bucket()

        try:
            blob = bucket.blob(file_path)
            blob.delete()
            return True

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    async def get_signed_url(
        self,
        file_path: str,
        expiration_minutes: int = 60,
    ) -> str:
        """
        Get a signed URL for temporary access to a private file

        Args:
            file_path: Path of the file in storage
            expiration_minutes: URL expiration time in minutes

        Returns:
            Signed URL
        """
        bucket = self._get_bucket()

        try:
            blob = bucket.blob(file_path)
            url = blob.generate_signed_url(
                expiration=datetime.utcnow() + timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url

        except Exception as e:
            logger.error(f"Error generating signed URL for {file_path}: {e}")
            raise

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in storage"""
        bucket = self._get_bucket()

        try:
            blob = bucket.blob(file_path)
            return blob.exists()

        except Exception as e:
            logger.error(f"Error checking file existence {file_path}: {e}")
            return False

    def generate_unique_filename(
        self,
        original_filename: str,
        prefix: str = "",
    ) -> str:
        """
        Generate a unique filename with timestamp and UUID

        Args:
            original_filename: Original file name
            prefix: Optional path prefix (e.g., "audio/", "images/")

        Returns:
            Unique filename with path
        """
        # Extract extension
        parts = original_filename.rsplit(".", 1)
        extension = parts[1] if len(parts) > 1 else ""

        # Generate unique name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        filename = f"{timestamp}_{unique_id}"
        if extension:
            filename += f".{extension}"

        return f"{prefix}{filename}"


# Storage paths constants
class StoragePaths:
    """Storage path prefixes for different content types"""
    AUDIO = "generated_audio/"
    PRESENTATIONS = "presentations/"
    IMAGES = "images/"
    VIDEOS = "generated_videos/"
    THUMBNAILS = "thumbnails/"
    EXPORTS = "exports/"
    COURSE_CONTENT = "courses/"
    USER_UPLOADS = "user_uploads/"


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the storage service singleton"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
