"""
Course domain models
Matches Firestore courses collection structure
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CourseStatus(str, Enum):
    """Course status enumeration"""
    DRAFT = "draft"
    PENDING = "pending"
    LIVE = "live"
    ARCHIVE = "archive"


class PriceStatus(str, Enum):
    """Course price status enumeration"""
    FREE = "free"
    PREMIUM = "premium"


class Author(BaseModel):
    """Course author embedded document"""
    id: str
    name: str
    image_url: Optional[str] = Field(None, alias="imageUrl")

    class Config:
        populate_by_name = True


class CourseMeta(BaseModel):
    """Course metadata embedded document"""
    duration: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    learnings: Optional[List[str]] = Field(default_factory=list)
    requirements: Optional[List[str]] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class Course(BaseModel):
    """
    Course model matching Firestore courses collection
    """
    id: str
    name: str
    thumbnail_url: str = Field(..., alias="thumbnailUrl")
    video_url: Optional[str] = Field(None, alias="videoUrl")
    category_id: Optional[str] = Field(None, alias="categoryId")
    tag_ids: Optional[List[str]] = Field(default_factory=list, alias="tagIDs")
    status: str = CourseStatus.DRAFT
    price_status: str = Field(PriceStatus.FREE, alias="priceStatus")
    author: Optional[Author] = None
    students_count: int = Field(0, alias="studentsCount")
    rating: float = 0.0
    lessons_count: int = Field(0, alias="lessonsCount")
    course_meta: CourseMeta = Field(default_factory=CourseMeta, alias="courseMeta")
    is_featured: bool = Field(False, alias="isFeatured")
    level: Optional[str] = None
    language: Optional[str] = None
    tutor_ids: Optional[List[str]] = Field(default_factory=list, alias="tutorIds")
    tutors: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "Course":
        """Create Course from Firestore document"""
        if doc_id:
            doc_dict["id"] = doc_id

        # Handle nested objects
        if "meta" in doc_dict and "courseMeta" not in doc_dict:
            doc_dict["courseMeta"] = doc_dict.pop("meta")

        # Handle timestamps
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        if "updatedAt" in doc_dict and hasattr(doc_dict["updatedAt"], "seconds"):
            doc_dict["updatedAt"] = datetime.fromtimestamp(doc_dict["updatedAt"].seconds)

        # Map old field names
        if "image_url" in doc_dict and "thumbnailUrl" not in doc_dict:
            doc_dict["thumbnailUrl"] = doc_dict.pop("image_url")
        if "cat_id" in doc_dict and "categoryId" not in doc_dict:
            doc_dict["categoryId"] = doc_dict.pop("cat_id")
        if "students" in doc_dict and "studentsCount" not in doc_dict:
            doc_dict["studentsCount"] = doc_dict.pop("students")

        return cls(**doc_dict)

    def to_firestore(self) -> dict:
        """Convert to Firestore document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        data.pop("id", None)
        return data


class Category(BaseModel):
    """Category model"""
    id: str
    name: str
    thumbnail_url: str = Field(..., alias="thumbnailUrl")
    order_index: Optional[int] = Field(0, alias="orderIndex")
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    class Config:
        populate_by_name = True


class Tag(BaseModel):
    """Tag model"""
    id: str
    name: str
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    class Config:
        populate_by_name = True
