"""
AI Studio - Prompt Configuration Endpoints
Manage Master Prompt, Structure Template, and Module Extensions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.core.security import get_current_user, require_admin
from app.core.firebase_admin import get_firestore, get_document, set_document, update_document
from app.models.domain.ai.prompt_config import (
    AIModule,
    MasterPrompt,
    StructureTemplate,
    ModuleExtension,
    PromptVersion,
    GenerationContext,
    MasterPromptUpdate,
    ModuleExtensionUpdate,
    StructureTemplateUpdate,
    PromptPreviewRequest,
    PromptPreviewResponse,
    DEFAULT_MASTER_PROMPT,
    DEFAULT_STRUCTURE_TEMPLATE,
    DEFAULT_MODULE_EXTENSIONS,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Collection name in Firestore
COLLECTION = "ai_studio_config"


# ============== HELPER FUNCTIONS ==============

async def get_or_create_master_prompt() -> dict:
    """Get master prompt from DB or create default"""
    doc = await get_document(COLLECTION, "master_prompt")
    if not doc:
        # Create default
        default_data = {
            "id": "master_prompt",
            "name": "IDECAP AI Studio - Prompt Maestro",
            "description": "Prompt central que define la filosofía y enfoque pedagógico",
            "content": DEFAULT_MASTER_PROMPT,
            "is_active": True,
            "current_version": 1,
            "versions": [{
                "version": 1,
                "content": DEFAULT_MASTER_PROMPT,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": "system",
                "notes": "Versión inicial"
            }],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await set_document(COLLECTION, "master_prompt", default_data)
        return default_data
    return doc


async def get_or_create_structure_template() -> dict:
    """Get structure template from DB or create default"""
    doc = await get_document(COLLECTION, "structure_template")
    if not doc:
        default_data = {
            "id": "structure_template",
            "name": "Plantilla de Estructura Base",
            "content": DEFAULT_STRUCTURE_TEMPLATE,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await set_document(COLLECTION, "structure_template", default_data)
        return default_data
    return doc


async def get_or_create_module_extension(module: str) -> dict:
    """Get module extension from DB or create default"""
    doc_id = f"extension_{module}"
    doc = await get_document(COLLECTION, doc_id)
    if not doc:
        if module not in DEFAULT_MODULE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Module extension '{module}' not found"
            )
        default = DEFAULT_MODULE_EXTENSIONS[module]
        default_data = {
            "id": doc_id,
            "module": module,
            "name": default["name"],
            "description": default["description"],
            "content": default["content"],
            "parameters": default["parameters"],
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await set_document(COLLECTION, doc_id, default_data)
        return default_data
    return doc


def assemble_full_prompt(
    master_prompt: str,
    structure_template: str,
    module_extension: str,
    context: GenerationContext
) -> str:
    """Assemble the complete prompt from all layers"""
    # Replace variables in templates
    variables = {
        "tema": context.tema,
        "nivel": context.nivel,
        "unidad": context.unidad or "General",
        "duracion": context.duracion or "Variable",
        "objetivo": context.objetivo or "Aprender el tema indicado",
        "idioma_base": context.idioma_base,
        "idioma_objetivo": context.idioma_objetivo,
    }

    # Simple variable replacement
    processed_master = master_prompt
    processed_structure = structure_template
    processed_extension = module_extension

    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        processed_master = processed_master.replace(placeholder, str(value))
        processed_structure = processed_structure.replace(placeholder, str(value))
        processed_extension = processed_extension.replace(placeholder, str(value))

    # Assemble final prompt
    full_prompt = f"""{processed_master}

---

{processed_structure}

---

{processed_extension}

---

## DATOS DE GENERACIÓN
- Tema: {context.tema}
- Nivel: {context.nivel}
- Unidad: {context.unidad or 'N/A'}
- Duración: {context.duracion or 'Variable'}
- Objetivo: {context.objetivo or 'Aprender el tema'}

{f"## CONTEXTO ADICIONAL{chr(10)}{context.additional_context}" if context.additional_context else ""}

Genera el contenido completo siguiendo todas las instrucciones anteriores.
"""
    return full_prompt


def estimate_tokens(text: str) -> int:
    """Rough estimate of tokens (1 token ≈ 4 chars for Spanish/Portuguese)"""
    return len(text) // 4


# ============== MASTER PROMPT ENDPOINTS ==============

@router.get("/master-prompt")
async def get_master_prompt(
    current_user: dict = Depends(get_current_user),
):
    """
    Get the current master prompt
    """
    prompt = await get_or_create_master_prompt()
    return prompt


@router.put("/master-prompt")
async def update_master_prompt(
    request: MasterPromptUpdate,
    current_user: dict = Depends(require_admin),
):
    """
    Update the master prompt (creates new version)
    Admin only
    """
    prompt = await get_or_create_master_prompt()

    # Create new version
    new_version = prompt.get("current_version", 1) + 1
    new_version_entry = {
        "version": new_version,
        "content": request.content,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": current_user["id"],
        "notes": request.notes or f"Versión {new_version}"
    }

    versions = prompt.get("versions", [])
    versions.append(new_version_entry)

    # Keep only last 10 versions
    if len(versions) > 10:
        versions = versions[-10:]

    update_data = {
        "content": request.content,
        "current_version": new_version,
        "versions": versions,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": current_user["id"],
    }

    await update_document(COLLECTION, "master_prompt", update_data)

    updated = await get_document(COLLECTION, "master_prompt")
    logger.info(f"Master prompt updated to version {new_version} by {current_user['id']}")
    return updated


@router.get("/master-prompt/versions")
async def get_master_prompt_versions(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all versions of the master prompt
    """
    prompt = await get_or_create_master_prompt()
    return {
        "current_version": prompt.get("current_version", 1),
        "versions": prompt.get("versions", [])
    }


@router.post("/master-prompt/rollback/{version}")
async def rollback_master_prompt(
    version: int,
    current_user: dict = Depends(require_admin),
):
    """
    Rollback master prompt to a specific version
    Admin only
    """
    prompt = await get_or_create_master_prompt()
    versions = prompt.get("versions", [])

    # Find the version
    target_version = None
    for v in versions:
        if v.get("version") == version:
            target_version = v
            break

    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found"
        )

    # Create new version from rollback
    new_version = prompt.get("current_version", 1) + 1
    new_version_entry = {
        "version": new_version,
        "content": target_version["content"],
        "created_at": datetime.utcnow().isoformat(),
        "created_by": current_user["id"],
        "notes": f"Rollback a versión {version}"
    }

    versions.append(new_version_entry)

    update_data = {
        "content": target_version["content"],
        "current_version": new_version,
        "versions": versions,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": current_user["id"],
    }

    await update_document(COLLECTION, "master_prompt", update_data)

    logger.info(f"Master prompt rolled back to version {version} by {current_user['id']}")
    return {"message": f"Rolled back to version {version}", "new_version": new_version}


# ============== STRUCTURE TEMPLATE ENDPOINTS ==============

@router.get("/structure-template")
async def get_structure_template(
    current_user: dict = Depends(get_current_user),
):
    """
    Get the structure template
    """
    template = await get_or_create_structure_template()
    return template


@router.put("/structure-template")
async def update_structure_template(
    request: StructureTemplateUpdate,
    current_user: dict = Depends(require_admin),
):
    """
    Update the structure template
    Admin only
    """
    await get_or_create_structure_template()  # Ensure exists

    update_data = {
        "content": request.content,
        "updated_at": datetime.utcnow().isoformat(),
    }

    await update_document(COLLECTION, "structure_template", update_data)

    updated = await get_document(COLLECTION, "structure_template")
    logger.info(f"Structure template updated by {current_user['id']}")
    return updated


# ============== MODULE EXTENSIONS ENDPOINTS ==============

@router.get("/extensions")
async def list_module_extensions(
    current_user: dict = Depends(get_current_user),
):
    """
    List all available module extensions
    """
    extensions = []
    for module in AIModule:
        ext = await get_or_create_module_extension(module.value)
        extensions.append(ext)
    return {"extensions": extensions}


@router.get("/extensions/{module}")
async def get_module_extension(
    module: AIModule,
    current_user: dict = Depends(get_current_user),
):
    """
    Get a specific module extension
    """
    ext = await get_or_create_module_extension(module.value)
    return ext


@router.put("/extensions/{module}")
async def update_module_extension(
    module: AIModule,
    request: ModuleExtensionUpdate,
    current_user: dict = Depends(require_admin),
):
    """
    Update a module extension
    Admin only
    """
    await get_or_create_module_extension(module.value)  # Ensure exists

    update_data = {
        "content": request.content,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if request.parameters is not None:
        update_data["parameters"] = request.parameters

    doc_id = f"extension_{module.value}"
    await update_document(COLLECTION, doc_id, update_data)

    updated = await get_document(COLLECTION, doc_id)
    logger.info(f"Extension {module.value} updated by {current_user['id']}")
    return updated


# ============== PROMPT ASSEMBLY ENDPOINTS ==============

@router.post("/preview")
async def preview_assembled_prompt(
    request: PromptPreviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Preview the full assembled prompt for a given module and context
    """
    master = await get_or_create_master_prompt()
    structure = await get_or_create_structure_template()
    extension = await get_or_create_module_extension(request.module.value)

    full_prompt = assemble_full_prompt(
        master_prompt=master["content"],
        structure_template=structure["content"],
        module_extension=extension["content"],
        context=request.context
    )

    return PromptPreviewResponse(
        full_prompt=full_prompt,
        master_prompt_version=master.get("current_version", 1),
        module_extension=request.module.value,
        estimated_tokens=estimate_tokens(full_prompt)
    )


@router.get("/modules")
async def list_available_modules(
    current_user: dict = Depends(get_current_user),
):
    """
    List all available AI modules with their default parameters
    """
    modules = []
    for module in AIModule:
        ext = await get_or_create_module_extension(module.value)
        modules.append({
            "id": module.value,
            "name": ext.get("name", module.value),
            "description": ext.get("description", ""),
            "parameters": ext.get("parameters", {}),
            "is_active": ext.get("is_active", True)
        })
    return {"modules": modules}


@router.post("/reset-defaults")
async def reset_to_defaults(
    current_user: dict = Depends(require_admin),
):
    """
    Reset all prompts to default values
    Admin only - USE WITH CAUTION
    """
    db = get_firestore()

    # Reset master prompt
    master_data = {
        "id": "master_prompt",
        "name": "IDECAP AI Studio - Prompt Maestro",
        "description": "Prompt central que define la filosofía y enfoque pedagógico",
        "content": DEFAULT_MASTER_PROMPT,
        "is_active": True,
        "current_version": 1,
        "versions": [{
            "version": 1,
            "content": DEFAULT_MASTER_PROMPT,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user["id"],
            "notes": "Reset a valores por defecto"
        }],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": current_user["id"],
    }
    await set_document(COLLECTION, "master_prompt", master_data)

    # Reset structure template
    structure_data = {
        "id": "structure_template",
        "name": "Plantilla de Estructura Base",
        "content": DEFAULT_STRUCTURE_TEMPLATE,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    await set_document(COLLECTION, "structure_template", structure_data)

    # Reset all module extensions
    for module, default in DEFAULT_MODULE_EXTENSIONS.items():
        doc_id = f"extension_{module}"
        ext_data = {
            "id": doc_id,
            "module": module,
            "name": default["name"],
            "description": default["description"],
            "content": default["content"],
            "parameters": default["parameters"],
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await set_document(COLLECTION, doc_id, ext_data)

    logger.info(f"All prompts reset to defaults by {current_user['id']}")
    return {"message": "All prompts reset to default values"}
