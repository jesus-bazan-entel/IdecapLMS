"""
Unified Prompt Service
Provides assembled prompts for all AI modules using the 3-layer architecture:
1. Master Prompt (Core Pedagogy)
2. Structure Template (Content Organization)
3. Module Extension (Module-specific instructions)
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.firebase_admin import get_document, set_document
from app.models.domain.ai.prompt_config import (
    AIModule,
    GenerationContext,
    DEFAULT_MASTER_PROMPT,
    DEFAULT_STRUCTURE_TEMPLATE,
    DEFAULT_MODULE_EXTENSIONS,
)

logger = logging.getLogger(__name__)

COLLECTION = "ai_studio_config"


class UnifiedPromptService:
    """Service for assembling prompts from the 3-layer architecture"""

    _instance = None
    _cache: Dict[str, Any] = {}
    _cache_timestamp: Optional[datetime] = None
    _cache_ttl_seconds = 300  # 5 minutes cache

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _get_cached_or_fetch(self, doc_id: str, default_data: dict) -> dict:
        """Get from cache or fetch from Firestore"""
        now = datetime.utcnow()

        # Check cache validity
        if self._cache_timestamp and (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds:
            if doc_id in self._cache:
                return self._cache[doc_id]

        # Fetch from Firestore
        doc = await get_document(COLLECTION, doc_id)
        if not doc:
            # Create default
            await set_document(COLLECTION, doc_id, default_data)
            doc = default_data

        # Update cache
        self._cache[doc_id] = doc
        self._cache_timestamp = now

        return doc

    def clear_cache(self):
        """Clear the prompt cache"""
        self._cache = {}
        self._cache_timestamp = None
        logger.info("Prompt cache cleared")

    async def get_master_prompt(self) -> dict:
        """Get the master prompt"""
        default = {
            "id": "master_prompt",
            "content": DEFAULT_MASTER_PROMPT,
            "current_version": 1,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        return await self._get_cached_or_fetch("master_prompt", default)

    async def get_structure_template(self) -> dict:
        """Get the structure template"""
        default = {
            "id": "structure_template",
            "content": DEFAULT_STRUCTURE_TEMPLATE,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        return await self._get_cached_or_fetch("structure_template", default)

    async def get_module_extension(self, module: str) -> dict:
        """Get the extension for a specific module"""
        doc_id = f"extension_{module}"

        if module not in DEFAULT_MODULE_EXTENSIONS:
            raise ValueError(f"Unknown module: {module}")

        default_ext = DEFAULT_MODULE_EXTENSIONS[module]
        default = {
            "id": doc_id,
            "module": module,
            "name": default_ext["name"],
            "description": default_ext["description"],
            "content": default_ext["content"],
            "parameters": default_ext["parameters"],
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        return await self._get_cached_or_fetch(doc_id, default)

    def _replace_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Replace {{variable}} placeholders in template"""
        result = template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    async def assemble_prompt(
        self,
        module: AIModule,
        context: GenerationContext,
        include_structure: bool = True,
    ) -> str:
        """
        Assemble the complete prompt for a generation request.

        Args:
            module: The AI module to generate for
            context: The generation context with topic, level, etc.
            include_structure: Whether to include the structure template

        Returns:
            The fully assembled prompt string
        """
        # Get all layers
        master = await self.get_master_prompt()
        structure = await self.get_structure_template() if include_structure else {"content": ""}
        extension = await self.get_module_extension(module.value)

        # Prepare variables
        variables = {
            "tema": context.tema,
            "nivel": context.nivel,
            "unidad": context.unidad or "General",
            "duracion": context.duracion or "Variable",
            "objetivo": context.objetivo or "Dominar el tema presentado",
            "idioma_base": context.idioma_base,
            "idioma_objetivo": context.idioma_objetivo,
        }

        # Add module-specific parameters
        for key, value in context.module_params.items():
            variables[key] = value

        # Process each layer
        master_content = self._replace_variables(master["content"], variables)
        structure_content = self._replace_variables(structure.get("content", ""), variables)
        extension_content = self._replace_variables(extension["content"], variables)

        # Assemble final prompt
        parts = [master_content]

        if include_structure and structure_content:
            parts.append("---\n\n" + structure_content)

        parts.append("---\n\n" + extension_content)

        # Add generation data
        data_section = f"""
---

## DATOS DE GENERACIÓN
- Tema: {context.tema}
- Nivel: {context.nivel}
- Unidad: {context.unidad or 'N/A'}
- Duración: {context.duracion or 'Variable'}
- Objetivo: {context.objetivo or 'Dominar el tema presentado'}
"""

        if context.additional_context:
            data_section += f"\n## CONTEXTO ADICIONAL\n{context.additional_context}\n"

        data_section += "\nGenera el contenido completo siguiendo todas las instrucciones anteriores."

        parts.append(data_section)

        return "\n\n".join(parts)

    async def get_quick_prompt(
        self,
        module: AIModule,
        topic: str,
        level: str = "basico",
        **kwargs
    ) -> str:
        """
        Convenience method for quick prompt assembly.

        Args:
            module: The AI module
            topic: The topic to generate about
            level: Difficulty level
            **kwargs: Additional context parameters

        Returns:
            Assembled prompt string
        """
        context = GenerationContext(
            tema=topic,
            nivel=level,
            unidad=kwargs.get("unidad"),
            duracion=kwargs.get("duracion"),
            objetivo=kwargs.get("objetivo"),
            additional_context=kwargs.get("additional_context"),
            module_params=kwargs.get("module_params", {})
        )

        return await self.assemble_prompt(module, context)

    async def get_module_parameters(self, module: str) -> Dict[str, Any]:
        """Get the default parameters for a module"""
        extension = await self.get_module_extension(module)
        return extension.get("parameters", {})


# Singleton instance
_prompt_service: Optional[UnifiedPromptService] = None


def get_unified_prompt_service() -> UnifiedPromptService:
    """Get the unified prompt service singleton"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = UnifiedPromptService()
    return _prompt_service
