"""
Dashboard endpoints
Statistics and charts data
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.security import get_current_user, require_admin
from app.core.firebase_admin import get_firestore

router = APIRouter()


# ============== SCHEMAS ==============
class StatCard(BaseModel):
    """Single stat card data"""
    title: str
    value: int
    change: Optional[float] = None  # Percentage change from previous period
    trend: str = "neutral"  # up, down, neutral
    icon: Optional[str] = None


class DashboardStats(BaseModel):
    """Dashboard overview statistics"""
    total_students: StatCard
    total_courses: StatCard
    total_tutors: StatCard
    active_enrollments: StatCard
    total_revenue: Optional[StatCard] = None
    pending_payments: Optional[StatCard] = None


class ChartDataPoint(BaseModel):
    """Single data point for charts"""
    label: str
    value: float


class TimeSeriesPoint(BaseModel):
    """Time series data point"""
    date: str
    value: float


class ChartData(BaseModel):
    """Chart data response"""
    title: str
    type: str  # line, bar, pie, area
    data: List[ChartDataPoint]
    total: Optional[float] = None


class TimeSeriesData(BaseModel):
    """Time series chart data"""
    title: str
    series: List[Dict]  # Multiple series for line charts


class CourseStats(BaseModel):
    """Course-specific statistics"""
    course_id: str
    course_name: str
    total_students: int
    completion_rate: float
    average_progress: float
    total_lessons: int


class RecentActivity(BaseModel):
    """Recent activity item"""
    id: str
    type: str  # enrollment, payment, completion
    description: str
    user_name: str
    timestamp: datetime


def _calculate_change(current: int, previous: int) -> tuple[float, str]:
    """Calculate percentage change and trend"""
    if previous == 0:
        return (100.0 if current > 0 else 0.0, "up" if current > 0 else "neutral")

    change = ((current - previous) / previous) * 100
    trend = "up" if change > 0 else ("down" if change < 0 else "neutral")
    return (round(change, 1), trend)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(require_admin),
):
    """
    Get main dashboard statistics
    Admin only
    """
    db = get_firestore()

    # Count students
    students_query = db.collection("users").where("role", "array_contains", "student")
    students = list(students_query.stream())
    total_students = len(students)

    # Count students from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_students = [
        s for s in students
        if (s.to_dict().get("createdAt") or datetime.min) > thirty_days_ago
    ]
    students_change, students_trend = _calculate_change(len(recent_students), total_students - len(recent_students))

    # Count courses
    courses_query = db.collection("courses")
    courses = list(courses_query.stream())
    total_courses = len(courses)
    live_courses = len([c for c in courses if c.to_dict().get("status") == "live"])

    # Count tutors
    tutors_query = db.collection("users").where("role", "array_contains", "tutor")
    tutors = list(tutors_query.stream())
    total_tutors = len(tutors)

    # Count active enrollments (students with enrolled courses)
    active_enrollments = len([
        s for s in students
        if len(s.to_dict().get("enrolledCourses") or s.to_dict().get("enrolled_courses", [])) > 0
    ])

    # Count pending payments
    pending_payments = len([
        s for s in students
        if (s.to_dict().get("paymentStatus") or s.to_dict().get("payment_status")) == "pending"
    ])

    return DashboardStats(
        total_students=StatCard(
            title="Total Estudiantes",
            value=total_students,
            change=students_change,
            trend=students_trend,
            icon="users"
        ),
        total_courses=StatCard(
            title="Cursos Activos",
            value=live_courses,
            change=None,
            trend="neutral",
            icon="book-open"
        ),
        total_tutors=StatCard(
            title="Tutores",
            value=total_tutors,
            change=None,
            trend="neutral",
            icon="graduation-cap"
        ),
        active_enrollments=StatCard(
            title="Matrículas Activas",
            value=active_enrollments,
            change=None,
            trend="neutral",
            icon="clipboard-check"
        ),
        pending_payments=StatCard(
            title="Pagos Pendientes",
            value=pending_payments,
            change=None,
            trend="down" if pending_payments > 0 else "neutral",
            icon="credit-card"
        ),
    )


@router.get("/charts/users", response_model=TimeSeriesData)
async def get_users_chart(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(require_admin),
):
    """
    Get user registration chart data
    Admin only
    """
    db = get_firestore()

    # Get all students
    students_query = db.collection("users").where("role", "array_contains", "student")
    students = list(students_query.stream())

    # Group by date
    start_date = datetime.utcnow() - timedelta(days=days)
    registrations_by_date = defaultdict(int)

    for student in students:
        created_at = student.to_dict().get("createdAt")
        if created_at and created_at > start_date:
            date_str = created_at.strftime("%Y-%m-%d")
            registrations_by_date[date_str] += 1

    # Generate all dates in range
    data = []
    current_date = start_date
    while current_date <= datetime.utcnow():
        date_str = current_date.strftime("%Y-%m-%d")
        data.append({
            "date": date_str,
            "registrations": registrations_by_date.get(date_str, 0)
        })
        current_date += timedelta(days=1)

    return TimeSeriesData(
        title="Registros de Estudiantes",
        series=[
            {
                "name": "Nuevos estudiantes",
                "data": data
            }
        ]
    )


@router.get("/charts/enrollments", response_model=ChartData)
async def get_enrollments_by_course(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_admin),
):
    """
    Get enrollments by course chart data
    Admin only
    """
    db = get_firestore()

    # Get all courses
    courses = {doc.id: doc.to_dict() for doc in db.collection("courses").stream()}

    # Count enrollments per course
    enrollment_counts = defaultdict(int)
    students_query = db.collection("users").where("role", "array_contains", "student")

    for student in students_query.stream():
        enrolled = student.to_dict().get("enrolledCourses") or student.to_dict().get("enrolled_courses", [])
        for course_id in enrolled:
            enrollment_counts[course_id] += 1

    # Sort by count and take top N
    sorted_courses = sorted(enrollment_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    data = [
        ChartDataPoint(
            label=courses.get(course_id, {}).get("name", "Curso desconocido"),
            value=count
        )
        for course_id, count in sorted_courses
    ]

    return ChartData(
        title="Estudiantes por Curso",
        type="bar",
        data=data,
        total=sum(count for _, count in sorted_courses)
    )


@router.get("/charts/payment-status", response_model=ChartData)
async def get_payment_status_chart(
    current_user: dict = Depends(require_admin),
):
    """
    Get payment status distribution chart
    Admin only
    """
    db = get_firestore()

    # Count by payment status
    status_counts = defaultdict(int)
    students_query = db.collection("users").where("role", "array_contains", "student")

    for student in students_query.stream():
        payment_status = (
            student.to_dict().get("paymentStatus") or
            student.to_dict().get("payment_status") or
            "pending"
        )
        status_counts[payment_status] += 1

    status_labels = {
        "paid": "Pagado",
        "pending": "Pendiente",
        "overdue": "Vencido",
        "free": "Gratuito"
    }

    data = [
        ChartDataPoint(
            label=status_labels.get(status, status.capitalize()),
            value=count
        )
        for status, count in status_counts.items()
    ]

    return ChartData(
        title="Estado de Pagos",
        type="pie",
        data=data,
        total=sum(status_counts.values())
    )


@router.get("/charts/student-levels", response_model=ChartData)
async def get_student_levels_chart(
    current_user: dict = Depends(require_admin),
):
    """
    Get student level distribution chart
    Admin only
    """
    db = get_firestore()

    # Count by student level
    level_counts = defaultdict(int)
    students_query = db.collection("users").where("role", "array_contains", "student")

    for student in students_query.stream():
        level = (
            student.to_dict().get("studentLevel") or
            student.to_dict().get("student_level") or
            "basic"
        )
        level_counts[level] += 1

    level_labels = {
        "basic": "Básico",
        "intermediate": "Intermedio",
        "advanced": "Avanzado"
    }

    data = [
        ChartDataPoint(
            label=level_labels.get(level, level.capitalize()),
            value=count
        )
        for level, count in level_counts.items()
    ]

    return ChartData(
        title="Niveles de Estudiantes",
        type="pie",
        data=data,
        total=sum(level_counts.values())
    )


@router.get("/charts/courses-status", response_model=ChartData)
async def get_courses_status_chart(
    current_user: dict = Depends(require_admin),
):
    """
    Get courses by status chart
    Admin only
    """
    db = get_firestore()

    # Count by course status
    status_counts = defaultdict(int)
    for course in db.collection("courses").stream():
        status = course.to_dict().get("status", "draft")
        status_counts[status] += 1

    status_labels = {
        "draft": "Borrador",
        "pending": "Pendiente",
        "live": "Publicado",
        "archive": "Archivado"
    }

    data = [
        ChartDataPoint(
            label=status_labels.get(status, status.capitalize()),
            value=count
        )
        for status, count in status_counts.items()
    ]

    return ChartData(
        title="Estado de Cursos",
        type="bar",
        data=data,
        total=sum(status_counts.values())
    )


@router.get("/course-stats", response_model=List[CourseStats])
async def get_course_statistics(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_admin),
):
    """
    Get detailed statistics per course
    Admin only
    """
    db = get_firestore()

    # Get all courses
    courses = list(db.collection("courses").stream())

    # Count enrollments per course
    enrollment_counts = defaultdict(int)
    students_query = db.collection("users").where("role", "array_contains", "student")

    for student in students_query.stream():
        enrolled = student.to_dict().get("enrolledCourses") or student.to_dict().get("enrolled_courses", [])
        for course_id in enrolled:
            enrollment_counts[course_id] += 1

    result = []
    for course_doc in courses[:limit]:
        course_id = course_doc.id
        course_data = course_doc.to_dict()
        meta = course_data.get("courseMeta") or course_data.get("course_meta", {})

        result.append(CourseStats(
            course_id=course_id,
            course_name=course_data.get("name", ""),
            total_students=enrollment_counts.get(course_id, 0),
            completion_rate=0.0,  # Would need progress tracking
            average_progress=0.0,  # Would need progress tracking
            total_lessons=meta.get("lessonsCount") or meta.get("lessons_count", 0)
        ))

    # Sort by total students
    result.sort(key=lambda x: x.total_students, reverse=True)

    return result


@router.get("/recent-activity", response_model=List[RecentActivity])
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    """
    Get recent activity feed
    Admin only
    """
    db = get_firestore()

    activities = []

    # Get recent student registrations
    students_query = (
        db.collection("users")
        .where("role", "array_contains", "student")
        .order_by("createdAt", direction="DESCENDING")
        .limit(limit)
    )

    for student in students_query.stream():
        data = student.to_dict()
        created_at = data.get("createdAt")
        if created_at:
            activities.append(RecentActivity(
                id=student.id,
                type="enrollment",
                description=f"Nuevo estudiante registrado",
                user_name=data.get("name", "Usuario"),
                timestamp=created_at
            ))

    # Sort by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    return activities[:limit]
