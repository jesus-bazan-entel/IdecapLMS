"""
AI Translation models for Google Cloud Translation API
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TranslateRequest(BaseModel):
    """Request to translate text"""
    text: str = Field(..., min_length=1, max_length=10000)
    source_language: str = Field(default="auto", description="Source language code (es, pt) or 'auto' for detection")
    target_language: str = Field(..., description="Target language code (es, pt)")


class TranslateResponse(BaseModel):
    """Translation response"""
    translated_text: str
    detected_language: str
    source_language: str
    target_language: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DetectLanguageRequest(BaseModel):
    """Request to detect language"""
    text: str = Field(..., min_length=1, max_length=5000)


class DetectLanguageResponse(BaseModel):
    """Language detection response"""
    language: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class TranslationHistory(BaseModel):
    """Translation history record"""
    id: str
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

    @classmethod
    def from_firestore(cls, doc_dict: dict, doc_id: str = None) -> "TranslationHistory":
        if doc_id:
            doc_dict["id"] = doc_id
        if "created_at" in doc_dict and hasattr(doc_dict["created_at"], "seconds"):
            doc_dict["created_at"] = datetime.fromtimestamp(doc_dict["created_at"].seconds)
        return cls(**doc_dict)


# Supported languages for the Portuguese course
SUPPORTED_LANGUAGES = {
    "es": {
        "code": "es",
        "name": "Español",
        "native_name": "Español",
        "flag": "🇵🇪",
    },
    "pt": {
        "code": "pt",
        "name": "Portugués",
        "native_name": "Português",
        "flag": "🇧🇷",
    },
}
