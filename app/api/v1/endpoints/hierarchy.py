"""
Course hierarchy endpoints
Levels → Modules → Sections → Lessons
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document

router = APIRouter()


class LessonContentType(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    QUIZ = "quiz"
    YOUTUBE = "youtube"


# ============== LEVEL SCHEMAS ==============
class LevelCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0


class LevelUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class LevelResponse(BaseModel):
    id: str
    course_id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    created_at: Optional[datetime] = None


# ============== MODULE SCHEMAS ==============
class ModuleCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0
    total_classes: int = 16


class ModuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    total_classes: Optional[int] = None


class ModuleResponse(BaseModel):
    id: str
    level_id: str
    course_id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    total_classes: int = 16
    created_at: Optional[datetime] = None


# ============== SECTION SCHEMAS ==============
class SectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0


class SectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class SectionResponse(BaseModel):
    id: str
    module_id: str
    level_id: str
    course_id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    created_at: Optional[datetime] = None


# ============== LESSON SCHEMAS ==============
class QuestionOption(BaseModel):
    text: str
    is_correct: bool = False


class Question(BaseModel):
    id: str
    question_text: str
    options: List[QuestionOption] = []
    explanation: Optional[str] = None


class LessonMaterial(BaseModel):
    id: str
    name: str
    url: str
    type: str  # pdf, doc, link


class LessonCreateRequest(BaseModel):
    name: str
    order: int = 0
    content_type: LessonContentType = LessonContentType.VIDEO
    video_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    lesson_body: Optional[str] = None  # HTML content for articles
    duration: Optional[str] = None
    questions: List[Question] = []
    materials: List[LessonMaterial] = []


class LessonUpdateRequest(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    content_type: Optional[LessonContentType] = None
    video_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    lesson_body: Optional[str] = None
    duration: Optional[str] = None
    questions: Optional[List[Question]] = None
    materials: Optional[List[LessonMaterial]] = None


class LessonResponse(BaseModel):
    id: str
    section_id: str
    module_id: str
    level_id: str
    course_id: str
    name: str
    order: int = 0
    content_type: str
    video_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    lesson_body: Optional[str] = None
    duration: Optional[str] = None
    questions: List[Question] = []
    materials: List[LessonMaterial] = []
    created_at: Optional[datetime] = None


# ============== HELPER FUNCTIONS ==============
def _get_course_ref(db, course_id: str):
    return db.collection("courses").document(course_id)


def _get_levels_ref(db, course_id: str):
    return _get_course_ref(db, course_id).collection("levels")


def _get_modules_ref(db, course_id: str, level_id: str):
    return _get_levels_ref(db, course_id).document(level_id).collection("modules")


def _get_sections_ref(db, course_id: str, level_id: str, module_id: str):
    return _get_modules_ref(db, course_id, level_id).document(module_id).collection("sections")


def _get_lessons_ref(db, course_id: str, level_id: str, module_id: str, section_id: str):
    return _get_sections_ref(db, course_id, level_id, module_id).document(section_id).collection("lessons")


# ============== LEVEL ENDPOINTS ==============
@router.get("/{course_id}/levels", response_model=List[LevelResponse])
async def list_levels(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all levels for a course"""
    db = get_firestore()

    # Verify course exists
    course = await get_document("courses", course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    levels_ref = _get_levels_ref(db, course_id)
    docs = list(levels_ref.order_by("order").stream())

    return [
        LevelResponse(
            id=doc.id,
            course_id=course_id,
            name=doc.to_dict().get("name", ""),
            description=doc.to_dict().get("description"),
            order=doc.to_dict().get("order", 0),
            created_at=doc.to_dict().get("createdAt"),
        )
        for doc in docs
    ]


@router.post("/{course_id}/levels", response_model=LevelResponse, status_code=201)
async def create_level(
    course_id: str,
    request: LevelCreateRequest,
    current_user: dict = Depends(require_author),
):
    """Create a new level"""
    db = get_firestore()

    course = await get_document("courses", course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    level_id = str(uuid.uuid4())
    level_data = {
        "name": request.name,
        "description": request.description,
        "order": request.order,
        "createdAt": datetime.utcnow(),
    }

    _get_levels_ref(db, course_id).document(level_id).set(level_data)

    return LevelResponse(
        id=level_id,
        course_id=course_id,
        **level_data,
        created_at=level_data["createdAt"],
    )


@router.get("/{course_id}/levels/{level_id}", response_model=LevelResponse)
async def get_level(
    course_id: str,
    level_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific level"""
    db = get_firestore()

    doc = _get_levels_ref(db, course_id).document(level_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Level not found")

    data = doc.to_dict()
    return LevelResponse(
        id=level_id,
        course_id=course_id,
        name=data.get("name", ""),
        description=data.get("description"),
        order=data.get("order", 0),
        created_at=data.get("createdAt"),
    )


@router.put("/{course_id}/levels/{level_id}", response_model=LevelResponse)
async def update_level(
    course_id: str,
    level_id: str,
    request: LevelUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """Update a level"""
    db = get_firestore()

    level_ref = _get_levels_ref(db, course_id).document(level_id)
    doc = level_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Level not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.order is not None:
        update_data["order"] = request.order

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        level_ref.update(update_data)

    updated = level_ref.get().to_dict()
    return LevelResponse(
        id=level_id,
        course_id=course_id,
        name=updated.get("name", ""),
        description=updated.get("description"),
        order=updated.get("order", 0),
        created_at=updated.get("createdAt"),
    )


@router.delete("/{course_id}/levels/{level_id}", status_code=204)
async def delete_level(
    course_id: str,
    level_id: str,
    current_user: dict = Depends(require_author),
):
    """Delete a level and all its children"""
    db = get_firestore()

    level_ref = _get_levels_ref(db, course_id).document(level_id)
    if not level_ref.get().exists:
        raise HTTPException(status_code=404, detail="Level not found")

    # Delete all modules (cascading)
    modules_ref = _get_modules_ref(db, course_id, level_id)
    for module_doc in modules_ref.stream():
        sections_ref = _get_sections_ref(db, course_id, level_id, module_doc.id)
        for section_doc in sections_ref.stream():
            lessons_ref = _get_lessons_ref(db, course_id, level_id, module_doc.id, section_doc.id)
            for lesson_doc in lessons_ref.stream():
                lesson_doc.reference.delete()
            section_doc.reference.delete()
        module_doc.reference.delete()

    level_ref.delete()


# ============== MODULE ENDPOINTS ==============
@router.get("/{course_id}/levels/{level_id}/modules", response_model=List[ModuleResponse])
async def list_modules(
    course_id: str,
    level_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all modules for a level"""
    db = get_firestore()

    modules_ref = _get_modules_ref(db, course_id, level_id)
    docs = list(modules_ref.order_by("order").stream())

    return [
        ModuleResponse(
            id=doc.id,
            level_id=level_id,
            course_id=course_id,
            name=doc.to_dict().get("name", ""),
            description=doc.to_dict().get("description"),
            order=doc.to_dict().get("order", 0),
            total_classes=doc.to_dict().get("totalClasses", 16),
            created_at=doc.to_dict().get("createdAt"),
        )
        for doc in docs
    ]


@router.post("/{course_id}/levels/{level_id}/modules", response_model=ModuleResponse, status_code=201)
async def create_module(
    course_id: str,
    level_id: str,
    request: ModuleCreateRequest,
    current_user: dict = Depends(require_author),
):
    """Create a new module"""
    db = get_firestore()

    # Verify level exists
    if not _get_levels_ref(db, course_id).document(level_id).get().exists:
        raise HTTPException(status_code=404, detail="Level not found")

    module_id = str(uuid.uuid4())
    module_data = {
        "name": request.name,
        "description": request.description,
        "order": request.order,
        "totalClasses": request.total_classes,
        "createdAt": datetime.utcnow(),
    }

    _get_modules_ref(db, course_id, level_id).document(module_id).set(module_data)

    return ModuleResponse(
        id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=module_data["name"],
        description=module_data["description"],
        order=module_data["order"],
        total_classes=module_data["totalClasses"],
        created_at=module_data["createdAt"],
    )


@router.put("/{course_id}/levels/{level_id}/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    course_id: str,
    level_id: str,
    module_id: str,
    request: ModuleUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """Update a module"""
    db = get_firestore()

    module_ref = _get_modules_ref(db, course_id, level_id).document(module_id)
    if not module_ref.get().exists:
        raise HTTPException(status_code=404, detail="Module not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.order is not None:
        update_data["order"] = request.order
    if request.total_classes is not None:
        update_data["totalClasses"] = request.total_classes

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        module_ref.update(update_data)

    updated = module_ref.get().to_dict()
    return ModuleResponse(
        id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=updated.get("name", ""),
        description=updated.get("description"),
        order=updated.get("order", 0),
        total_classes=updated.get("totalClasses", 16),
        created_at=updated.get("createdAt"),
    )


@router.delete("/{course_id}/levels/{level_id}/modules/{module_id}", status_code=204)
async def delete_module(
    course_id: str,
    level_id: str,
    module_id: str,
    current_user: dict = Depends(require_author),
):
    """Delete a module and all its children"""
    db = get_firestore()

    module_ref = _get_modules_ref(db, course_id, level_id).document(module_id)
    if not module_ref.get().exists:
        raise HTTPException(status_code=404, detail="Module not found")

    # Delete all sections (cascading)
    sections_ref = _get_sections_ref(db, course_id, level_id, module_id)
    for section_doc in sections_ref.stream():
        lessons_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_doc.id)
        for lesson_doc in lessons_ref.stream():
            lesson_doc.reference.delete()
        section_doc.reference.delete()

    module_ref.delete()


# ============== SECTION ENDPOINTS ==============
@router.get("/{course_id}/levels/{level_id}/modules/{module_id}/sections", response_model=List[SectionResponse])
async def list_sections(
    course_id: str,
    level_id: str,
    module_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all sections for a module"""
    db = get_firestore()

    sections_ref = _get_sections_ref(db, course_id, level_id, module_id)
    docs = list(sections_ref.order_by("order").stream())

    return [
        SectionResponse(
            id=doc.id,
            module_id=module_id,
            level_id=level_id,
            course_id=course_id,
            name=doc.to_dict().get("name", ""),
            description=doc.to_dict().get("description"),
            order=doc.to_dict().get("order", 0),
            created_at=doc.to_dict().get("createdAt"),
        )
        for doc in docs
    ]


@router.post("/{course_id}/levels/{level_id}/modules/{module_id}/sections", response_model=SectionResponse, status_code=201)
async def create_section(
    course_id: str,
    level_id: str,
    module_id: str,
    request: SectionCreateRequest,
    current_user: dict = Depends(require_author),
):
    """Create a new section"""
    db = get_firestore()

    # Verify module exists
    if not _get_modules_ref(db, course_id, level_id).document(module_id).get().exists:
        raise HTTPException(status_code=404, detail="Module not found")

    section_id = str(uuid.uuid4())
    section_data = {
        "name": request.name,
        "description": request.description,
        "order": request.order,
        "createdAt": datetime.utcnow(),
    }

    _get_sections_ref(db, course_id, level_id, module_id).document(section_id).set(section_data)

    return SectionResponse(
        id=section_id,
        module_id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=section_data["name"],
        description=section_data["description"],
        order=section_data["order"],
        created_at=section_data["createdAt"],
    )


@router.put("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    request: SectionUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """Update a section"""
    db = get_firestore()

    section_ref = _get_sections_ref(db, course_id, level_id, module_id).document(section_id)
    if not section_ref.get().exists:
        raise HTTPException(status_code=404, detail="Section not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.order is not None:
        update_data["order"] = request.order

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        section_ref.update(update_data)

    updated = section_ref.get().to_dict()
    return SectionResponse(
        id=section_id,
        module_id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=updated.get("name", ""),
        description=updated.get("description"),
        order=updated.get("order", 0),
        created_at=updated.get("createdAt"),
    )


@router.delete("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}", status_code=204)
async def delete_section(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    current_user: dict = Depends(require_author),
):
    """Delete a section and all its lessons"""
    db = get_firestore()

    section_ref = _get_sections_ref(db, course_id, level_id, module_id).document(section_id)
    if not section_ref.get().exists:
        raise HTTPException(status_code=404, detail="Section not found")

    # Delete all lessons
    lessons_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id)
    for lesson_doc in lessons_ref.stream():
        lesson_doc.reference.delete()

    section_ref.delete()


# ============== LESSON ENDPOINTS ==============
@router.get("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}/lessons", response_model=List[LessonResponse])
async def list_lessons(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all lessons for a section"""
    db = get_firestore()

    lessons_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id)
    docs = list(lessons_ref.order_by("order").stream())

    return [
        LessonResponse(
            id=doc.id,
            section_id=section_id,
            module_id=module_id,
            level_id=level_id,
            course_id=course_id,
            name=doc.to_dict().get("name", ""),
            order=doc.to_dict().get("order", 0),
            content_type=doc.to_dict().get("contentType", "video"),
            video_url=doc.to_dict().get("videoUrl"),
            youtube_video_id=doc.to_dict().get("youtubeVideoId"),
            lesson_body=doc.to_dict().get("lessonBody"),
            duration=doc.to_dict().get("duration"),
            questions=doc.to_dict().get("questions", []),
            materials=doc.to_dict().get("materials", []),
            created_at=doc.to_dict().get("createdAt"),
        )
        for doc in docs
    ]


@router.post("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}/lessons", response_model=LessonResponse, status_code=201)
async def create_lesson(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    request: LessonCreateRequest,
    current_user: dict = Depends(require_author),
):
    """Create a new lesson"""
    db = get_firestore()

    # Verify section exists
    if not _get_sections_ref(db, course_id, level_id, module_id).document(section_id).get().exists:
        raise HTTPException(status_code=404, detail="Section not found")

    lesson_id = str(uuid.uuid4())
    lesson_data = {
        "name": request.name,
        "order": request.order,
        "contentType": request.content_type.value,
        "videoUrl": request.video_url,
        "youtubeVideoId": request.youtube_video_id,
        "lessonBody": request.lesson_body,
        "duration": request.duration,
        "questions": [q.model_dump() for q in request.questions],
        "materials": [m.model_dump() for m in request.materials],
        "createdAt": datetime.utcnow(),
    }

    _get_lessons_ref(db, course_id, level_id, module_id, section_id).document(lesson_id).set(lesson_data)

    # Update course lessons count
    course_ref = _get_course_ref(db, course_id)
    course_data = course_ref.get().to_dict()
    meta = course_data.get("courseMeta", {})
    meta["lessonsCount"] = meta.get("lessonsCount", 0) + 1
    course_ref.update({"courseMeta": meta})

    return LessonResponse(
        id=lesson_id,
        section_id=section_id,
        module_id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=lesson_data["name"],
        order=lesson_data["order"],
        content_type=lesson_data["contentType"],
        video_url=lesson_data["videoUrl"],
        youtube_video_id=lesson_data["youtubeVideoId"],
        lesson_body=lesson_data["lessonBody"],
        duration=lesson_data["duration"],
        questions=request.questions,
        materials=request.materials,
        created_at=lesson_data["createdAt"],
    )


@router.get("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific lesson"""
    db = get_firestore()

    lesson_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id).document(lesson_id)
    doc = lesson_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Lesson not found")

    data = doc.to_dict()
    return LessonResponse(
        id=lesson_id,
        section_id=section_id,
        module_id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=data.get("name", ""),
        order=data.get("order", 0),
        content_type=data.get("contentType", "video"),
        video_url=data.get("videoUrl"),
        youtube_video_id=data.get("youtubeVideoId"),
        lesson_body=data.get("lessonBody"),
        duration=data.get("duration"),
        questions=data.get("questions", []),
        materials=data.get("materials", []),
        created_at=data.get("createdAt"),
    )


@router.put("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    lesson_id: str,
    request: LessonUpdateRequest,
    current_user: dict = Depends(require_author),
):
    """Update a lesson"""
    db = get_firestore()

    lesson_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id).document(lesson_id)
    if not lesson_ref.get().exists:
        raise HTTPException(status_code=404, detail="Lesson not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.order is not None:
        update_data["order"] = request.order
    if request.content_type is not None:
        update_data["contentType"] = request.content_type.value
    if request.video_url is not None:
        update_data["videoUrl"] = request.video_url
    if request.youtube_video_id is not None:
        update_data["youtubeVideoId"] = request.youtube_video_id
    if request.lesson_body is not None:
        update_data["lessonBody"] = request.lesson_body
    if request.duration is not None:
        update_data["duration"] = request.duration
    if request.questions is not None:
        update_data["questions"] = [q.model_dump() for q in request.questions]
    if request.materials is not None:
        update_data["materials"] = [m.model_dump() for m in request.materials]

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        lesson_ref.update(update_data)

    updated = lesson_ref.get().to_dict()
    return LessonResponse(
        id=lesson_id,
        section_id=section_id,
        module_id=module_id,
        level_id=level_id,
        course_id=course_id,
        name=updated.get("name", ""),
        order=updated.get("order", 0),
        content_type=updated.get("contentType", "video"),
        video_url=updated.get("videoUrl"),
        youtube_video_id=updated.get("youtubeVideoId"),
        lesson_body=updated.get("lessonBody"),
        duration=updated.get("duration"),
        questions=updated.get("questions", []),
        materials=updated.get("materials", []),
        created_at=updated.get("createdAt"),
    )


@router.delete("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}/lessons/{lesson_id}", status_code=204)
async def delete_lesson(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    lesson_id: str,
    current_user: dict = Depends(require_author),
):
    """Delete a lesson"""
    db = get_firestore()

    lesson_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id).document(lesson_id)
    if not lesson_ref.get().exists:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson_ref.delete()

    # Update course lessons count
    course_ref = _get_course_ref(db, course_id)
    course_data = course_ref.get().to_dict()
    meta = course_data.get("courseMeta", {})
    meta["lessonsCount"] = max(0, meta.get("lessonsCount", 1) - 1)
    course_ref.update({"courseMeta": meta})
