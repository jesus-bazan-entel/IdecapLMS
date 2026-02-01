"""
User domain models
Matches Firestore users collection structure
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    AUTHOR = "author"
    TUTOR = "tutor"
    STUDENT = "student"
    COORDINATOR = "coordinator"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    FREE = "free"


class StudentLevel(str, Enum):
    """Student level enumeration"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class AuthorInfo(BaseModel):
    """Author profile information"""
    bio: Optional[str] = None
    job_title: Optional[str] = Field(None, alias="jobTitle")
    students: Optional[int] = 0
    fb: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None

    class Config:
        populate_by_name = True


class Subscription(BaseModel):
    """User subscription information"""
    plan: Optional[str] = None
    product_id: Optional[str] = Field(None, alias="productId")
    purchase_at: Optional[datetime] = Field(None, alias="purchaseAt")
    expire_at: Optional[datetime] = Field(None, alias="expireAt")

    class Config:
        populate_by_name = True

    @property
    def is_active(self) -> bool:
        if not self.expire_at:
            return False
        return datetime.utcnow() < self.expire_at


class UserModel(BaseModel):
    """
    User model matching Firestore users collection
    Supports admin, author, tutor, and student roles
    """
    id: str
    email: str
    name: str
    image_url: Optional[str] = Field(None, alias="imageUrl")
    role: Optional[List[str]] = Field(default_factory=list)
    enrolled_courses: Optional[List[str]] = Field(default_factory=list, alias="enrolledCourses")
    wishlist: Optional[List[str]] = Field(default_factory=list, alias="wishList")
    completed_lessons: Optional[List[str]] = Field(default_factory=list, alias="completedLessons")
    is_disabled: bool = Field(False, alias="isDisbaled")  # Keeping original typo for compatibility
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    platform: Optional[str] = None

    # Author specific fields
    author_info: Optional[AuthorInfo] = Field(None, alias="authorInfo")

    # Subscription
    subscription: Optional[Subscription] = None

    # Student specific fields
    qr_code_hash: Optional[str] = Field(None, alias="qrCodeHash")
    payment_status: Optional[str] = Field(None, alias="paymentStatus")
    student_level: Optional[str] = Field(None, alias="studentLevel")
    student_section: Optional[str] = Field(None, alias="studentSection")

    # Tutor specific fields
    assigned_courses: Optional[List[str]] = Field(default_factory=list, alias="assignedCourses")
    tutor_permissions: Optional[Dict[str, Any]] = Field(None, alias="tutorPermissions")

    class Config:
        populate_by_name = True

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return "admin" in (self.role or [])

    @property
    def is_author(self) -> bool:
        """Check if user has author role"""
        return "author" in (self.role or [])

    @property
    def is_tutor(self) -> bool:
        """Check if user has tutor role"""
        return "tutor" in (self.role or [])

    @property
    def disabled(self) -> bool:
        """Alias for is_disabled to match Flutter model"""
        return self.is_disabled

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "UserModel":
        """Create UserModel from Firestore document"""
        if doc_id:
            doc_dict["id"] = doc_id

        # Handle role as string or list
        role = doc_dict.get("role", [])
        if isinstance(role, str):
            doc_dict["role"] = [role]

        # Handle timestamps
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        if "updatedAt" in doc_dict and hasattr(doc_dict["updatedAt"], "seconds"):
            doc_dict["updatedAt"] = datetime.fromtimestamp(doc_dict["updatedAt"].seconds)

        return cls(**doc_dict)

    def to_firestore(self) -> dict:
        """Convert to Firestore document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        # Remove id as it's the document ID
        data.pop("id", None)
        return data
