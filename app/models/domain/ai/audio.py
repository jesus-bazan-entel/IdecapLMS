"""
AI Generated Audio models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TTSVoice(BaseModel):
    """Text-to-Speech voice configuration"""
    id: str
    name: str
    description: str
    gender: str  # male, female, neutral
    language_code: str = Field(..., alias="languageCode")

    class Config:
        populate_by_name = True


# Available voices for Google Cloud TTS
AVAILABLE_VOICES: List[TTSVoice] = [
    # Spanish voices
    TTSVoice(id="es-ES-Standard-A", name="Elena", description="Voz femenina estándar", gender="female", languageCode="es-ES"),
    TTSVoice(id="es-ES-Standard-B", name="Carlos", description="Voz masculina estándar", gender="male", languageCode="es-ES"),
    TTSVoice(id="es-ES-Neural2-A", name="Sofia", description="Voz femenina neural", gender="female", languageCode="es-ES"),
    TTSVoice(id="es-ES-Neural2-B", name="Miguel", description="Voz masculina neural", gender="male", languageCode="es-ES"),
    TTSVoice(id="es-US-Standard-A", name="María", description="Voz femenina latinoamericana", gender="female", languageCode="es-US"),
    TTSVoice(id="es-US-Standard-B", name="José", description="Voz masculina latinoamericana", gender="male", languageCode="es-US"),
    # Portuguese voices
    TTSVoice(id="pt-BR-Standard-A", name="Ana", description="Voz femenina brasileña", gender="female", languageCode="pt-BR"),
    TTSVoice(id="pt-BR-Standard-B", name="Pedro", description="Voz masculina brasileña", gender="male", languageCode="pt-BR"),
    TTSVoice(id="pt-BR-Neural2-A", name="Camila", description="Voz femenina neural brasileña", gender="female", languageCode="pt-BR"),
    TTSVoice(id="pt-BR-Neural2-B", name="Lucas", description="Voz masculina neural brasileña", gender="male", languageCode="pt-BR"),
    TTSVoice(id="pt-PT-Standard-A", name="Inês", description="Voz femenina portuguesa", gender="female", languageCode="pt-PT"),
    TTSVoice(id="pt-PT-Standard-B", name="João", description="Voz masculina portuguesa", gender="male", languageCode="pt-PT"),
]


class GeneratedAudio(BaseModel):
    """Generated audio from TTS"""
    id: str
    text: str
    voice: str
    speed: float = 1.0
    audio_url: str = Field(..., alias="audioUrl")
    duration_seconds: int = Field(0, alias="durationSeconds")
    language_code: str = Field("es-ES", alias="languageCode")
    lesson_id: Optional[str] = Field(None, alias="lessonId")
    course_id: Optional[str] = Field(None, alias="courseId")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "GeneratedAudio":
        if doc_id:
            doc_dict["id"] = doc_id
        if "createdAt" in doc_dict and hasattr(doc_dict["createdAt"], "seconds"):
            doc_dict["createdAt"] = datetime.fromtimestamp(doc_dict["createdAt"].seconds)
        return cls(**doc_dict)
