"""
AI Generated Mind Map models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MindMapLayout(str, Enum):
    """Mind map layout options"""
    RADIAL = "radial"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    ORGANIC = "organic"


# Color palette for mind map nodes
MINDMAP_COLORS = [
    "#4F46E5",  # Indigo (root)
    "#8B5CF6",  # Purple (level 1)
    "#06B6D4",  # Cyan (level 2)
    "#10B981",  # Emerald (level 3)
    "#F59E0B",  # Amber (level 4)
    "#EF4444",  # Red
    "#EC4899",  # Pink
    "#6366F1",  # Light Indigo
]


class MindMapNode(BaseModel):
    """Mind map node (recursive structure)"""
    id: str
    label: str
    description: Optional[str] = None
    color: str = "#4F46E5"
    level: int = 0
    children: List["MindMapNode"] = Field(default_factory=list)

    class Config:
        populate_by_name = True

    @property
    def total_nodes(self) -> int:
        """Count total nodes in this subtree"""
        count = 1
        for child in self.children:
            count += child.total_nodes
        return count

    @property
    def max_depth(self) -> int:
        """Get maximum depth of this subtree"""
        if not self.children:
            return 0
        return 1 + max(child.max_depth for child in self.children)

    @classmethod
    def from_dict(cls, data: dict) -> "MindMapNode":
        """Create node from dictionary (handles recursive children)"""
        children = data.get("children", [])
        if children:
            data["children"] = [
                cls.from_dict(c) if isinstance(c, dict) else c
                for c in children
            ]
        return cls(**data)


# Enable recursive model
MindMapNode.model_rebuild()


class MindMap(BaseModel):
    """Complete mind map structure"""
    id: str
    topic: str
    level: str = "basic"
    language: str = "spanish"
    root_node: MindMapNode = Field(..., alias="rootNode")
    layout: MindMapLayout = MindMapLayout.RADIAL
    image_url: Optional[str] = Field(None, alias="imageUrl")
    lesson_id: Optional[str] = Field(None, alias="lessonId")
    course_id: Optional[str] = Field(None, alias="courseId")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    class Config:
        populate_by_name = True

    @property
    def total_nodes(self) -> int:
        return self.root_node.total_nodes

    @property
    def max_depth(self) -> int:
        return self.root_node.max_depth

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "MindMap":
        if doc_id:
            doc_dict["id"] = doc_id
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)

        # Parse root node
        if "rootNode" in doc_dict and isinstance(doc_dict["rootNode"], dict):
            doc_dict["rootNode"] = MindMapNode.from_dict(doc_dict["rootNode"])

        return cls(**doc_dict)
