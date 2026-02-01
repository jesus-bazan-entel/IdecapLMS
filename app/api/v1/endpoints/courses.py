"""
Courses management endpoints
CRUD operations for courses
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.core.security import get_current_user, require_admin, require_author
from app.core.firebase_admin import (
    get_firestore,
    get_document,
    get_collection,
    create_document,
    update_document,
    delete_document,
)

router = APIRouter()


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    LIVE = "live"
    ARCHIVE = "archive"


class PriceStatus(str, Enum):
    FREE = "free"
    PREMIUM = "premium"


# Request/Response schemas
class AuthorInfo(BaseModel):
    """Author information"""
    id: str
    name: str
    image_url: Optional[str] = None


class CourseMeta(BaseModel):
    """Course metadata"""
    duration: Optional[str] = None
    enrollment: int = 0
    rating: float = 0.0
    total_reviews: int = 0
    lessons_count: int = 0


class CourseCreateRequest(BaseModel):
    """Create course request"""
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    price_status: PriceStatus = PriceStatus.FREE
    price: float = 0.0
    category_id: Optional[str] = None
    tag_ids: List[str] = []
    language: str = "es"
    summary: Optional[str] = None


class CourseUpdateRequest(BaseModel):
    """Update course request"""
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[CourseStatus] = None
    price_status: Optional[PriceStatus] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    tag_ids: Optional[List[str]] = None
    language: Optional[str] = None
    summary: Optional[str] = None


class CourseResponse(BaseModel):
    """Course response"""
    id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str
    price_status: str
    price: float = 0.0
    author: Optional[AuthorInfo] = None
    course_meta: Optional[CourseMeta] = None
    category_id: Optional[str] = None
    tag_ids: List[str] = []
    tutor_ids: List[str] = []
    language: str = "es"
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CourseListResponse(BaseModel):
    """Paginated course list response"""
    courses: List[CourseResponse]
    total: int
    page: int
    page_size: int


class TutorAssignRequest(BaseModel):
    """Assign tutor to course request"""
    tutor_id: str


def _course_to_response(course_id: str, data: dict) -> CourseResponse:
    """Convert Firestore course data to response"""
    author_data = data.get("author")
    author = None
    if author_data:
        author = AuthorInfo(
            id=author_data.get("id", ""),
            name=author_data.get("name", ""),
            image_url=author_data.get("imageUrl") or author_data.get("image_url"),
        )

    meta_data = data.get("courseMeta") or data.get("course_meta")
    course_meta = None
    if meta_data:
        course_meta = CourseMeta(
            duration=meta_data.get("duration"),
            enrollment=meta_data.get("enrollment", 0),
            rating=meta_data.get("rating", 0.0),
            total_reviews=meta_data.get("totalReviews") or meta_data.get("total_reviews", 0),
            lessons_count=meta_data.get("lessonsCount") or meta_data.get("lessons_count", 0),
        )

    return CourseResponse(
        id=course_id,
        name=data.get("name") or "",
        description=data.get("description"),
        thumbnail_url=data.get("thumbnailUrl") or data.get("thumbnail_url"),
        status=data.get("status") or "draft",
        price_status=data.get("priceStatus") or data.get("price_status") or "free",
        price=data.get("price") or 0.0,
        author=author,
        course_meta=course_meta,
        category_id=data.get("categoryId") or data.get("category_id"),
        tag_ids=data.get("tagIds") or data.get("tag_ids") or [],
        tutor_ids=data.get("tutorIds") or data.get("tutor_ids") or [],
        language=data.get("language") or "es",
        summary=data.get("summary"),
        created_at=data.get("createdAt") or data.get("created_at"),
        updated_at=data.get("updatedAt") or data.get("updated_at"),
    )


@router.get("", response_model=CourseListResponse)
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[CourseStatus] = None,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List all courses with pagination
    """
    db = get_firestore()
    courses_ref = db.collection("courses")

    # Build query
    query = courses_ref

    if status:
        query = query.where("status", "==", status.value)

    if category_id:
        query = query.where("categoryId", "==", category_id)

    docs = list(query.stream())

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        docs = [
            doc for doc in docs
            if search_lower in doc.to_dict().get("name", "").lower()
            or search_lower in (doc.to_dict().get("description") or "").lower()
        ]

    total = len(docs)

    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_docs = docs[start:end]

    courses = [
        _course_to_response(doc.id, doc.to_dict())
        for doc in paginated_docs
    ]

    return CourseListResponse(
        courses=courses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get course by ID
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    return _course_to_response(course_id, course_data)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    request: CourseCreateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Create a new course
    Author or Admin only
    """
    db = get_firestore()
    import uuid

    course_id = str(uuid.uuid4())

    # Get author info
    author_data = {
        "id": current_user["id"],
        "name": current_user.get("name", ""),
        "imageUrl": current_user.get("image_url"),
    }

    course_data = {
        "name": request.name,
        "description": request.description,
        "thumbnailUrl": request.thumbnail_url,
        "status": request.status.value,
        "priceStatus": request.price_status.value,
        "price": request.price,
        "author": author_data,
        "courseMeta": {
            "duration": None,
            "enrollment": 0,
            "rating": 0.0,
            "totalReviews": 0,
            "lessonsCount": 0,
        },
        "categoryId": request.category_id,
        "tagIds": request.tag_ids,
        "tutorIds": [],
        "language": request.language,
        "summary": request.summary,
        "createdAt": datetime.utcnow(),
    }

    db.collection("courses").document(course_id).set(course_data)

    return _course_to_response(course_id, course_data)


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    request: CourseUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Update course by ID
    Author or Admin only
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Build update data
    update_data = {}

    if request.name is not None:
        update_data["name"] = request.name

    if request.description is not None:
        update_data["description"] = request.description

    if request.thumbnail_url is not None:
        update_data["thumbnailUrl"] = request.thumbnail_url

    if request.status is not None:
        update_data["status"] = request.status.value

    if request.price_status is not None:
        update_data["priceStatus"] = request.price_status.value

    if request.price is not None:
        update_data["price"] = request.price

    if request.category_id is not None:
        update_data["categoryId"] = request.category_id

    if request.tag_ids is not None:
        update_data["tagIds"] = request.tag_ids

    if request.language is not None:
        update_data["language"] = request.language

    if request.summary is not None:
        update_data["summary"] = request.summary

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("courses", course_id, update_data)

    # Return updated course
    updated_course = await get_document("courses", course_id)
    return _course_to_response(course_id, updated_course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Delete course by ID
    Admin only
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Delete course and all subcollections
    db = get_firestore()

    # Delete levels subcollection (which cascades to modules, sections, lessons)
    levels_ref = db.collection("courses").document(course_id).collection("levels")
    for level_doc in levels_ref.stream():
        # Delete modules
        modules_ref = levels_ref.document(level_doc.id).collection("modules")
        for module_doc in modules_ref.stream():
            # Delete sections
            sections_ref = modules_ref.document(module_doc.id).collection("sections")
            for section_doc in sections_ref.stream():
                # Delete lessons
                lessons_ref = sections_ref.document(section_doc.id).collection("lessons")
                for lesson_doc in lessons_ref.stream():
                    lesson_doc.reference.delete()
                section_doc.reference.delete()
            module_doc.reference.delete()
        level_doc.reference.delete()

    # Delete the course document
    await delete_document("courses", course_id)


@router.post("/{course_id}/publish", response_model=CourseResponse)
async def publish_course(
    course_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Publish course (set status to live)
    Author or Admin only
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    await update_document("courses", course_id, {
        "status": CourseStatus.LIVE.value,
        "updatedAt": datetime.utcnow(),
    })

    updated_course = await get_document("courses", course_id)
    return _course_to_response(course_id, updated_course)


@router.post("/{course_id}/archive", response_model=CourseResponse)
async def archive_course(
    course_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Archive course
    Author or Admin only
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    await update_document("courses", course_id, {
        "status": CourseStatus.ARCHIVE.value,
        "updatedAt": datetime.utcnow(),
    })

    updated_course = await get_document("courses", course_id)
    return _course_to_response(course_id, updated_course)


@router.post("/{course_id}/tutors", response_model=CourseResponse)
async def assign_tutor(
    course_id: str,
    request: TutorAssignRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Assign tutor to course
    Admin only
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Verify tutor exists and has tutor role
    tutor_data = await get_document("users", request.tutor_id)
    if not tutor_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutor not found"
        )

    tutor_role = tutor_data.get("role", [])
    if isinstance(tutor_role, str):
        tutor_role = [tutor_role]

    if "tutor" not in tutor_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a tutor"
        )

    # Add tutor to course
    tutor_ids = course_data.get("tutorIds") or course_data.get("tutor_ids", [])
    if request.tutor_id not in tutor_ids:
        tutor_ids.append(request.tutor_id)

    await update_document("courses", course_id, {
        "tutorIds": tutor_ids,
        "updatedAt": datetime.utcnow(),
    })

    # Also add course to tutor's assigned courses
    assigned = tutor_data.get("assignedCourses") or tutor_data.get("assigned_courses", [])
    if course_id not in assigned:
        assigned.append(course_id)
        await update_document("users", request.tutor_id, {
            "assignedCourses": assigned,
        })

    updated_course = await get_document("courses", course_id)
    return _course_to_response(course_id, updated_course)


@router.delete("/{course_id}/tutors/{tutor_id}", response_model=CourseResponse)
async def remove_tutor(
    course_id: str,
    tutor_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Remove tutor from course
    Admin only
    """
    course_data = await get_document("courses", course_id)

    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Remove tutor from course
    tutor_ids = course_data.get("tutorIds") or course_data.get("tutor_ids", [])
    if tutor_id in tutor_ids:
        tutor_ids.remove(tutor_id)

    await update_document("courses", course_id, {
        "tutorIds": tutor_ids,
        "updatedAt": datetime.utcnow(),
    })

    # Also remove course from tutor's assigned courses
    tutor_data = await get_document("users", tutor_id)
    if tutor_data:
        assigned = tutor_data.get("assignedCourses") or tutor_data.get("assigned_courses", [])
        if course_id in assigned:
            assigned.remove(course_id)
            await update_document("users", tutor_id, {
                "assignedCourses": assigned,
            })

    updated_course = await get_document("courses", course_id)
    return _course_to_response(course_id, updated_course)
