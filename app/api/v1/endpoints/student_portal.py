"""
Student Portal API Endpoints
Endpoints for student mobile app - courses, lessons, content, progress
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.security import get_current_user
from app.core.firebase_admin import get_firestore, get_document, update_document

router = APIRouter()


# ============== SCHEMAS ==============

class StudentInfo(BaseModel):
    id: str
    email: str
    name: str
    image_url: Optional[str] = None
    student_level: Optional[str] = None


class EnrolledCourseResponse(BaseModel):
    id: str
    course_id: str
    course_name: str
    course_description: Optional[str] = None
    course_image: Optional[str] = None
    progress_percent: float = 0
    enrolled_at: Optional[str] = None
    last_accessed_at: Optional[str] = None


class StudentLoginResponse(BaseModel):
    access_token: str
    student: StudentInfo
    enrolled_courses: List[EnrolledCourseResponse]


class LessonSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    duration_minutes: Optional[int] = None
    is_completed: bool = False
    is_locked: bool = False
    content_type: Optional[str] = None
    has_flashcards: bool = False
    has_quizzes: bool = False
    has_materials: bool = False


class SectionSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    is_locked: bool = False
    lessons: List[LessonSummary] = []


class ModuleSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    is_locked: bool = False
    sections: List[SectionSummary] = []


class LevelSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order: int = 0
    is_locked: bool = False
    is_current: bool = False
    modules: List[ModuleSummary] = []


class CourseDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    levels: List[LevelSummary] = []
    student_current_level: Optional[str] = None
    total_lessons: int = 0
    completed_lessons: int = 0
    progress_percent: float = 0


class FlashcardItem(BaseModel):
    id: str
    order: int = 0
    front: str
    back: str
    hint: Optional[str] = None
    image_url: Optional[str] = None


class FlashcardSet(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    cards: List[FlashcardItem] = []


class QuizOption(BaseModel):
    id: str
    text: str


class QuizQuestion(BaseModel):
    id: str
    order: int = 0
    type: str
    question: str
    options: List[QuizOption] = []
    points: int = 1


class Quiz(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    questions: List[QuizQuestion] = []


class PresentationSlide(BaseModel):
    id: str
    order: int = 0
    type: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    image_url: Optional[str] = None
    speaker_notes: Optional[str] = None


class Presentation(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    slides: List[PresentationSlide] = []


class Material(BaseModel):
    id: str
    name: str
    type: str
    url: str
    description: Optional[str] = None


class LessonContentResponse(BaseModel):
    lesson_id: str
    lesson_name: str
    lesson_body: Optional[str] = None
    video_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    flashcards: List[FlashcardSet] = []
    quizzes: List[Quiz] = []
    presentations: List[Presentation] = []
    materials: List[Material] = []


# ============== HELPER FUNCTIONS ==============

def get_student_level_order(level: str) -> int:
    """Convert student level to numeric order for comparison"""
    levels = {
        "basic": 1,
        "basico": 1,
        "intermediate": 2,
        "intermedio": 2,
        "advanced": 3,
        "avanzado": 3,
    }
    return levels.get(level.lower() if level else "", 1)


def get_level_difficulty_order(level_name: str, level_order: int) -> int:
    """Determine if a course level maps to basic/intermediate/advanced"""
    name_lower = level_name.lower() if level_name else ""

    # Check name for difficulty keywords
    if any(x in name_lower for x in ["básico", "basico", "basic", "beginner", "principiante"]):
        return 1
    elif any(x in name_lower for x in ["intermedio", "intermediate", "medium"]):
        return 2
    elif any(x in name_lower for x in ["avanzado", "advanced", "expert"]):
        return 3

    # Fall back to order-based mapping (1st level = basic, 2nd = intermediate, etc.)
    if level_order <= 1:
        return 1
    elif level_order <= 2:
        return 2
    else:
        return 3


async def get_student_progress(student_id: str, course_id: str) -> Dict[str, bool]:
    """Get completed lessons for a student in a course"""
    db = get_firestore()

    # Query progress collection
    progress_ref = db.collection("student_progress")
    query = progress_ref.where("studentId", "==", student_id).where("courseId", "==", course_id)
    docs = list(query.stream())

    completed = {}
    for doc in docs:
        data = doc.to_dict()
        lesson_id = data.get("lessonId")
        if lesson_id and data.get("completed"):
            completed[lesson_id] = True

    return completed


async def get_lesson_content_counts(db, lesson_id: str) -> Dict[str, bool]:
    """Check if a lesson has flashcards, quizzes, etc."""
    # Check flashcards
    fc_query = db.collection("generated_flashcards").where("lessonId", "==", lesson_id).where("status", "==", "completed").limit(1)
    has_flashcards = len(list(fc_query.stream())) > 0

    # Check quizzes
    quiz_query = db.collection("generated_quizzes").where("lessonId", "==", lesson_id).where("status", "==", "completed").limit(1)
    has_quizzes = len(list(quiz_query.stream())) > 0

    return {
        "has_flashcards": has_flashcards,
        "has_quizzes": has_quizzes,
    }


# ============== ENDPOINTS ==============

@router.get("/me", response_model=StudentInfo)
async def get_current_student(
    current_user: dict = Depends(get_current_user),
):
    """Get current student information"""
    user_id = current_user["id"]
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail="Student not found")

    return StudentInfo(
        id=user_id,
        email=user_data.get("email", ""),
        name=user_data.get("name", ""),
        image_url=user_data.get("imageUrl") or user_data.get("image_url"),
        student_level=user_data.get("studentLevel") or user_data.get("student_level", "basic"),
    )


@router.get("/courses", response_model=List[EnrolledCourseResponse])
async def get_enrolled_courses(
    current_user: dict = Depends(get_current_user),
):
    """Get all courses enrolled by the current student"""
    user_id = current_user["id"]
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get enrolled course IDs
    enrolled_course_ids = user_data.get("enrolledCourses") or user_data.get("enrolled_courses", [])

    if not enrolled_course_ids:
        return []

    db = get_firestore()
    courses = []

    for course_id in enrolled_course_ids:
        course_data = await get_document("courses", course_id)
        if course_data:
            # Get progress for this course
            progress = await get_student_progress(user_id, course_id)

            # Count total lessons in course
            total_lessons = 0
            levels_ref = db.collection("courses").document(course_id).collection("levels")
            for level in levels_ref.stream():
                modules_ref = levels_ref.document(level.id).collection("modules")
                for module in modules_ref.stream():
                    sections_ref = modules_ref.document(module.id).collection("sections")
                    for section in sections_ref.stream():
                        lessons_ref = sections_ref.document(section.id).collection("lessons")
                        total_lessons += len(list(lessons_ref.stream()))

            completed_lessons = len(progress)
            progress_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

            courses.append(EnrolledCourseResponse(
                id=f"{user_id}_{course_id}",  # enrollment ID
                course_id=course_id,
                course_name=course_data.get("name", ""),
                course_description=course_data.get("description"),
                course_image=course_data.get("imageUrl") or course_data.get("image_url"),
                progress_percent=round(progress_percent, 1),
                enrolled_at=str(user_data.get("createdAt", "")),
            ))

    return courses


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
async def get_course_detail(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get course detail with full hierarchy.
    Includes lock status based on student level.
    """
    user_id = current_user["id"]
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail="Student not found")

    # Verify student is enrolled
    enrolled_courses = user_data.get("enrolledCourses") or user_data.get("enrolled_courses", [])
    if course_id not in enrolled_courses:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # Get course
    course_data = await get_document("courses", course_id)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")

    db = get_firestore()

    # Get student's current level
    student_level = user_data.get("studentLevel") or user_data.get("student_level", "basic")
    student_level_order = get_student_level_order(student_level)

    # Get completed lessons
    completed_lessons = await get_student_progress(user_id, course_id)

    # Build course hierarchy
    levels = []
    total_lessons = 0
    completed_count = 0

    levels_ref = db.collection("courses").document(course_id).collection("levels")
    level_docs = list(levels_ref.order_by("order").stream())

    for level_doc in level_docs:
        level_data = level_doc.to_dict()
        level_order = level_data.get("order", 0)
        level_difficulty = get_level_difficulty_order(level_data.get("name", ""), level_order)

        # Level is locked if its difficulty is higher than student's level
        is_level_locked = level_difficulty > student_level_order
        is_current_level = level_difficulty == student_level_order

        modules = []
        modules_ref = levels_ref.document(level_doc.id).collection("modules")
        module_docs = list(modules_ref.order_by("order").stream())

        for module_doc in module_docs:
            module_data = module_doc.to_dict()

            sections = []
            sections_ref = modules_ref.document(module_doc.id).collection("sections")
            section_docs = list(sections_ref.order_by("order").stream())

            for section_doc in section_docs:
                section_data = section_doc.to_dict()

                lessons = []
                lessons_ref = sections_ref.document(section_doc.id).collection("lessons")
                lesson_docs = list(lessons_ref.order_by("order").stream())

                for lesson_doc in lesson_docs:
                    lesson_data = lesson_doc.to_dict()
                    lesson_id = lesson_doc.id
                    total_lessons += 1

                    is_completed = lesson_id in completed_lessons
                    if is_completed:
                        completed_count += 1

                    # Check content availability
                    content_counts = await get_lesson_content_counts(db, lesson_id)
                    materials = lesson_data.get("materials", [])

                    # Parse duration
                    duration_str = lesson_data.get("duration")
                    duration_minutes = None
                    if duration_str:
                        try:
                            # Handle formats like "15:00" or "15"
                            if ":" in str(duration_str):
                                parts = str(duration_str).split(":")
                                duration_minutes = int(parts[0])
                            else:
                                duration_minutes = int(duration_str)
                        except:
                            pass

                    lessons.append(LessonSummary(
                        id=lesson_id,
                        name=lesson_data.get("name", ""),
                        description=lesson_data.get("description"),
                        order=lesson_data.get("order", 0),
                        duration_minutes=duration_minutes,
                        is_completed=is_completed,
                        is_locked=is_level_locked,
                        content_type=lesson_data.get("contentType"),
                        has_flashcards=content_counts["has_flashcards"],
                        has_quizzes=content_counts["has_quizzes"],
                        has_materials=len(materials) > 0,
                    ))

                sections.append(SectionSummary(
                    id=section_doc.id,
                    name=section_data.get("name", ""),
                    description=section_data.get("description"),
                    order=section_data.get("order", 0),
                    is_locked=is_level_locked,
                    lessons=lessons,
                ))

            modules.append(ModuleSummary(
                id=module_doc.id,
                name=module_data.get("name", ""),
                description=module_data.get("description"),
                order=module_data.get("order", 0),
                is_locked=is_level_locked,
                sections=sections,
            ))

        levels.append(LevelSummary(
            id=level_doc.id,
            name=level_data.get("name", ""),
            description=level_data.get("description"),
            order=level_order,
            is_locked=is_level_locked,
            is_current=is_current_level,
            modules=modules,
        ))

    progress_percent = (completed_count / total_lessons * 100) if total_lessons > 0 else 0

    return CourseDetailResponse(
        id=course_id,
        name=course_data.get("name", ""),
        description=course_data.get("description"),
        image_url=course_data.get("imageUrl") or course_data.get("image_url"),
        levels=levels,
        student_current_level=student_level,
        total_lessons=total_lessons,
        completed_lessons=completed_count,
        progress_percent=round(progress_percent, 1),
    )


@router.get("/lessons/{lesson_id}", response_model=LessonContentResponse)
async def get_lesson_content(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get full lesson content including flashcards, quizzes, and materials.
    """
    db = get_firestore()

    # Find the lesson in the hierarchy
    lesson_info = None
    courses_ref = db.collection("courses")

    for course in courses_ref.stream():
        levels_ref = courses_ref.document(course.id).collection("levels")
        for level in levels_ref.stream():
            modules_ref = levels_ref.document(level.id).collection("modules")
            for module in modules_ref.stream():
                sections_ref = modules_ref.document(module.id).collection("sections")
                for section in sections_ref.stream():
                    lesson_ref = sections_ref.document(section.id).collection("lessons").document(lesson_id)
                    lesson_doc = lesson_ref.get()
                    if lesson_doc.exists:
                        lesson_info = {
                            "data": lesson_doc.to_dict(),
                            "course_id": course.id,
                            "level_id": level.id,
                        }
                        break
                if lesson_info:
                    break
            if lesson_info:
                break
        if lesson_info:
            break

    if not lesson_info:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson_data = lesson_info["data"]

    # Get flashcards
    fc_query = db.collection("generated_flashcards").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    fc_docs = list(fc_query.stream())

    flashcards = []
    for doc in fc_docs:
        data = doc.to_dict()
        cards = data.get("cards", [])
        flashcards.append(FlashcardSet(
            id=doc.id,
            title=data.get("title", ""),
            description=data.get("description"),
            cards=[FlashcardItem(
                id=c.get("id", ""),
                order=idx,
                front=c.get("front", ""),
                back=c.get("back", ""),
                hint=c.get("hint"),
                image_url=c.get("imageUrl"),
            ) for idx, c in enumerate(cards)],
        ))

    # Get quizzes (without correct answers for students)
    quiz_query = db.collection("generated_quizzes").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    quiz_docs = list(quiz_query.stream())

    quizzes = []
    for doc in quiz_docs:
        data = doc.to_dict()
        questions = data.get("questions", [])
        quizzes.append(Quiz(
            id=doc.id,
            title=data.get("title", ""),
            description=data.get("description"),
            time_limit_minutes=data.get("timeLimitMinutes"),
            questions=[QuizQuestion(
                id=q.get("id", ""),
                order=idx,
                type=q.get("type", "multiple_choice"),
                question=q.get("question", ""),
                options=[QuizOption(
                    id=opt.get("id", ""),
                    text=opt.get("text", ""),
                ) for opt in q.get("options", [])],
                points=q.get("points", 1),
            ) for idx, q in enumerate(questions)],
        ))

    # Get presentations (check if stored)
    presentations = []
    pres_query = db.collection("generated_presentations").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    pres_docs = list(pres_query.stream())

    for doc in pres_docs:
        data = doc.to_dict()
        slides = data.get("slides", [])
        presentations.append(Presentation(
            id=doc.id,
            title=data.get("title", ""),
            description=data.get("description"),
            slides=[PresentationSlide(
                id=s.get("id", str(idx)),
                order=idx,
                type=s.get("type", "content"),
                title=s.get("title"),
                subtitle=s.get("subtitle"),
                content=s.get("content"),
                bullet_points=s.get("bulletPoints") or s.get("bullet_points"),
                image_url=s.get("imageUrl"),
                speaker_notes=s.get("speakerNotes"),
            ) for idx, s in enumerate(slides)],
        ))

    # Get materials
    materials_data = lesson_data.get("materials", [])
    materials = [Material(
        id=m.get("id", ""),
        name=m.get("name", ""),
        type=m.get("type", "document"),
        url=m.get("url", ""),
        description=m.get("description"),
    ) for m in materials_data]

    return LessonContentResponse(
        lesson_id=lesson_id,
        lesson_name=lesson_data.get("name", ""),
        lesson_body=lesson_data.get("lessonBody"),
        video_url=lesson_data.get("videoUrl"),
        youtube_video_id=lesson_data.get("youtubeVideoId"),
        flashcards=flashcards,
        quizzes=quizzes,
        presentations=presentations,
        materials=materials,
    )


@router.post("/progress/lessons/{lesson_id}/complete")
async def mark_lesson_completed(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Mark a lesson as completed for the current student"""
    user_id = current_user["id"]
    db = get_firestore()

    # Find the lesson to get course_id
    course_id = None
    courses_ref = db.collection("courses")

    for course in courses_ref.stream():
        levels_ref = courses_ref.document(course.id).collection("levels")
        for level in levels_ref.stream():
            modules_ref = levels_ref.document(level.id).collection("modules")
            for module in modules_ref.stream():
                sections_ref = modules_ref.document(module.id).collection("sections")
                for section in sections_ref.stream():
                    lesson_ref = sections_ref.document(section.id).collection("lessons").document(lesson_id)
                    if lesson_ref.get().exists:
                        course_id = course.id
                        break
                if course_id:
                    break
            if course_id:
                break
        if course_id:
            break

    if not course_id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Create or update progress record
    progress_ref = db.collection("student_progress")
    progress_id = f"{user_id}_{course_id}_{lesson_id}"

    progress_ref.document(progress_id).set({
        "studentId": user_id,
        "courseId": course_id,
        "lessonId": lesson_id,
        "completed": True,
        "completedAt": datetime.utcnow(),
    }, merge=True)

    return {"message": "Lesson marked as completed", "lesson_id": lesson_id}


@router.get("/progress/courses/{course_id}")
async def get_course_progress(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get progress summary for a course"""
    user_id = current_user["id"]
    db = get_firestore()

    # Get completed lessons
    completed = await get_student_progress(user_id, course_id)

    # Count total lessons
    total_lessons = 0
    levels_ref = db.collection("courses").document(course_id).collection("levels")
    for level in levels_ref.stream():
        modules_ref = levels_ref.document(level.id).collection("modules")
        for module in modules_ref.stream():
            sections_ref = modules_ref.document(module.id).collection("sections")
            for section in sections_ref.stream():
                lessons_ref = sections_ref.document(section.id).collection("lessons")
                total_lessons += len(list(lessons_ref.stream()))

    completed_count = len(completed)
    progress_percent = (completed_count / total_lessons * 100) if total_lessons > 0 else 0

    return {
        "completed_lessons": completed_count,
        "total_lessons": total_lessons,
        "progress_percent": round(progress_percent, 1),
    }
