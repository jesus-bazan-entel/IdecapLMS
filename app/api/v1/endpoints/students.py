"""
Students management endpoints
Enrollment, QR codes, payment status
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum
import io
import hashlib
import qrcode

from app.core.security import get_current_user, require_admin, get_password_hash
from app.core.firebase_admin import (
    get_firestore,
    get_document,
    update_document,
    delete_document,
)

router = APIRouter()


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    FREE = "free"


class StudentLevel(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# Request/Response schemas
class StudentEnrollRequest(BaseModel):
    """Enroll new student request"""
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    student_level: StudentLevel = StudentLevel.BASIC
    student_section: Optional[str] = None
    course_ids: List[str] = []
    payment_status: PaymentStatus = PaymentStatus.PENDING


class StudentUpdateRequest(BaseModel):
    """Update student request"""
    name: Optional[str] = None
    phone: Optional[str] = None
    student_level: Optional[StudentLevel] = None
    student_section: Optional[str] = None
    payment_status: Optional[PaymentStatus] = None
    payment_date: Optional[datetime] = None
    payment_amount: Optional[float] = None


class StudentResponse(BaseModel):
    """Student response"""
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    image_url: Optional[str] = None
    student_level: Optional[str] = None
    student_section: Optional[str] = None
    enrolled_courses: List[str] = []
    payment_status: Optional[str] = None
    payment_date: Optional[datetime] = None
    payment_amount: Optional[float] = None
    qr_code_hash: Optional[str] = None
    is_disabled: bool = False
    created_at: Optional[datetime] = None


class StudentListResponse(BaseModel):
    """Paginated student list response"""
    students: List[StudentResponse]
    total: int
    page: int
    page_size: int


class QRVerifyRequest(BaseModel):
    """QR code verification request"""
    qr_code: str


class QRVerifyResponse(BaseModel):
    """QR code verification response"""
    valid: bool
    student: Optional[StudentResponse] = None
    message: str


def _student_to_response(student_id: str, data: dict) -> StudentResponse:
    """Convert Firestore student data to response"""
    return StudentResponse(
        id=student_id,
        email=data.get("email", ""),
        name=data.get("name", ""),
        phone=data.get("phone"),
        image_url=data.get("imageUrl") or data.get("image_url"),
        student_level=data.get("studentLevel") or data.get("student_level"),
        student_section=data.get("studentSection") or data.get("student_section"),
        enrolled_courses=data.get("enrolledCourses") or data.get("enrolled_courses", []),
        payment_status=data.get("paymentStatus") or data.get("payment_status"),
        payment_date=data.get("paymentDate") or data.get("payment_date"),
        payment_amount=data.get("paymentAmount") or data.get("payment_amount"),
        qr_code_hash=data.get("qrCodeHash") or data.get("qr_code_hash"),
        is_disabled=data.get("isDisabled") or data.get("is_disabled", False),
        created_at=data.get("createdAt") or data.get("created_at"),
    )


def _generate_qr_hash(student_id: str, email: str) -> str:
    """Generate unique QR code hash for student"""
    data = f"{student_id}:{email}:{datetime.utcnow().timestamp()}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def _generate_qr_image(data: str) -> bytes:
    """Generate QR code image as PNG bytes"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    return img_buffer.getvalue()


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    payment_status: Optional[PaymentStatus] = None,
    student_level: Optional[StudentLevel] = None,
    search: Optional[str] = None,
    course_id: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    """
    List all students with pagination and filters
    Admin only
    """
    db = get_firestore()
    users_ref = db.collection("users")

    # Query users with student role
    query = users_ref.where("role", "array_contains", "student")

    docs = list(query.stream())

    # Apply filters
    filtered_docs = []
    for doc in docs:
        data = doc.to_dict()

        # Filter by payment status
        if payment_status:
            doc_payment = data.get("paymentStatus") or data.get("payment_status")
            if doc_payment != payment_status.value:
                continue

        # Filter by student level
        if student_level:
            doc_level = data.get("studentLevel") or data.get("student_level")
            if doc_level != student_level.value:
                continue

        # Filter by course
        if course_id:
            enrolled = data.get("enrolledCourses") or data.get("enrolled_courses", [])
            if course_id not in enrolled:
                continue

        # Filter by search
        if search:
            search_lower = search.lower()
            name = data.get("name", "").lower()
            email = data.get("email", "").lower()
            if search_lower not in name and search_lower not in email:
                continue

        filtered_docs.append(doc)

    total = len(filtered_docs)

    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_docs = filtered_docs[start:end]

    students = [
        _student_to_response(doc.id, doc.to_dict())
        for doc in paginated_docs
    ]

    return StudentListResponse(
        students=students,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Get student by ID
    Admin only
    """
    student_data = await get_document("users", student_id)

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    return _student_to_response(student_id, student_data)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student(
    request: StudentEnrollRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Enroll a new student
    Admin only
    """
    db = get_firestore()

    # Check if email already exists
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", request.email).limit(1)
    docs = list(query.stream())

    if docs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create student document
    import uuid
    student_id = str(uuid.uuid4())
    password_hash = get_password_hash(request.password)
    qr_hash = _generate_qr_hash(student_id, request.email)

    student_data = {
        "email": request.email,
        "name": request.name,
        "passwordHash": password_hash,
        "role": ["student"],
        "phone": request.phone,
        "studentLevel": request.student_level.value,
        "studentSection": request.student_section,
        "enrolledCourses": request.course_ids,
        "paymentStatus": request.payment_status.value,
        "qrCodeHash": qr_hash,
        "createdAt": datetime.utcnow(),
        "platform": "web",
        "isDisabled": False,
    }

    db.collection("users").document(student_id).set(student_data)

    return _student_to_response(student_id, student_data)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    request: StudentUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Update student by ID
    Admin only
    """
    student_data = await get_document("users", student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Build update data
    update_data = {}

    if request.name is not None:
        update_data["name"] = request.name

    if request.phone is not None:
        update_data["phone"] = request.phone

    if request.student_level is not None:
        update_data["studentLevel"] = request.student_level.value

    if request.student_section is not None:
        update_data["studentSection"] = request.student_section

    if request.payment_status is not None:
        update_data["paymentStatus"] = request.payment_status.value

    if request.payment_date is not None:
        update_data["paymentDate"] = request.payment_date

    if request.payment_amount is not None:
        update_data["paymentAmount"] = request.payment_amount

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("users", student_id, update_data)

    # Return updated student
    updated_student = await get_document("users", student_id)
    return _student_to_response(student_id, updated_student)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Delete a student
    Admin only
    """
    student_data = await get_document("users", student_id)

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Delete the student document
    await delete_document("users", student_id)

    # Also delete associated access codes
    db = get_firestore()
    access_codes_ref = db.collection("access_codes")
    codes = list(access_codes_ref.where("studentId", "==", student_id).stream())
    for code_doc in codes:
        code_doc.reference.delete()

    return None


@router.put("/{student_id}/payment", response_model=StudentResponse)
async def update_payment_status(
    student_id: str,
    payment_status: PaymentStatus,
    payment_amount: Optional[float] = None,
    current_user: dict = Depends(require_admin),
):
    """
    Update student payment status
    Admin only
    """
    student_data = await get_document("users", student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    update_data = {
        "paymentStatus": payment_status.value,
        "updatedAt": datetime.utcnow(),
    }

    if payment_status == PaymentStatus.PAID:
        update_data["paymentDate"] = datetime.utcnow()

    if payment_amount is not None:
        update_data["paymentAmount"] = payment_amount

    await update_document("users", student_id, update_data)

    updated_student = await get_document("users", student_id)
    return _student_to_response(student_id, updated_student)


@router.post("/{student_id}/courses/{course_id}", response_model=StudentResponse)
async def enroll_in_course(
    student_id: str,
    course_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Enroll student in a course
    Admin only
    """
    student_data = await get_document("users", student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Verify course exists
    course_data = await get_document("courses", course_id)
    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Add course to enrolled courses
    enrolled = student_data.get("enrolledCourses") or student_data.get("enrolled_courses", [])
    if course_id not in enrolled:
        enrolled.append(course_id)

    await update_document("users", student_id, {
        "enrolledCourses": enrolled,
        "updatedAt": datetime.utcnow(),
    })

    updated_student = await get_document("users", student_id)
    return _student_to_response(student_id, updated_student)


@router.delete("/{student_id}/courses/{course_id}", response_model=StudentResponse)
async def unenroll_from_course(
    student_id: str,
    course_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Unenroll student from a course
    Admin only
    """
    student_data = await get_document("users", student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Remove course from enrolled courses
    enrolled = student_data.get("enrolledCourses") or student_data.get("enrolled_courses", [])
    if course_id in enrolled:
        enrolled.remove(course_id)

    await update_document("users", student_id, {
        "enrolledCourses": enrolled,
        "updatedAt": datetime.utcnow(),
    })

    updated_student = await get_document("users", student_id)
    return _student_to_response(student_id, updated_student)


@router.get("/{student_id}/qr")
async def get_qr_code(
    student_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Get student QR code as PNG image
    Admin only
    """
    student_data = await get_document("users", student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    qr_hash = student_data.get("qrCodeHash") or student_data.get("qr_code_hash")

    if not qr_hash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not generated for this student"
        )

    # Generate QR code image
    qr_data = f"APOLO:{student_id}:{qr_hash}"
    qr_image = _generate_qr_image(qr_data)

    return StreamingResponse(
        io.BytesIO(qr_image),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=qr_{student_id}.png"}
    )


@router.post("/{student_id}/qr", response_model=StudentResponse)
async def regenerate_qr_code(
    student_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Regenerate student QR code
    Admin only
    """
    student_data = await get_document("users", student_id)

    if not student_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Generate new QR hash
    email = student_data.get("email", "")
    new_qr_hash = _generate_qr_hash(student_id, email)

    await update_document("users", student_id, {
        "qrCodeHash": new_qr_hash,
        "updatedAt": datetime.utcnow(),
    })

    updated_student = await get_document("users", student_id)
    return _student_to_response(student_id, updated_student)


@router.post("/qr/verify", response_model=QRVerifyResponse)
async def verify_qr_code(
    request: QRVerifyRequest,
):
    """
    Verify student QR code for login
    Public endpoint for QR scanner
    """
    qr_code = request.qr_code

    # Parse QR code format: APOLO:{student_id}:{qr_hash}
    if not qr_code.startswith("APOLO:"):
        return QRVerifyResponse(
            valid=False,
            message="Invalid QR code format"
        )

    parts = qr_code.split(":")
    if len(parts) != 3:
        return QRVerifyResponse(
            valid=False,
            message="Invalid QR code format"
        )

    student_id = parts[1]
    qr_hash = parts[2]

    # Verify student exists and QR matches
    student_data = await get_document("users", student_id)

    if not student_data:
        return QRVerifyResponse(
            valid=False,
            message="Student not found"
        )

    stored_hash = student_data.get("qrCodeHash") or student_data.get("qr_code_hash")

    if stored_hash != qr_hash:
        return QRVerifyResponse(
            valid=False,
            message="QR code expired or invalid"
        )

    # Check if student is disabled
    if student_data.get("isDisabled") or student_data.get("is_disabled"):
        return QRVerifyResponse(
            valid=False,
            message="Account is disabled"
        )

    return QRVerifyResponse(
        valid=True,
        student=_student_to_response(student_id, student_data),
        message="QR code verified successfully"
    )
