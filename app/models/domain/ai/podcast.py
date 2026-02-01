"""
AI Generated Podcast models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class PodcastStyle(str, Enum):
    """Podcast style enumeration"""
    CONVERSATIONAL = "conversational"  # Dialogue between two people
    LECTURE = "lecture"  # Single voice lecture
    INTERVIEW = "interview"  # Q&A format


# Voice configurations for each style
PODCAST_VOICE_CONFIGS: Dict[PodcastStyle, List[Dict[str, str]]] = {
    PodcastStyle.CONVERSATIONAL: [
        {"name": "Ana", "voice": "pt-BR-Neural2-A", "role": "Anfitriona"},
        {"name": "Carlos", "voice": "es-ES-Neural2-B", "role": "Co-anfitrión"},
    ],
    PodcastStyle.LECTURE: [
        {"name": "Profesor", "voice": "es-ES-Neural2-B", "role": "Instructor"},
    ],
    PodcastStyle.INTERVIEW: [
        {"name": "Entrevistador", "voice": "es-ES-Neural2-A", "role": "Conductor"},
        {"name": "Experto", "voice": "es-ES-Neural2-B", "role": "Invitado"},
    ],
}


class PodcastSegment(BaseModel):
    """Single segment of a podcast script"""
    order: int
    speaker: str
    text: str
    voice: str
    start_seconds: Optional[int] = Field(None, alias="startSeconds")
    duration_seconds: Optional[int] = Field(None, alias="durationSeconds")

    class Config:
        populate_by_name = True


class PodcastScript(BaseModel):
    """Generated podcast script (before audio generation)"""
    title: str
    introduction: str = ""
    segments: List[PodcastSegment] = Field(default_factory=list)
    style: PodcastStyle = PodcastStyle.CONVERSATIONAL

    @property
    def full_script(self) -> str:
        """Get full script as formatted text"""
        return "\n\n".join(
            f"{s.speaker}: {s.text}"
            for s in self.segments
        )

    @property
    def estimated_word_count(self) -> int:
        """Estimate total word count"""
        return sum(
            len(s.text.split())
            for s in self.segments
        )


class Podcast(BaseModel):
    """Complete podcast with script and audio"""
    id: str
    title: str
    topic: str
    level: str = "basic"
    language: str = "spanish"
    style: PodcastStyle = PodcastStyle.CONVERSATIONAL
    script: str = ""  # Full text script
    audio_url: Optional[str] = Field(None, alias="audioUrl")
    duration_seconds: int = Field(0, alias="durationSeconds")
    segments: List[PodcastSegment] = Field(default_factory=list)
    lesson_id: Optional[str] = Field(None, alias="lessonId")
    course_id: Optional[str] = Field(None, alias="courseId")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "Podcast":
        if doc_id:
            doc_dict["id"] = doc_id
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)

        # Parse segments
        if "segments" in doc_dict:
            doc_dict["segments"] = [
                PodcastSegment(**s) if isinstance(s, dict) else s
                for s in doc_dict["segments"]
            ]

        # Parse style
        if "style" in doc_dict and isinstance(doc_dict["style"], str):
            doc_dict["style"] = PodcastStyle(doc_dict["style"])

        return cls(**doc_dict)
