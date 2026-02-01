"""
AI Studio - Mind Maps endpoints
Generate interactive mind maps with AI using Gemini
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import logging

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore, get_document, update_document
from app.services.ai.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

router = APIRouter()


class MindMapStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# Color palette for mind map nodes
MINDMAP_COLORS = [
    "#6366f1",  # Indigo (root)
    "#8b5cf6",  # Purple
    "#ec4899",  # Pink
    "#f97316",  # Orange
    "#22c55e",  # Green
    "#06b6d4",  # Cyan
    "#3b82f6",  # Blue
]


# Request/Response schemas
class MindMapNode(BaseModel):
    """Single node in a mind map"""
    id: str
    label: str
    color: str = "#6366f1"
    level: int = 0
    children: List["MindMapNode"] = []


# Update forward reference
MindMapNode.model_rebuild()


class MindMapGenerateRequest(BaseModel):
    """Request to generate a mind map"""
    topic: str
    depth: int = 3  # Levels of depth (1-5)
    language: str = "es"
    additional_context: Optional[str] = None
    lesson_id: Optional[str] = None


class MindMapResponse(BaseModel):
    """Mind map response"""
    id: str
    title: str
    topic: str
    status: str
    root_node: Optional[MindMapNode] = None
    total_nodes: int = 0
    created_at: datetime
    lesson_id: Optional[str] = None
    error_message: Optional[str] = None


class MindMapListResponse(BaseModel):
    """List of mind maps"""
    mindmaps: List[MindMapResponse]
    total: int


def _count_nodes(node: dict) -> int:
    """Recursively count nodes in a mind map"""
    if not node:
        return 0
    count = 1
    for child in node.get("children", []):
        count += _count_nodes(child)
    return count


def _assign_colors(node: dict, level: int = 0) -> dict:
    """Recursively assign colors to nodes based on level"""
    color = MINDMAP_COLORS[level % len(MINDMAP_COLORS)]
    node["color"] = color
    node["level"] = level

    if "children" in node:
        for child in node["children"]:
            _assign_colors(child, level + 1)

    return node


def _dict_to_node(data: dict) -> MindMapNode:
    """Convert dict to MindMapNode"""
    children = [_dict_to_node(c) for c in data.get("children", [])]
    return MindMapNode(
        id=data.get("id", str(uuid.uuid4())),
        label=data.get("label", ""),
        color=data.get("color", "#6366f1"),
        level=data.get("level", 0),
        children=children,
    )


def _mindmap_to_response(mm_id: str, data: dict) -> MindMapResponse:
    root_data = data.get("rootNode")
    root_node = _dict_to_node(root_data) if root_data else None
    total_nodes = _count_nodes(root_data) if root_data else 0

    return MindMapResponse(
        id=mm_id,
        title=data.get("title", ""),
        topic=data.get("topic", ""),
        status=data.get("status", "pending"),
        root_node=root_node,
        total_nodes=total_nodes,
        created_at=data.get("createdAt", datetime.utcnow()),
        lesson_id=data.get("lessonId"),
        error_message=data.get("errorMessage"),
    )


@router.get("/colors")
async def get_color_palette(
    current_user: dict = Depends(get_current_user),
):
    """
    Get available color palette for mind map nodes
    """
    return {
        "colors": MINDMAP_COLORS,
        "description": "Colores organizados por nivel de profundidad"
    }


@router.post("/generate", response_model=MindMapResponse)
async def generate_mindmap(
    request: MindMapGenerateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Generate a mind map with AI (synchronous)
    Author or Admin only
    """
    if request.depth < 1 or request.depth > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Depth must be between 1 and 5"
        )

    db = get_firestore()
    mm_id = str(uuid.uuid4())

    # Create mind map document
    mm_data = {
        "title": f"Mapa Mental: {request.topic[:50]}",
        "topic": request.topic,
        "depth": request.depth,
        "language": request.language,
        "additionalContext": request.additional_context,
        "status": MindMapStatus.GENERATING.value,
        "rootNode": None,
        "lessonId": request.lesson_id,
        "createdBy": current_user["id"],
        "createdAt": datetime.utcnow(),
    }

    db.collection("mindmaps").document(mm_id).set(mm_data)
    logger.info(f"Starting mind map generation for {mm_id}: {request.topic}")

    try:
        # Generate mind map with Gemini
        gemini = get_gemini_service()
        root_node = await gemini.generate_mindmap(
            topic=request.topic,
            depth=request.depth,
            language=request.language,
            additional_context=request.additional_context,
        )

        # Assign colors based on levels
        root_node = _assign_colors(root_node)

        # Update document with success
        db.collection("mindmaps").document(mm_id).update({
            "status": MindMapStatus.COMPLETED.value,
            "rootNode": root_node,
            "updatedAt": datetime.utcnow(),
        })

        total_nodes = _count_nodes(root_node)
        logger.info(f"Mind map generated successfully for {mm_id}: {total_nodes} nodes")

    except Exception as e:
        logger.error(f"Mind map generation failed for {mm_id}: {e}")
        db.collection("mindmaps").document(mm_id).update({
            "status": MindMapStatus.FAILED.value,
            "errorMessage": str(e),
            "updatedAt": datetime.utcnow(),
        })

    # Return final state
    final_data = await get_document("mindmaps", mm_id)
    return _mindmap_to_response(mm_id, final_data)


@router.get("", response_model=MindMapListResponse)
async def list_mindmaps(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    List generated mind maps
    """
    db = get_firestore()
    query = db.collection("mindmaps")

    if lesson_id:
        query = query.where("lessonId", "==", lesson_id)

    # Filter by user if not admin
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role:
        query = query.where("createdBy", "==", current_user["id"])

    docs = list(query.order_by("createdAt", direction="DESCENDING").limit(50).stream())

    mindmaps = [_mindmap_to_response(doc.id, doc.to_dict()) for doc in docs]

    return MindMapListResponse(
        mindmaps=mindmaps,
        total=len(mindmaps)
    )


@router.get("/{mindmap_id}", response_model=MindMapResponse)
async def get_mindmap(
    mindmap_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get mind map by ID
    """
    mm_data = await get_document("mindmaps", mindmap_id)

    if not mm_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mind map not found"
        )

    return _mindmap_to_response(mindmap_id, mm_data)


@router.delete("/{mindmap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mindmap(
    mindmap_id: str,
    current_user: dict = Depends(require_author),
):
    """
    Delete mind map
    Author or Admin only
    """
    db = get_firestore()
    mm_ref = db.collection("mindmaps").document(mindmap_id)
    doc = mm_ref.get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mind map not found"
        )

    # Verify ownership or admin
    data = doc.to_dict()
    role = current_user.get("role", [])
    if isinstance(role, str):
        role = [role]

    if "admin" not in role and data.get("createdBy") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this mind map"
        )

    mm_ref.delete()
