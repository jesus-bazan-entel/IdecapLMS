"""
QR Code Service
Generate and validate QR codes for student authentication
"""
import hashlib
import logging
from typing import Optional, Tuple
from datetime import datetime
from io import BytesIO

import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

from app.core.firebase_admin import get_document, update_document

logger = logging.getLogger(__name__)


class QRService:
    """Service for QR code operations"""

    # QR code prefix for identification
    QR_PREFIX = "APOLO"

    # Error correction levels
    ERROR_CORRECTION_LEVELS = {
        "L": ERROR_CORRECT_L,  # ~7% error correction
        "M": ERROR_CORRECT_M,  # ~15% error correction
        "Q": ERROR_CORRECT_Q,  # ~25% error correction
        "H": ERROR_CORRECT_H,  # ~30% error correction
    }

    def generate_hash(self, student_id: str, email: str, salt: Optional[str] = None) -> str:
        """
        Generate a unique hash for student QR code

        Args:
            student_id: Student's unique ID
            email: Student's email
            salt: Optional salt for additional security

        Returns:
            32-character hash string
        """
        if salt is None:
            salt = datetime.utcnow().isoformat()

        data = f"{student_id}:{email}:{salt}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def generate_qr_data(self, student_id: str, qr_hash: str) -> str:
        """
        Generate the data string to encode in QR code

        Format: APOLO:{student_id}:{qr_hash}
        """
        return f"{self.QR_PREFIX}:{student_id}:{qr_hash}"

    def parse_qr_data(self, qr_data: str) -> Optional[Tuple[str, str]]:
        """
        Parse QR code data string

        Args:
            qr_data: Raw QR code data

        Returns:
            Tuple of (student_id, qr_hash) or None if invalid
        """
        try:
            if not qr_data.startswith(f"{self.QR_PREFIX}:"):
                return None

            parts = qr_data.split(":")
            if len(parts) != 3:
                return None

            _, student_id, qr_hash = parts

            if not student_id or not qr_hash:
                return None

            return (student_id, qr_hash)

        except Exception as e:
            logger.error(f"Error parsing QR data: {e}")
            return None

    def generate_qr_image(
        self,
        data: str,
        size: int = 10,
        border: int = 4,
        error_correction: str = "M",
        fill_color: str = "black",
        back_color: str = "white",
    ) -> bytes:
        """
        Generate QR code image

        Args:
            data: Data to encode
            size: Box size in pixels
            border: Border size in boxes
            error_correction: L, M, Q, or H
            fill_color: QR code color
            back_color: Background color

        Returns:
            PNG image as bytes
        """
        error_level = self.ERROR_CORRECTION_LEVELS.get(
            error_correction.upper(),
            ERROR_CORRECT_M
        )

        qr = qrcode.QRCode(
            version=1,
            error_correction=error_level,
            box_size=size,
            border=border,
        )

        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer.getvalue()

    async def generate_student_qr(
        self,
        student_id: str,
        email: str,
        size: int = 10,
        update_database: bool = True,
    ) -> Tuple[bytes, str]:
        """
        Generate QR code for a student

        Args:
            student_id: Student's unique ID
            email: Student's email
            size: Image size
            update_database: Whether to update the student's qrCodeHash

        Returns:
            Tuple of (image_bytes, qr_hash)
        """
        # Generate hash
        qr_hash = self.generate_hash(student_id, email)

        # Generate QR data
        qr_data = self.generate_qr_data(student_id, qr_hash)

        # Generate image
        image = self.generate_qr_image(qr_data, size=size)

        # Update database if requested
        if update_database:
            await update_document("users", student_id, {
                "qrCodeHash": qr_hash,
                "qrGeneratedAt": datetime.utcnow(),
            })

        return (image, qr_hash)

    async def verify_qr_code(self, qr_data: str) -> dict:
        """
        Verify a QR code and return student information

        Args:
            qr_data: Raw QR code data

        Returns:
            Dict with verification result:
            {
                "valid": bool,
                "student_id": str or None,
                "student_data": dict or None,
                "error": str or None
            }
        """
        # Parse QR data
        parsed = self.parse_qr_data(qr_data)

        if not parsed:
            return {
                "valid": False,
                "student_id": None,
                "student_data": None,
                "error": "Invalid QR code format"
            }

        student_id, qr_hash = parsed

        # Fetch student data
        student_data = await get_document("users", student_id)

        if not student_data:
            return {
                "valid": False,
                "student_id": student_id,
                "student_data": None,
                "error": "Student not found"
            }

        # Verify hash matches
        stored_hash = student_data.get("qrCodeHash") or student_data.get("qr_code_hash")

        if stored_hash != qr_hash:
            return {
                "valid": False,
                "student_id": student_id,
                "student_data": None,
                "error": "QR code expired or invalid"
            }

        # Check if student is disabled
        is_disabled = (
            student_data.get("isDisabled") or
            student_data.get("is_disabled") or
            student_data.get("isDisbaled")  # typo in original Flutter code
        )

        if is_disabled:
            return {
                "valid": False,
                "student_id": student_id,
                "student_data": student_data,
                "error": "Student account is disabled"
            }

        # Verify student role
        role = student_data.get("role", [])
        if isinstance(role, str):
            role = [role]

        if "student" not in role:
            return {
                "valid": False,
                "student_id": student_id,
                "student_data": student_data,
                "error": "User is not a student"
            }

        return {
            "valid": True,
            "student_id": student_id,
            "student_data": student_data,
            "error": None
        }

    async def regenerate_qr(self, student_id: str) -> Tuple[bytes, str]:
        """
        Regenerate QR code for an existing student

        This invalidates the previous QR code.

        Args:
            student_id: Student's unique ID

        Returns:
            Tuple of (image_bytes, new_qr_hash)
        """
        # Fetch student data
        student_data = await get_document("users", student_id)

        if not student_data:
            raise ValueError(f"Student not found: {student_id}")

        email = student_data.get("email", "")

        # Generate new QR with current timestamp as salt
        return await self.generate_student_qr(
            student_id,
            email,
            update_database=True
        )


# Singleton instance
_qr_service: Optional[QRService] = None


def get_qr_service() -> QRService:
    """Get the QR service singleton"""
    global _qr_service
    if _qr_service is None:
        _qr_service = QRService()
    return _qr_service
