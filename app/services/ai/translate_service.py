"""
Google Cloud Translation API Service
Provides translation between Spanish and Portuguese for the language course
"""
import logging
from typing import Optional, Tuple
from functools import lru_cache

from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

from app.config import settings

logger = logging.getLogger(__name__)


class TranslateService:
    """Service for text translation using Google Cloud Translation API"""

    def __init__(self):
        self._client: Optional[translate.Client] = None

    @property
    def client(self) -> translate.Client:
        """Lazy initialization of the translation client"""
        if self._client is None:
            try:
                import os
                cred_path = settings.firebase_service_account_path

                # Check if service account file exists (local development)
                if os.path.exists(cred_path):
                    credentials = service_account.Credentials.from_service_account_file(cred_path)
                    self._client = translate.Client(credentials=credentials)
                    logger.info("Google Translate client initialized with service account file")
                else:
                    # Use Application Default Credentials (Cloud Run, GCE, etc.)
                    self._client = translate.Client()
                    logger.info("Google Translate client initialized with ADC")
            except Exception as e:
                logger.error(f"Failed to initialize Google Translate client: {e}")
                raise
        return self._client

    async def translate(
        self,
        text: str,
        source_language: str = "auto",
        target_language: str = "pt",
    ) -> Tuple[str, str, float]:
        """
        Translate text between languages.

        Args:
            text: Text to translate
            source_language: Source language code ('es', 'pt', or 'auto' for detection)
            target_language: Target language code ('es' or 'pt')

        Returns:
            Tuple of (translated_text, detected_language, confidence)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Normalize language codes
        source_lang = None if source_language == "auto" else self._normalize_language(source_language)
        target_lang = self._normalize_language(target_language)

        if source_lang == target_lang and source_lang is not None:
            return text, source_lang, 1.0

        try:
            # Call Google Cloud Translation API
            result = self.client.translate(
                text,
                source_language=source_lang,
                target_language=target_lang,
            )

            translated_text = result["translatedText"]
            detected_language = result.get("detectedSourceLanguage", source_lang or "es")

            # Normalize detected language to our supported codes
            detected_language = self._normalize_to_supported(detected_language)

            logger.info(
                f"Translation successful: {detected_language} -> {target_lang}, "
                f"text length: {len(text)} -> {len(translated_text)}"
            )

            return translated_text, detected_language, 1.0

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    async def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect the language of the given text.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            result = self.client.detect_language(text)

            language = result["language"]
            confidence = result.get("confidence", 1.0)

            # Normalize to our supported languages
            language = self._normalize_to_supported(language)

            logger.info(f"Language detected: {language} (confidence: {confidence})")

            return language, confidence

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise

    def _normalize_language(self, lang_code: str) -> str:
        """Normalize language code to Google Translate format"""
        lang_map = {
            "es": "es",
            "spanish": "es",
            "español": "es",
            "pt": "pt",
            "portuguese": "pt",
            "português": "pt",
            "pt-br": "pt",
            "pt-pt": "pt",
        }
        return lang_map.get(lang_code.lower(), lang_code.lower())

    def _normalize_to_supported(self, lang_code: str) -> str:
        """Normalize detected language to our supported languages (es/pt)"""
        lang_code = lang_code.lower()

        # Spanish variants
        if lang_code in ["es", "es-419", "es-es", "es-mx", "es-pe"]:
            return "es"

        # Portuguese variants
        if lang_code in ["pt", "pt-br", "pt-pt"]:
            return "pt"

        # Default to Spanish for unsupported languages in this course context
        return "es"


# Singleton instance
_translate_service: Optional[TranslateService] = None


def get_translate_service() -> TranslateService:
    """Get the singleton translate service instance"""
    global _translate_service
    if _translate_service is None:
        _translate_service = TranslateService()
    return _translate_service
