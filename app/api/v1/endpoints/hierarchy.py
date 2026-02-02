"""
Course hierarchy endpoints
Levels → Modules → Sections → Lessons
With metadata and progression rules for Learning Path
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document

router = APIRouter()


# ============== ENUMS ==============
class LessonContentType(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    QUIZ = "quiz"
    YOUTUBE = "youtube"
    AUDIO = "audio"
    IA = "ia"


class Difficulty(str, Enum):
    BASICO = "basico"
    INTERMEDIO = "intermedio"
    AVANZADO = "avanzado"


# ============== SHARED SCHEMAS ==============
class NodeMetadata(BaseModel):
    """Metadata for learning path nodes"""
    objective: Optional[str] = None
    estimated_minutes: Optional[int] = None
    difficulty: Optional[Difficulty] = None
    tags: Optional[List[str]] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class ProgressionRules(BaseModel):
    """Rules for progression through the learning path"""
    require_previous_completion: bool = True
    minimum_score_percent: Optional[int] = None
    minimum_completion_percent: Optional[int] = None
    minimum_duration_days: Optional[int] = None


class ReorderRequest(BaseModel):
    """Request to reorder items"""
    order: List[str]  # List of IDs in new order


# ============== LEVEL SCHEMAS ==============
class LevelCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


class LevelUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


class LevelResponse(BaseModel):
    id: str
    course_id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    created_at: Optional[datetime] = None
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


# ============== MODULE SCHEMAS ==============
class ModuleCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0
    total_classes: int = 16
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


class ModuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    total_classes: Optional[int] = None
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


class ModuleResponse(BaseModel):
    id: str
    level_id: str
    course_id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    total_classes: int = 16
    created_at: Optional[datetime] = None
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


# ============== SECTION SCHEMAS ==============
class SectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


class SectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


class SectionResponse(BaseModel):
    id: str
    module_id: str
    level_id: str
    course_id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    created_at: Optional[datetime] = None
    metadata: Optional[NodeMetadata] = None
    progression_rules: Optional[ProgressionRules] = None


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
    lesson_body: Optional[str] = None
    duration: Optional[str] = None
    questions: List[Question] = []
    materials: List[LessonMaterial] = []
    metadata: Optional[NodeMetadata] = None


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
    metadata: Optional[NodeMetadata] = None


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
    metadata: Optional[NodeMetadata] = None


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


def _parse_metadata(data: dict) -> Optional[NodeMetadata]:
    """Parse metadata from Firestore document"""
    meta = data.get("metadata")
    if not meta:
        return None
    return NodeMetadata(
        objective=meta.get("objective"),
        estimated_minutes=meta.get("estimatedMinutes") or meta.get("estimated_minutes"),
        difficulty=meta.get("difficulty"),
        tags=meta.get("tags"),
        icon=meta.get("icon"),
        color=meta.get("color"),
    )


def _parse_progression_rules(data: dict) -> Optional[ProgressionRules]:
    """Parse progression rules from Firestore document"""
    rules = data.get("progressionRules") or data.get("progression_rules")
    if not rules:
        return None
    return ProgressionRules(
        require_previous_completion=rules.get("requirePreviousCompletion", rules.get("require_previous_completion", True)),
        minimum_score_percent=rules.get("minimumScorePercent") or rules.get("minimum_score_percent"),
        minimum_completion_percent=rules.get("minimumCompletionPercent") or rules.get("minimum_completion_percent"),
        minimum_duration_days=rules.get("minimumDurationDays") or rules.get("minimum_duration_days"),
    )


def _metadata_to_firestore(metadata: Optional[NodeMetadata]) -> Optional[dict]:
    """Convert metadata to Firestore format"""
    if not metadata:
        return None
    return {
        "objective": metadata.objective,
        "estimatedMinutes": metadata.estimated_minutes,
        "difficulty": metadata.difficulty.value if metadata.difficulty else None,
        "tags": metadata.tags,
        "icon": metadata.icon,
        "color": metadata.color,
    }


def _progression_rules_to_firestore(rules: Optional[ProgressionRules]) -> Optional[dict]:
    """Convert progression rules to Firestore format"""
    if not rules:
        return None
    return {
        "requirePreviousCompletion": rules.require_previous_completion,
        "minimumScorePercent": rules.minimum_score_percent,
        "minimumCompletionPercent": rules.minimum_completion_percent,
        "minimumDurationDays": rules.minimum_duration_days,
    }


# ============== UTILITY ENDPOINTS ==============

@router.post("/{course_id}/recalculate-lessons")
async def recalculate_lessons_count(
    course_id: str,
    current_user: dict = Depends(require_author),
):
    """Recalculate the lesson count for a course by counting all lessons in hierarchy"""
    db = get_firestore()

    course_ref = _get_course_ref(db, course_id)
    course = course_ref.get()
    if not course.exists:
        raise HTTPException(status_code=404, detail="Course not found")

    # Count all lessons in all levels > modules > sections
    total_lessons = 0
    levels_ref = _get_levels_ref(db, course_id)
    for level_doc in levels_ref.stream():
        modules_ref = _get_modules_ref(db, course_id, level_doc.id)
        for module_doc in modules_ref.stream():
            sections_ref = _get_sections_ref(db, course_id, level_doc.id, module_doc.id)
            for section_doc in sections_ref.stream():
                lessons_ref = _get_lessons_ref(db, course_id, level_doc.id, module_doc.id, section_doc.id)
                for _ in lessons_ref.stream():
                    total_lessons += 1

    # Update the course meta
    course_data = course.to_dict()
    meta = course_data.get("courseMeta", {})
    meta["lessonsCount"] = total_lessons
    course_ref.update({"courseMeta": meta})

    return {"course_id": course_id, "lessons_count": total_lessons, "message": "Lesson count updated"}


# ============== LEVEL ENDPOINTS ==============
@router.get("/{course_id}/levels", response_model=List[LevelResponse])
async def list_levels(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all levels for a course"""
    db = get_firestore()

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
            metadata=_parse_metadata(doc.to_dict()),
            progression_rules=_parse_progression_rules(doc.to_dict()),
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

    if request.metadata:
        level_data["metadata"] = _metadata_to_firestore(request.metadata)
    if request.progression_rules:
        level_data["progressionRules"] = _progression_rules_to_firestore(request.progression_rules)

    _get_levels_ref(db, course_id).document(level_id).set(level_data)

    return LevelResponse(
        id=level_id,
        course_id=course_id,
        name=level_data["name"],
        description=level_data["description"],
        order=level_data["order"],
        created_at=level_data["createdAt"],
        metadata=request.metadata,
        progression_rules=request.progression_rules,
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
        metadata=_parse_metadata(data),
        progression_rules=_parse_progression_rules(data),
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
    if request.metadata is not None:
        update_data["metadata"] = _metadata_to_firestore(request.metadata)
    if request.progression_rules is not None:
        update_data["progressionRules"] = _progression_rules_to_firestore(request.progression_rules)

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
        metadata=_parse_metadata(updated),
        progression_rules=_parse_progression_rules(updated),
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


@router.post("/{course_id}/levels/reorder", status_code=200)
async def reorder_levels(
    course_id: str,
    request: ReorderRequest,
    current_user: dict = Depends(require_author),
):
    """Reorder levels"""
    db = get_firestore()

    course = await get_document("courses", course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    levels_ref = _get_levels_ref(db, course_id)

    for index, level_id in enumerate(request.order):
        levels_ref.document(level_id).update({"order": index, "updatedAt": datetime.utcnow()})

    return {"message": "Levels reordered successfully"}


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
            metadata=_parse_metadata(doc.to_dict()),
            progression_rules=_parse_progression_rules(doc.to_dict()),
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

    if request.metadata:
        module_data["metadata"] = _metadata_to_firestore(request.metadata)
    if request.progression_rules:
        module_data["progressionRules"] = _progression_rules_to_firestore(request.progression_rules)

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
        metadata=request.metadata,
        progression_rules=request.progression_rules,
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
    if request.metadata is not None:
        update_data["metadata"] = _metadata_to_firestore(request.metadata)
    if request.progression_rules is not None:
        update_data["progressionRules"] = _progression_rules_to_firestore(request.progression_rules)

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
        metadata=_parse_metadata(updated),
        progression_rules=_parse_progression_rules(updated),
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

    sections_ref = _get_sections_ref(db, course_id, level_id, module_id)
    for section_doc in sections_ref.stream():
        lessons_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_doc.id)
        for lesson_doc in lessons_ref.stream():
            lesson_doc.reference.delete()
        section_doc.reference.delete()

    module_ref.delete()


@router.post("/{course_id}/levels/{level_id}/modules/reorder", status_code=200)
async def reorder_modules(
    course_id: str,
    level_id: str,
    request: ReorderRequest,
    current_user: dict = Depends(require_author),
):
    """Reorder modules within a level"""
    db = get_firestore()

    modules_ref = _get_modules_ref(db, course_id, level_id)

    for index, module_id in enumerate(request.order):
        modules_ref.document(module_id).update({"order": index, "updatedAt": datetime.utcnow()})

    return {"message": "Modules reordered successfully"}


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
            metadata=_parse_metadata(doc.to_dict()),
            progression_rules=_parse_progression_rules(doc.to_dict()),
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

    if not _get_modules_ref(db, course_id, level_id).document(module_id).get().exists:
        raise HTTPException(status_code=404, detail="Module not found")

    section_id = str(uuid.uuid4())
    section_data = {
        "name": request.name,
        "description": request.description,
        "order": request.order,
        "createdAt": datetime.utcnow(),
    }

    if request.metadata:
        section_data["metadata"] = _metadata_to_firestore(request.metadata)
    if request.progression_rules:
        section_data["progressionRules"] = _progression_rules_to_firestore(request.progression_rules)

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
        metadata=request.metadata,
        progression_rules=request.progression_rules,
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
    if request.metadata is not None:
        update_data["metadata"] = _metadata_to_firestore(request.metadata)
    if request.progression_rules is not None:
        update_data["progressionRules"] = _progression_rules_to_firestore(request.progression_rules)

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
        metadata=_parse_metadata(updated),
        progression_rules=_parse_progression_rules(updated),
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

    lessons_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id)
    for lesson_doc in lessons_ref.stream():
        lesson_doc.reference.delete()

    section_ref.delete()


@router.post("/{course_id}/levels/{level_id}/modules/{module_id}/sections/reorder", status_code=200)
async def reorder_sections(
    course_id: str,
    level_id: str,
    module_id: str,
    request: ReorderRequest,
    current_user: dict = Depends(require_author),
):
    """Reorder sections within a module"""
    db = get_firestore()

    sections_ref = _get_sections_ref(db, course_id, level_id, module_id)

    for index, section_id in enumerate(request.order):
        sections_ref.document(section_id).update({"order": index, "updatedAt": datetime.utcnow()})

    return {"message": "Sections reordered successfully"}


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
            metadata=_parse_metadata(doc.to_dict()),
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

    if request.metadata:
        lesson_data["metadata"] = _metadata_to_firestore(request.metadata)

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
        metadata=request.metadata,
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
        metadata=_parse_metadata(data),
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
    if request.metadata is not None:
        update_data["metadata"] = _metadata_to_firestore(request.metadata)

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
        metadata=_parse_metadata(updated),
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


@router.post("/{course_id}/levels/{level_id}/modules/{module_id}/sections/{section_id}/lessons/reorder", status_code=200)
async def reorder_lessons(
    course_id: str,
    level_id: str,
    module_id: str,
    section_id: str,
    request: ReorderRequest,
    current_user: dict = Depends(require_author),
):
    """Reorder lessons within a section"""
    db = get_firestore()

    lessons_ref = _get_lessons_ref(db, course_id, level_id, module_id, section_id)

    for index, lesson_id in enumerate(request.order):
        lessons_ref.document(lesson_id).update({"order": index, "updatedAt": datetime.utcnow()})

    return {"message": "Lessons reordered successfully"}
