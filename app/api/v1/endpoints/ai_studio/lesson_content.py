"""
AI Studio - Lesson Content endpoints
Student-accessible endpoints for AI-generated lesson content
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.security import get_current_user
from app.core.firebase_admin import get_firestore

router = APIRouter()


# ============== FLASHCARD SCHEMAS ==============
class FlashcardItemResponse(BaseModel):
    id: str
    front: str
    back: str
    hint: Optional[str] = None
    category: Optional[str] = None


class LessonFlashcardsResponse(BaseModel):
    """Flashcards for a lesson"""
    id: str
    title: str
    topic: str
    cards: List[FlashcardItemResponse]
    total_cards: int
    difficulty: str


# ============== QUIZ SCHEMAS ==============
class QuizOptionResponse(BaseModel):
    id: str
    text: str
    is_correct: bool


class QuizQuestionResponse(BaseModel):
    id: str
    question: str
    type: str
    options: List[QuizOptionResponse]
    explanation: Optional[str] = None
    points: int = 1
    category: Optional[str] = None


class LessonQuizResponse(BaseModel):
    """Quiz for a lesson"""
    id: str
    title: str
    topic: str
    questions: List[QuizQuestionResponse]
    total_questions: int
    total_points: int
    difficulty: str
    time_limit_minutes: Optional[int] = None


# ============== FLASHCARD ENDPOINTS ==============
@router.get("/lessons/{lesson_id}/flashcards", response_model=List[LessonFlashcardsResponse])
async def get_lesson_flashcards(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get all flashcard sets for a specific lesson
    Available to all authenticated users (students, tutors, admins)
    """
    db = get_firestore()

    # Query flashcards by lesson_id
    query = db.collection("generated_flashcards").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    docs = list(query.stream())

    flashcard_sets = []
    for doc in docs:
        data = doc.to_dict()
        cards = data.get("cards", [])

        flashcard_sets.append(LessonFlashcardsResponse(
            id=doc.id,
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            cards=[FlashcardItemResponse(**card) for card in cards],
            total_cards=len(cards),
            difficulty=data.get("difficulty", "intermediate"),
        ))

    return flashcard_sets


# ============== QUIZ ENDPOINTS ==============
@router.get("/lessons/{lesson_id}/quizzes", response_model=List[LessonQuizResponse])
async def get_lesson_quizzes(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get all quizzes for a specific lesson
    Available to all authenticated users (students, tutors, admins)
    """
    db = get_firestore()

    # Query quizzes by lesson_id
    query = db.collection("generated_quizzes").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    docs = list(query.stream())

    quizzes = []
    for doc in docs:
        data = doc.to_dict()
        questions = data.get("questions", [])
        total_points = sum(q.get("points", 1) for q in questions)

        processed_questions = []
        for q in questions:
            options = [QuizOptionResponse(**opt) for opt in q.get("options", [])]
            processed_questions.append(QuizQuestionResponse(
                id=q.get("id", ""),
                question=q.get("question", ""),
                type=q.get("type", "multiple_choice"),
                options=options,
                explanation=q.get("explanation"),
                points=q.get("points", 1),
                category=q.get("category"),
            ))

        quizzes.append(LessonQuizResponse(
            id=doc.id,
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            questions=processed_questions,
            total_questions=len(questions),
            total_points=total_points,
            difficulty=data.get("difficulty", "intermediate"),
            time_limit_minutes=data.get("timeLimitMinutes"),
        ))

    return quizzes


# ============== COMBINED CONTENT ENDPOINT ==============
class LessonAIContentResponse(BaseModel):
    """All AI-generated content for a lesson"""
    lesson_id: str
    flashcard_sets: List[LessonFlashcardsResponse]
    quizzes: List[LessonQuizResponse]
    has_flashcards: bool
    has_quizzes: bool


@router.get("/lessons/{lesson_id}/ai-content", response_model=LessonAIContentResponse)
async def get_lesson_ai_content(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get all AI-generated content for a lesson (flashcards + quizzes)
    Available to all authenticated users
    """
    db = get_firestore()

    # Get flashcards
    fc_query = db.collection("generated_flashcards").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    fc_docs = list(fc_query.stream())

    flashcard_sets = []
    for doc in fc_docs:
        data = doc.to_dict()
        cards = data.get("cards", [])
        flashcard_sets.append(LessonFlashcardsResponse(
            id=doc.id,
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            cards=[FlashcardItemResponse(**card) for card in cards],
            total_cards=len(cards),
            difficulty=data.get("difficulty", "intermediate"),
        ))

    # Get quizzes
    quiz_query = db.collection("generated_quizzes").where("lessonId", "==", lesson_id).where("status", "==", "completed")
    quiz_docs = list(quiz_query.stream())

    quizzes = []
    for doc in quiz_docs:
        data = doc.to_dict()
        questions = data.get("questions", [])
        total_points = sum(q.get("points", 1) for q in questions)

        processed_questions = []
        for q in questions:
            options = [QuizOptionResponse(**opt) for opt in q.get("options", [])]
            processed_questions.append(QuizQuestionResponse(
                id=q.get("id", ""),
                question=q.get("question", ""),
                type=q.get("type", "multiple_choice"),
                options=options,
                explanation=q.get("explanation"),
                points=q.get("points", 1),
                category=q.get("category"),
            ))

        quizzes.append(LessonQuizResponse(
            id=doc.id,
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            questions=processed_questions,
            total_questions=len(questions),
            total_points=total_points,
            difficulty=data.get("difficulty", "intermediate"),
            time_limit_minutes=data.get("timeLimitMinutes"),
        ))

    return LessonAIContentResponse(
        lesson_id=lesson_id,
        flashcard_sets=flashcard_sets,
        quizzes=quizzes,
        has_flashcards=len(flashcard_sets) > 0,
        has_quizzes=len(quizzes) > 0,
    )
