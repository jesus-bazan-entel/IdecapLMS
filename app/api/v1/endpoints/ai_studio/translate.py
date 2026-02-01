"""
AI Studio - Translation endpoints
Text translation using Google Cloud Translation API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import logging

from app.core.security import get_current_user, require_author
from app.core.firebase_admin import get_firestore
from app.services.ai.translate_service import get_translate_service
from app.models.domain.ai.translate import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response schemas
class TranslateRequest(BaseModel):
    """Request to translate text"""
    text: str = Field(..., min_length=1, max_length=10000)
    source_language: str = Field(
        default="auto",
        description="Source language code (es, pt) or 'auto' for detection"
    )
    target_language: str = Field(
        ...,
        description="Target language code (es, pt)"
    )


class TranslateResponse(BaseModel):
    """Translation response"""
    translated_text: str
    detected_language: str
    source_language: str
    target_language: str
    confidence: float = 1.0


class DetectLanguageRequest(BaseModel):
    """Request to detect language"""
    text: str = Field(..., min_length=1, max_length=5000)


class DetectLanguageResponse(BaseModel):
    """Language detection response"""
    language: str
    confidence: float = 1.0


class SupportedLanguage(BaseModel):
    """Supported language info"""
    code: str
    name: str
    native_name: str
    flag: str


@router.get("/languages", response_model=List[SupportedLanguage])
async def list_supported_languages(
    current_user: dict = Depends(get_current_user),
):
    """
    List supported languages for translation.
    Currently supports Spanish (es) and Portuguese (pt) for the language course.
    """
    return [
        SupportedLanguage(**lang_info)
        for lang_info in SUPPORTED_LANGUAGES.values()
    ]


@router.post("", response_model=TranslateResponse)
async def translate_text(
    request: TranslateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Translate text between Spanish and Portuguese using Google Cloud Translation API.

    - **text**: Text to translate (max 10,000 characters)
    - **source_language**: Source language code ('es', 'pt', or 'auto' for detection)
    - **target_language**: Target language code ('es' or 'pt')
    """
    # Validate target language
    if request.target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target language: {request.target_language}. "
                   f"Supported languages: {list(SUPPORTED_LANGUAGES.keys())}"
        )

    # Validate source language if specified
    if request.source_language != "auto" and request.source_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source language: {request.source_language}. "
                   f"Use 'auto' for detection or specify: {list(SUPPORTED_LANGUAGES.keys())}"
        )

    try:
        translate_service = get_translate_service()

        translated_text, detected_language, confidence = await translate_service.translate(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
        )

        # Optionally save to history (for analytics/learning)
        try:
            db = get_firestore()
            db.collection("translation_history").add({
                "sourceText": request.text[:500],  # Limit stored text
                "translatedText": translated_text[:500],
                "sourceLanguage": detected_language,
                "targetLanguage": request.target_language,
                "createdBy": current_user["id"],
                "createdAt": datetime.utcnow(),
            })
        except Exception as e:
            logger.warning(f"Failed to save translation history: {e}")

        return TranslateResponse(
            translated_text=translated_text,
            detected_language=detected_language,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=confidence,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al traducir el texto. Por favor intenta de nuevo."
        )


@router.post("/detect", response_model=DetectLanguageResponse)
async def detect_language(
    request: DetectLanguageRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Detect the language of the given text.

    Returns the detected language code ('es' or 'pt') and confidence score.
    """
    try:
        translate_service = get_translate_service()

        language, confidence = await translate_service.detect_language(request.text)

        return DetectLanguageResponse(
            language=language,
            confidence=confidence,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al detectar el idioma. Por favor intenta de nuevo."
        )
