"""
Access codes management endpoints
Generate and validate student access codes for QR/code-based login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import secrets
import string

from app.core.security import get_current_user, require_admin, create_access_token
from app.core.firebase_admin import (
    get_firestore,
    get_document,
    update_document,
)
from app.config import settings

router = APIRouter()


# Request/Response schemas
class AccessCodeGenerateRequest(BaseModel):
    """Generate access code request"""
    student_id: str
    expires_in_days: Optional[int] = None  # None = never expires


class AccessCodeValidateRequest(BaseModel):
    """Validate access code request"""
    code: str


class CourseInfo(BaseModel):
    """Course info for response"""
    id: str
    name: str
    description: Optional[str] = None
    level: Optional[str] = None


class StudentInfo(BaseModel):
    """Student info for response"""
    id: str
    email: str
    name: str
    student_level: Optional[str] = None
    enrolled_courses: List[str] = []


class AccessCodeResponse(BaseModel):
    """Access code response"""
    code: str
    student_id: str
    student_name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    used: bool = False


class AccessCodeValidateResponse(BaseModel):
    """Access code validation response with JWT token"""
    valid: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    student: Optional[StudentInfo] = None
    courses: Optional[List[CourseInfo]] = []


class AccessCodeListResponse(BaseModel):
    """List of access codes"""
    codes: List[AccessCodeResponse]
    total: int


def _generate_access_code(length: int = 6) -> str:
    """Generate a unique alphanumeric access code"""
    # Use uppercase letters and digits, excluding confusing chars (0, O, I, 1, L)
    chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(chars) for _ in range(length))


def _code_to_response(code_data: dict) -> AccessCodeResponse:
    """Convert Firestore code data to response"""
    created_at = code_data.get("createdAt") or code_data.get("created_at")
    expires_at = code_data.get("expiresAt") or code_data.get("expires_at")

    return AccessCodeResponse(
        code=code_data.get("code", ""),
        student_id=code_data.get("studentId") or code_data.get("student_id", ""),
        student_name=code_data.get("studentName") or code_data.get("student_name", ""),
        created_at=created_at if isinstance(created_at, datetime) else datetime.utcnow(),
        expires_at=expires_at if isinstance(expires_at, datetime) else None,
        used=code_data.get("used", False),
    )


@router.post("/generate", response_model=AccessCodeResponse)
async def generate_access_code(
    request: AccessCodeGenerateRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Generate a new access code for a student
    Admin only
    """
    db = get_firestore()

    # Verify student exists
    student_data = await get_document("users", request.student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Verify it's a student
    role = student_data.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "student" not in role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a student"
        )

    # Generate unique code
    access_codes_ref = db.collection("access_codes")
    max_attempts = 10
    code = None

    for _ in range(max_attempts):
        potential_code = _generate_access_code()
        # Check if code already exists
        existing = list(access_codes_ref.where("code", "==", potential_code).limit(1).stream())
        if not existing:
            code = potential_code
            break

    if not code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique code"
        )

    # Deactivate any previous unused codes for this student
    previous_codes = access_codes_ref.where("studentId", "==", request.student_id).where("used", "==", False).stream()
    for doc in previous_codes:
        doc.reference.update({"used": True, "deactivatedAt": datetime.utcnow()})

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create new access code document
    code_data = {
        "code": code,
        "studentId": request.student_id,
        "studentName": student_data.get("name", ""),
        "studentEmail": student_data.get("email", ""),
        "createdAt": datetime.utcnow(),
        "expiresAt": expires_at,
        "used": False,
        "createdBy": current_user["id"],
    }

    access_codes_ref.document().set(code_data)

    # Also store the code hash on the student for quick lookup
    await update_document("users", request.student_id, {
        "accessCode": code,
        "accessCodeCreatedAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    })

    return _code_to_response(code_data)


@router.post("/validate", response_model=AccessCodeValidateResponse)
async def validate_access_code(
    request: AccessCodeValidateRequest,
):
    """
    Validate an access code and return JWT token for student login
    Public endpoint - used by student mobile app
    """
    db = get_firestore()
    code = request.code.upper().strip()

    if not code or len(code) < 4:
        return AccessCodeValidateResponse(
            valid=False,
            message="Invalid access code format"
        )

    # Find the access code
    access_codes_ref = db.collection("access_codes")
    query = access_codes_ref.where("code", "==", code).limit(1)
    docs = list(query.stream())

    if not docs:
        # Also try to find by student's accessCode field (fallback)
        users_ref = db.collection("users")
        user_query = users_ref.where("accessCode", "==", code).limit(1)
        user_docs = list(user_query.stream())

        if not user_docs:
            return AccessCodeValidateResponse(
                valid=False,
                message="Código de acceso inválido"
            )

        # Found by user's accessCode field
        user_doc = user_docs[0]
        student_id = user_doc.id
        student_data = user_doc.to_dict()
    else:
        # Found in access_codes collection
        code_doc = docs[0]
        code_data = code_doc.to_dict()

        # Check if already used
        if code_data.get("used"):
            return AccessCodeValidateResponse(
                valid=False,
                message="Este código ya fue utilizado"
            )

        # Check expiration
        expires_at = code_data.get("expiresAt")
        if expires_at and isinstance(expires_at, datetime):
            if datetime.utcnow() > expires_at:
                return AccessCodeValidateResponse(
                    valid=False,
                    message="Este código ha expirado"
                )

        # Get student data
        student_id = code_data.get("studentId")
        student_data = await get_document("users", student_id)

        if not student_data:
            return AccessCodeValidateResponse(
                valid=False,
                message="Estudiante no encontrado"
            )

        # Mark code as used
        code_doc.reference.update({
            "used": True,
            "usedAt": datetime.utcnow(),
        })

    # Check if student is disabled
    if student_data.get("isDisabled") or student_data.get("is_disabled"):
        return AccessCodeValidateResponse(
            valid=False,
            message="Esta cuenta está deshabilitada"
        )

    # Get enrolled courses info
    enrolled_course_ids = student_data.get("enrolledCourses") or student_data.get("enrolled_courses", [])
    courses_info = []

    for course_id in enrolled_course_ids:
        course_data = await get_document("courses", course_id)
        if course_data:
            courses_info.append(CourseInfo(
                id=course_id,
                name=course_data.get("name") or course_data.get("title", ""),
                description=course_data.get("description"),
                level=course_data.get("level"),
            ))

    # Create JWT token for the student
    role = student_data.get("role", ["student"])
    if isinstance(role, str):
        role = [role]

    token_data = {
        "sub": student_id,
        "email": student_data.get("email"),
        "role": role,
    }
    access_token = create_access_token(token_data)

    # Build student info
    student_info = StudentInfo(
        id=student_id,
        email=student_data.get("email", ""),
        name=student_data.get("name", ""),
        student_level=student_data.get("studentLevel") or student_data.get("student_level"),
        enrolled_courses=enrolled_course_ids,
    )

    return AccessCodeValidateResponse(
        valid=True,
        message="Código validado exitosamente",
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        student=student_info,
        courses=courses_info,
    )


@router.get("", response_model=AccessCodeListResponse)
async def list_access_codes(
    student_id: Optional[str] = None,
    include_used: bool = False,
    current_user: dict = Depends(require_admin),
):
    """
    List all access codes
    Admin only
    """
    db = get_firestore()
    access_codes_ref = db.collection("access_codes")

    # Build query
    query = access_codes_ref

    if student_id:
        query = query.where("studentId", "==", student_id)

    if not include_used:
        query = query.where("used", "==", False)

    docs = list(query.stream())

    codes = [_code_to_response(doc.to_dict()) for doc in docs]

    return AccessCodeListResponse(
        codes=codes,
        total=len(codes),
    )


@router.delete("/{code}")
async def revoke_access_code(
    code: str,
    current_user: dict = Depends(require_admin),
):
    """
    Revoke/delete an access code
    Admin only
    """
    db = get_firestore()
    access_codes_ref = db.collection("access_codes")

    query = access_codes_ref.where("code", "==", code.upper()).limit(1)
    docs = list(query.stream())

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access code not found"
        )

    docs[0].reference.delete()

    return {"message": "Access code revoked successfully"}


@router.get("/student/{student_id}", response_model=Optional[AccessCodeResponse])
async def get_student_access_code(
    student_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Get the current active access code for a student
    Admin only
    """
    db = get_firestore()
    access_codes_ref = db.collection("access_codes")

    # Find active (unused) code for this student
    query = access_codes_ref.where("studentId", "==", student_id).where("used", "==", False).limit(1)
    docs = list(query.stream())

    if not docs:
        # Check if student has accessCode field
        student_data = await get_document("users", student_id)
        if student_data and student_data.get("accessCode"):
            return AccessCodeResponse(
                code=student_data.get("accessCode"),
                student_id=student_id,
                student_name=student_data.get("name", ""),
                created_at=student_data.get("accessCodeCreatedAt") or datetime.utcnow(),
                expires_at=None,
                used=False,
            )
        return None

    return _code_to_response(docs[0].to_dict())
