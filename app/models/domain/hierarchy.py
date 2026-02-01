"""
Course hierarchy models
Level -> Module -> Section -> Lesson
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class Level(BaseModel):
    """
    Level model - First level in course hierarchy
    Path: courses/{courseId}/levels/{levelId}
    """
    id: str
    course_id: str = Field(..., alias="courseId")
    name: str
    description: str = ""
    order: int = 0
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "Level":
        if doc_id:
            doc_dict["id"] = doc_id
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        if "updatedAt" in doc_dict and hasattr(doc_dict["updatedAt"], "seconds"):
            doc_dict["updatedAt"] = datetime.fromtimestamp(doc_dict["updatedAt"].seconds)
        return cls(**doc_dict)


class Module(BaseModel):
    """
    Module model - Second level in course hierarchy
    Path: courses/{courseId}/levels/{levelId}/modules/{moduleId}
    """
    id: str
    level_id: str = Field(..., alias="levelId")
    course_id: str = Field(..., alias="courseId")
    name: str
    description: str = ""
    order: int = 0
    total_classes: int = Field(16, alias="totalClasses")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "Module":
        if doc_id:
            doc_dict["id"] = doc_id
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        if "updatedAt" in doc_dict and hasattr(doc_dict["updatedAt"], "seconds"):
            doc_dict["updatedAt"] = datetime.fromtimestamp(doc_dict["updatedAt"].seconds)
        return cls(**doc_dict)


class Section(BaseModel):
    """
    Section model - Third level in course hierarchy
    Path: courses/{courseId}/sections/{sectionId} (legacy)
    Or: courses/{courseId}/levels/{levelId}/modules/{moduleId}/sections/{sectionId}
    """
    id: str
    name: str
    order: int = 0

    class Config:
        populate_by_name = True


class LessonContentType(str, Enum):
    """Lesson content type enumeration"""
    VIDEO = "video"
    ARTICLE = "article"
    QUIZ = "quiz"
    DOCUMENT = "document"
    YOUTUBE = "youtube"
    MIXED = "mixed"


class Question(BaseModel):
    """Quiz question model"""
    question_title: str = Field(..., alias="questionTitle")
    options: List[str] = Field(default_factory=list)
    correct_answer_index: int = Field(0, alias="correctAnswerIndex")

    class Config:
        populate_by_name = True


class DocumentType(str, Enum):
    """Document type enumeration"""
    WORD = "word"
    PDF = "pdf"
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"


class LessonMaterial(BaseModel):
    """Lesson downloadable material"""
    id: str
    name: str
    type: str = DocumentType.PDF
    url: str
    file_size: Optional[int] = Field(None, alias="fileSize")
    mime_type: Optional[str] = Field(None, alias="mimeType")
    uploaded_at: Optional[datetime] = Field(None, alias="uploadedAt")

    class Config:
        populate_by_name = True


class YouTubeVideo(BaseModel):
    """YouTube video embedded data"""
    video_id: str = Field(..., alias="videoId")
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    duration: Optional[int] = None

    class Config:
        populate_by_name = True

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def embed_url(self) -> str:
        return f"https://www.youtube.com/embed/{self.video_id}"


class LocalVideo(BaseModel):
    """Local/uploaded video data"""
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")

    class Config:
        populate_by_name = True


class Lesson(BaseModel):
    """
    Lesson model - Fourth level in course hierarchy
    Path: courses/{courseId}/sections/{sectionId}/lessons/{lessonId}
    Or: courses/{courseId}/levels/{levelId}/modules/{moduleId}/lessons/{lessonId}
    """
    id: str
    name: str
    order: int = 0
    content_type: str = Field(LessonContentType.ARTICLE, alias="contentType")
    description: Optional[str] = None

    # Video content
    video_url: Optional[str] = Field(None, alias="videoUrl")
    vimeo_video_id: Optional[str] = Field(None, alias="vimeoVideoId")
    youtube_video: Optional[YouTubeVideo] = Field(None, alias="youtubeVideo")
    local_video: Optional[LocalVideo] = Field(None, alias="localVideo")

    # Article content
    lesson_body: Optional[str] = Field(None, alias="lessonBody")

    # Quiz content
    questions: Optional[List[Question]] = Field(default_factory=list)

    # Materials
    pdf_links: Optional[List[str]] = Field(default_factory=list, alias="pdfLinks")
    materials: Optional[List[LessonMaterial]] = Field(default_factory=list)

    # References
    course_id: Optional[str] = Field(None, alias="courseId")
    level_id: Optional[str] = Field(None, alias="levelId")
    module_id: Optional[str] = Field(None, alias="moduleId")
    section_id: Optional[str] = Field(None, alias="sectionId")

    # Metadata
    duration: int = 0
    is_free: bool = Field(False, alias="isFree")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "Lesson":
        if doc_id:
            doc_dict["id"] = doc_id

        # Handle timestamps
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        if "updatedAt" in doc_dict and hasattr(doc_dict["updatedAt"], "seconds"):
            doc_dict["updatedAt"] = datetime.fromtimestamp(doc_dict["updatedAt"].seconds)

        # Handle questions
        if "quiz" in doc_dict and "questions" not in doc_dict:
            doc_dict["questions"] = doc_dict.pop("quiz")

        return cls(**doc_dict)

    def to_firestore(self) -> dict:
        """Convert to Firestore document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        data.pop("id", None)
        return data
