"""
Knowledge Base Module for AI Studio Content Generation
Contains master prompts and templates for educational content.
"""

from .master_prompt import (
    MASTER_PROMPT,
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

__all__ = [
    "MASTER_PROMPT",
    "get_master_prompt",
    "get_audio_prompt",
    "get_presentation_prompt",
    "get_mindmap_prompt",
    "get_podcast_prompt",
    "get_video_prompt",
    "VOICES",
    "LEVELS",
    "CONTENT_TYPES",
]
