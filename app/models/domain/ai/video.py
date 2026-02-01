"""
AI Generated Video models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class VideoGenerationStatus(str, Enum):
    """Video generation status"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoStyle(str, Enum):
    """Video style/type"""
    EXPLAINER = "explainer"  # Modern animated explainer
    WHITEBOARD = "whiteboard"  # Whiteboard drawing style
    SLIDESHOW = "slideshow"  # Animated slideshow
    DOCUMENTARY = "documentary"  # Documentary style
    TUTORIAL = "tutorial"  # Step-by-step tutorial


# Default durations for each style (in seconds)
VIDEO_STYLE_DURATIONS: Dict[VideoStyle, int] = {
    VideoStyle.EXPLAINER: 120,  # 2 min
    VideoStyle.WHITEBOARD: 180,  # 3 min
    VideoStyle.SLIDESHOW: 90,  # 1.5 min
    VideoStyle.DOCUMENTARY: 240,  # 4 min
    VideoStyle.TUTORIAL: 300,  # 5 min
}

# Style descriptions for prompts
VIDEO_STYLE_DESCRIPTIONS: Dict[VideoStyle, str] = {
    VideoStyle.EXPLAINER: "Video explicativo moderno con animaciones 2D/3D, texto flotante y metáforas visuales",
    VideoStyle.WHITEBOARD: "Estilo animación de pizarra con mano dibujando diagramas y texto",
    VideoStyle.SLIDESHOW: "Presentación animada con transiciones dinámicas y viñetas",
    VideoStyle.DOCUMENTARY: "Estilo documental con imágenes reales y narración superpuesta",
    VideoStyle.TUTORIAL: "Tutorial paso a paso con demostraciones y grabaciones de pantalla",
}


class VideoGenerationConfig(BaseModel):
    """Configuration for video generation"""
    style: VideoStyle = VideoStyle.EXPLAINER
    max_duration_seconds: int = Field(120, alias="maxDurationSeconds")
    aspect_ratio: str = Field("16:9", alias="aspectRatio")
    quality: str = "hd"
    include_narration: bool = Field(True, alias="includeNarration")
    narration_voice: str = Field("es-ES-Neural2-B", alias="narrationVoice")

    class Config:
        populate_by_name = True


class GeneratedVideo(BaseModel):
    """AI generated video"""
    id: str
    title: str
    prompt: str
    script: Optional[str] = None
    video_url: Optional[str] = Field(None, alias="videoUrl")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    duration_seconds: int = Field(0, alias="durationSeconds")
    status: VideoGenerationStatus = VideoGenerationStatus.PENDING
    style: VideoStyle = VideoStyle.EXPLAINER
    job_id: Optional[str] = Field(None, alias="jobId")  # Veo 3 job ID
    lesson_id: Optional[str] = Field(None, alias="lessonId")
    course_id: Optional[str] = Field(None, alias="courseId")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")

    class Config:
        populate_by_name = True

    @property
    def is_completed(self) -> bool:
        return self.status == VideoGenerationStatus.COMPLETED

    @property
    def is_processing(self) -> bool:
        return self.status == VideoGenerationStatus.GENERATING

    @property
    def has_failed(self) -> bool:
        return self.status == VideoGenerationStatus.FAILED

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "GeneratedVideo":
        if doc_id:
            doc_dict["id"] = doc_id

        # Handle timestamps
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        if "completedAt" in doc_dict and hasattr(doc_dict["completedAt"], "seconds"):
            doc_dict["completedAt"] = datetime.fromtimestamp(doc_dict["completedAt"].seconds)

        # Parse enums
        if "status" in doc_dict and isinstance(doc_dict["status"], str):
            doc_dict["status"] = VideoGenerationStatus(doc_dict["status"])
        if "style" in doc_dict and isinstance(doc_dict["style"], str):
            doc_dict["style"] = VideoStyle(doc_dict["style"])

        return cls(**doc_dict)
