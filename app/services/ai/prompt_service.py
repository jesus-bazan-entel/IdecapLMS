"""
Prompt Service for AI Studio Content Generation
Provides prompts based on the master knowledge base for educational content.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

from app.services.ai.knowledge import (
    get_master_prompt,
    get_audio_prompt,
    get_presentation_prompt,
    get_mindmap_prompt,
    get_podcast_prompt,
    get_video_prompt,
    VOICES,
    LEVELS,
    CONTENT_TYPES,
)

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    AUDIO_TTS = "audio_tts"
    PRESENTATION = "presentation"
    MINDMAP = "mindmap"
    PODCAST = "podcast"
    VIDEO = "video"


class PromptService:
    """Service for generating educational content prompts."""

    def __init__(self):
        self._master_prompt = get_master_prompt()

    @property
    def master_prompt(self) -> str:
        """Get the complete master prompt."""
        return self._master_prompt

    def get_system_prompt(self, content_type: Optional[ContentType] = None) -> str:
        """
        Get the system prompt for AI content generation.

        Args:
            content_type: Optional content type to include specific guidelines

        Returns:
            System prompt with master prompt and specific guidelines
        """
        base_prompt = f"""Eres un experto en la creación de contenido educativo para la enseñanza
de portugués brasileño a estudiantes hispanohablantes peruanos.

{self._master_prompt}

IMPORTANTE:
- Todo el contenido debe ser apropiado para estudiantes adultos
- Mantén un tono profesional pero accesible
- Incluye siempre ejemplos prácticos
- Destaca los falsos amigos cuando sean relevantes
- Indica la pronunciación de palabras difíciles
"""

        if content_type:
            base_prompt += f"\n\nESTÁS GENERANDO CONTENIDO DE TIPO: {content_type.value.upper()}"

        return base_prompt

    def generate_content_prompt(
        self,
        content_type: ContentType,
        tema: str,
        nivel: str = "básico",
        **kwargs
    ) -> str:
        """
        Generate a specific prompt for content creation.

        Args:
            content_type: Type of content to generate
            tema: Topic/theme of the content
            nivel: Difficulty level (básico, intermedio, avanzado)
            **kwargs: Additional parameters specific to content type

        Returns:
            Formatted prompt for the content type
        """
        if nivel not in LEVELS:
            nivel = "básico"

        prompt_generators = {
            ContentType.AUDIO_TTS: lambda: get_audio_prompt(
                tema=tema,
                nivel=nivel,
                contexto=kwargs.get("contexto", ""),
                voz_es=kwargs.get("voz_es", VOICES["es"]["female"]),
                voz_pt=kwargs.get("voz_pt", VOICES["pt"]["female"])
            ),
            ContentType.PRESENTATION: lambda: get_presentation_prompt(
                tema=tema,
                nivel=nivel,
                num_slides=kwargs.get("num_slides", 10),
                enfoque=kwargs.get("enfoque", "vocabulario")
            ),
            ContentType.MINDMAP: lambda: get_mindmap_prompt(
                tema=tema,
                nivel=nivel,
                enfoque=kwargs.get("enfoque", "vocabulario relacionado")
            ),
            ContentType.PODCAST: lambda: get_podcast_prompt(
                tema=tema,
                nivel=nivel,
                duracion=kwargs.get("duracion", 10),
                formato=kwargs.get("formato", "conversacional"),
                participante_adicional=kwargs.get("participante", "Invitado experto")
            ),
            ContentType.VIDEO: lambda: get_video_prompt(
                tema=tema,
                nivel=nivel,
                tipo_video=kwargs.get("tipo_video", "tutorial"),
                duracion=kwargs.get("duracion", 5)
            ),
        }

        generator = prompt_generators.get(content_type)
        if generator:
            return generator()
        else:
            raise ValueError(f"Unknown content type: {content_type}")

    def get_voices(self, language: str = "pt") -> Dict[str, str]:
        """
        Get available voices for a language.

        Args:
            language: Language code ('es' or 'pt')

        Returns:
            Dictionary with female and male voice names
        """
        return VOICES.get(language, VOICES["pt"])

    def get_available_levels(self) -> list:
        """Get list of available difficulty levels."""
        return LEVELS.copy()

    def get_available_content_types(self) -> list:
        """Get list of available content types."""
        return CONTENT_TYPES.copy()


# Singleton instance
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """Get the singleton prompt service instance."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
