"""
Users management endpoints
CRUD operations for users
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.core.security import get_current_user, require_admin, get_password_hash
from app.core.firebase_admin import (
    get_firestore,
    get_document,
    get_collection,
    create_document,
    update_document,
    delete_document,
)

router = APIRouter()


# Request/Response schemas
class UserCreateRequest(BaseModel):
    """Create user request"""
    email: EmailStr
    password: str
    name: str
    role: List[str] = ["student"]
    image_url: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Update user request"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_disabled: Optional[bool] = None


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    name: str
    image_url: Optional[str] = None
    role: List[str] = []
    is_disabled: bool = False
    created_at: Optional[datetime] = None
    enrolled_courses: List[str] = []


class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


def _user_to_response(user_id: str, user_data: dict) -> UserResponse:
    """Convert Firestore user data to response"""
    role = user_data.get("role", [])
    if isinstance(role, str):
        role = [role]

    return UserResponse(
        id=user_id,
        email=user_data.get("email", ""),
        name=user_data.get("name", ""),
        image_url=user_data.get("imageUrl") or user_data.get("image_url"),
        role=role,
        is_disabled=user_data.get("isDisabled") or user_data.get("is_disabled", False),
        created_at=user_data.get("createdAt"),
        enrolled_courses=user_data.get("enrolledCourses") or user_data.get("enrolled_courses", []),
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    """
    List all users with pagination
    Admin only
    """
    db = get_firestore()
    users_ref = db.collection("users")

    # Build query
    query = users_ref

    if role:
        query = query.where("role", "array_contains", role)

    # Get all matching documents (Firestore doesn't support offset well)
    docs = list(query.stream())

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        docs = [
            doc for doc in docs
            if search_lower in doc.to_dict().get("name", "").lower()
            or search_lower in doc.to_dict().get("email", "").lower()
        ]

    total = len(docs)

    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_docs = docs[start:end]

    users = [
        _user_to_response(doc.id, doc.to_dict())
        for doc in paginated_docs
    ]

    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Get user by ID
    Admin only
    """
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return _user_to_response(user_id, user_data)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Create a new user
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

    # Create user document
    import uuid
    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(request.password)

    user_data = {
        "email": request.email,
        "name": request.name,
        "passwordHash": password_hash,
        "role": request.role,
        "imageUrl": request.image_url,
        "createdAt": datetime.utcnow(),
        "platform": "web",
        "isDisabled": False,
        "enrolledCourses": [],
    }

    db.collection("users").document(user_id).set(user_data)

    return _user_to_response(user_id, user_data)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Update user by ID
    Admin only
    """
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build update data
    update_data = {}

    if request.name is not None:
        update_data["name"] = request.name

    if request.email is not None:
        # Check if email already exists
        db = get_firestore()
        users_ref = db.collection("users")
        query = users_ref.where("email", "==", request.email).limit(1)
        docs = list(query.stream())

        if docs and docs[0].id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        update_data["email"] = request.email

    if request.role is not None:
        update_data["role"] = request.role

    if request.image_url is not None:
        update_data["imageUrl"] = request.image_url

    if request.is_disabled is not None:
        update_data["isDisabled"] = request.is_disabled

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("users", user_id, update_data)

    # Return updated user
    updated_user = await get_document("users", user_id)
    return _user_to_response(user_id, updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Delete user by ID
    Admin only
    """
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    await delete_document("users", user_id)


@router.post("/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Disable user account
    Admin only
    """
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-disable
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )

    await update_document("users", user_id, {
        "isDisabled": True,
        "updatedAt": datetime.utcnow(),
    })

    updated_user = await get_document("users", user_id)
    return _user_to_response(user_id, updated_user)


@router.post("/{user_id}/enable", response_model=UserResponse)
async def enable_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Enable user account
    Admin only
    """
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    await update_document("users", user_id, {
        "isDisabled": False,
        "updatedAt": datetime.utcnow(),
    })

    updated_user = await get_document("users", user_id)
    return _user_to_response(user_id, updated_user)
