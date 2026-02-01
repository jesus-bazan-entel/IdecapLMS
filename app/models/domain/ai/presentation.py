"""
AI Generated Presentation models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SlideType(str, Enum):
    """Slide type enumeration"""
    TITLE = "title"
    CONTENT = "content"
    IMAGE = "image"
    QUOTE = "quote"
    SUMMARY = "summary"


class Slide(BaseModel):
    """Single presentation slide"""
    order: int
    title: str
    content: str = ""
    bullet_points: List[str] = Field(default_factory=list, alias="bulletPoints")
    image_url: Optional[str] = Field(None, alias="imageUrl")
    image_prompt: Optional[str] = Field(None, alias="imagePrompt")
    type: SlideType = SlideType.CONTENT

    class Config:
        populate_by_name = True


class PresentationTemplate(BaseModel):
    """Presentation visual template"""
    id: str
    name: str
    primary_color: str = Field("#4F46E5", alias="primaryColor")
    secondary_color: str = Field("#8B5CF6", alias="secondaryColor")
    font_family: str = Field("Inter", alias="fontFamily")

    class Config:
        populate_by_name = True


# Available templates
PRESENTATION_TEMPLATES = [
    PresentationTemplate(id="modern", name="Moderno", primaryColor="#4F46E5", secondaryColor="#8B5CF6"),
    PresentationTemplate(id="classic", name="Clásico", primaryColor="#1E3A5F", secondaryColor="#64748B"),
    PresentationTemplate(id="vibrant", name="Vibrante", primaryColor="#EC4899", secondaryColor="#F97316"),
    PresentationTemplate(id="minimal", name="Minimalista", primaryColor="#171717", secondaryColor="#737373"),
]


class Presentation(BaseModel):
    """Generated presentation with slides"""
    id: str
    title: str
    topic: str
    level: str = "basic"
    language: str = "spanish"
    slides: List[Slide] = Field(default_factory=list)
    template_id: str = Field("modern", alias="templateId")
    pdf_url: Optional[str] = Field(None, alias="pdfUrl")
    pptx_url: Optional[str] = Field(None, alias="pptxUrl")
    lesson_id: Optional[str] = Field(None, alias="lessonId")
    course_id: Optional[str] = Field(None, alias="courseId")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "Presentation":
        if doc_id:
            doc_dict["id"] = doc_id
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)

        # Parse slides
        if "slides" in doc_dict:
            doc_dict["slides"] = [
                Slide(**s) if isinstance(s, dict) else s
                for s in doc_dict["slides"]
            ]

        return cls(**doc_dict)
