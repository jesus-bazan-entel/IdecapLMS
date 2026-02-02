"""
Main API router - combines all endpoint routers
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    students,
    courses,
    hierarchy,
    categories,
    dashboard,
    access_codes,
)
from app.api.v1.endpoints.ai_studio import (
    audio,
    presentations,
    mindmaps,
    podcasts,
    videos,
    translate,
    flashcards,
    quizzes,
    lesson_content,
    course_structure,
)

api_router = APIRouter()

# Authentication
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Users
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

# Students
api_router.include_router(
    students.router,
    prefix="/students",
    tags=["Students"]
)

# Access Codes (for student QR/code login)
api_router.include_router(
    access_codes.router,
    prefix="/access-codes",
    tags=["Access Codes"]
)

# Courses
api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["Courses"]
)

# Course Hierarchy
api_router.include_router(
    hierarchy.router,
    prefix="/courses",
    tags=["Course Hierarchy"]
)

# Categories
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Categories"]
)

# Dashboard
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)

# AI Studio
api_router.include_router(
    audio.router,
    prefix="/ai/audio",
    tags=["AI Audio"]
)

api_router.include_router(
    presentations.router,
    prefix="/ai/presentations",
    tags=["AI Presentations"]
)

api_router.include_router(
    mindmaps.router,
    prefix="/ai/mindmaps",
    tags=["AI Mind Maps"]
)

api_router.include_router(
    podcasts.router,
    prefix="/ai/podcasts",
    tags=["AI Podcasts"]
)

api_router.include_router(
    videos.router,
    prefix="/ai/videos",
    tags=["AI Videos"]
)

api_router.include_router(
    translate.router,
    prefix="/ai/translate",
    tags=["AI Translation"]
)

api_router.include_router(
    flashcards.router,
    prefix="/ai/flashcards",
    tags=["AI Flashcards"]
)

api_router.include_router(
    quizzes.router,
    prefix="/ai/quizzes",
    tags=["AI Quizzes"]
)

api_router.include_router(
    lesson_content.router,
    prefix="/ai",
    tags=["AI Lesson Content"]
)

api_router.include_router(
    course_structure.router,
    prefix="/ai-studio",
    tags=["AI Course Structure"]
)
