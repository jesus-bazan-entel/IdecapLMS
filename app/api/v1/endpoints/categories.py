"""
Categories and Tags management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

from app.core.security import get_current_user, require_admin
from app.core.firebase_admin import (
    get_firestore,
    get_document,
    get_collection,
    create_document,
    update_document,
    delete_document,
)

router = APIRouter()


# ============== CATEGORY SCHEMAS ==============
class CategoryCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[str] = None
    order: int = 0


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[str] = None
    order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[str] = None
    order: int = 0
    course_count: int = 0
    created_at: Optional[datetime] = None


# ============== TAG SCHEMAS ==============
class TagCreateRequest(BaseModel):
    name: str
    color: Optional[str] = "#6366f1"  # Default indigo


class TagUpdateRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class TagResponse(BaseModel):
    id: str
    name: str
    color: str = "#6366f1"
    usage_count: int = 0
    created_at: Optional[datetime] = None


def _category_to_response(category_id: str, data: dict) -> CategoryResponse:
    return CategoryResponse(
        id=category_id,
        name=data.get("name", ""),
        description=data.get("description"),
        image_url=data.get("imageUrl") or data.get("image_url"),
        parent_id=data.get("parentId") or data.get("parent_id"),
        order=data.get("order", 0),
        course_count=data.get("courseCount") or data.get("course_count", 0),
        created_at=data.get("createdAt") or data.get("created_at"),
    )


def _tag_to_response(tag_id: str, data: dict) -> TagResponse:
    return TagResponse(
        id=tag_id,
        name=data.get("name", ""),
        color=data.get("color", "#6366f1"),
        usage_count=data.get("usageCount") or data.get("usage_count", 0),
        created_at=data.get("createdAt") or data.get("created_at"),
    )


# ============== CATEGORY ENDPOINTS ==============
@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user),
):
    """List all categories"""
    categories = await get_collection("categories")

    return [
        _category_to_response(cat_id, cat_data)
        for cat_id, cat_data in categories.items()
    ]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get category by ID"""
    category_data = await get_document("categories", category_id)

    if not category_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return _category_to_response(category_id, category_data)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreateRequest,
    current_user: dict = Depends(require_admin),
):
    """Create a new category (Admin only)"""
    db = get_firestore()

    # Verify parent exists if specified
    if request.parent_id:
        parent = await get_document("categories", request.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )

    category_id = str(uuid.uuid4())
    category_data = {
        "name": request.name,
        "description": request.description,
        "imageUrl": request.image_url,
        "parentId": request.parent_id,
        "order": request.order,
        "courseCount": 0,
        "createdAt": datetime.utcnow(),
    }

    db.collection("categories").document(category_id).set(category_data)

    return _category_to_response(category_id, category_data)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    request: CategoryUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    """Update category (Admin only)"""
    category_data = await get_document("categories", category_id)

    if not category_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Verify parent exists if specified
    if request.parent_id:
        if request.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )
        parent = await get_document("categories", request.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.image_url is not None:
        update_data["imageUrl"] = request.image_url
    if request.parent_id is not None:
        update_data["parentId"] = request.parent_id
    if request.order is not None:
        update_data["order"] = request.order

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("categories", category_id, update_data)

    updated = await get_document("categories", category_id)
    return _category_to_response(category_id, updated)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user: dict = Depends(require_admin),
):
    """Delete category (Admin only)"""
    category_data = await get_document("categories", category_id)

    if not category_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if category has courses
    db = get_firestore()
    courses_query = db.collection("courses").where("categoryId", "==", category_id).limit(1)
    if list(courses_query.stream()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with associated courses"
        )

    # Check if category has children
    children_query = db.collection("categories").where("parentId", "==", category_id).limit(1)
    if list(children_query.stream()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with subcategories"
        )

    await delete_document("categories", category_id)


# ============== TAG ENDPOINTS ==============
@router.get("/tags/all", response_model=List[TagResponse])
async def list_tags(
    current_user: dict = Depends(get_current_user),
):
    """List all tags"""
    tags = await get_collection("tags")

    return [
        _tag_to_response(tag_id, tag_data)
        for tag_id, tag_data in tags.items()
    ]


@router.get("/tags/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get tag by ID"""
    tag_data = await get_document("tags", tag_id)

    if not tag_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    return _tag_to_response(tag_id, tag_data)


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    request: TagCreateRequest,
    current_user: dict = Depends(require_admin),
):
    """Create a new tag (Admin only)"""
    db = get_firestore()

    tag_id = str(uuid.uuid4())
    tag_data = {
        "name": request.name,
        "color": request.color,
        "usageCount": 0,
        "createdAt": datetime.utcnow(),
    }

    db.collection("tags").document(tag_id).set(tag_data)

    return _tag_to_response(tag_id, tag_data)


@router.put("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    request: TagUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    """Update tag (Admin only)"""
    tag_data = await get_document("tags", tag_id)

    if not tag_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.color is not None:
        update_data["color"] = request.color

    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await update_document("tags", tag_id, update_data)

    updated = await get_document("tags", tag_id)
    return _tag_to_response(tag_id, updated)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    current_user: dict = Depends(require_admin),
):
    """Delete tag (Admin only)"""
    tag_data = await get_document("tags", tag_id)

    if not tag_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    await delete_document("tags", tag_id)
