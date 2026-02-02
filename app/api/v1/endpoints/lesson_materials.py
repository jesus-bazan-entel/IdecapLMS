"""
Lesson Materials API Endpoints
Upload, manage, and retrieve lesson materials (files, links, etc.)
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field

from app.core.firebase_admin import get_firestore
from app.core.security import get_current_user, require_author
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lessons", tags=["Lesson Materials"])


# ============== REQUEST/RESPONSE MODELS ==============

class MaterialCreateRequest(BaseModel):
    """Request model for creating a link-based material"""
    title: str
    url: str
    description: Optional[str] = None
    type: str = "link"


class MaterialResponse(BaseModel):
    """Response model for a material"""
    id: str
    name: str
    type: str
    url: str
    description: Optional[str] = None
    file_size: Optional[int] = Field(None, alias="fileSize")
    mime_type: Optional[str] = Field(None, alias="mimeType")
    uploaded_at: Optional[datetime] = Field(None, alias="uploadedAt")
    lesson_id: Optional[str] = Field(None, alias="lessonId")

    class Config:
        populate_by_name = True


class MaterialsListResponse(BaseModel):
    """Response model for list of materials"""
    materials: List[MaterialResponse]
    total: int


# ============== HELPER FUNCTIONS ==============

def get_file_type(filename: str, content_type: str) -> str:
    """Determine file type from filename and content type"""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    # Check by extension first
    if ext in ["pdf"]:
        return "pdf"
    elif ext in ["pptx", "ppt", "odp"]:
        return "presentation"
    elif ext in ["mp4", "webm", "mov", "avi"]:
        return "video"
    elif ext in ["mp3", "wav", "ogg", "m4a", "aac"]:
        return "audio"
    elif ext in ["docx", "doc", "txt", "rtf"]:
        return "document"
    elif ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        return "image"

    # Fallback to content type
    if content_type:
        if "pdf" in content_type:
            return "pdf"
        elif "presentation" in content_type or "powerpoint" in content_type:
            return "presentation"
        elif "video" in content_type:
            return "video"
        elif "audio" in content_type:
            return "audio"
        elif "image" in content_type:
            return "image"

    return "document"


async def get_lesson_path(lesson_id: str) -> Optional[dict]:
    """
    Find the full path to a lesson in the hierarchy.
    Returns dict with courseId, levelId, moduleId, sectionId if found.
    """
    db = get_firestore()

    # Search through all courses for this lesson
    courses_ref = db.collection("courses")
    courses = courses_ref.stream()

    for course in courses:
        course_id = course.id

        # Search levels
        levels_ref = courses_ref.document(course_id).collection("levels")
        levels = levels_ref.stream()

        for level in levels:
            level_id = level.id

            # Search modules
            modules_ref = levels_ref.document(level_id).collection("modules")
            modules = modules_ref.stream()

            for module in modules:
                module_id = module.id

                # Search sections
                sections_ref = modules_ref.document(module_id).collection("sections")
                sections = sections_ref.stream()

                for section in sections:
                    section_id = section.id

                    # Check if lesson exists in this section
                    lesson_ref = sections_ref.document(section_id).collection("lessons").document(lesson_id)
                    lesson_doc = lesson_ref.get()

                    if lesson_doc.exists:
                        return {
                            "courseId": course_id,
                            "levelId": level_id,
                            "moduleId": module_id,
                            "sectionId": section_id,
                            "lessonRef": lesson_ref,
                            "lessonData": lesson_doc.to_dict()
                        }

    return None


# ============== ENDPOINTS ==============

@router.get("/{lesson_id}/materials", response_model=MaterialsListResponse)
async def get_lesson_materials(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get all materials for a specific lesson.
    Includes both uploaded files and linked materials.
    """
    try:
        lesson_path = await get_lesson_path(lesson_id)

        if not lesson_path:
            raise HTTPException(status_code=404, detail="Lección no encontrada")

        lesson_data = lesson_path["lessonData"]
        materials = lesson_data.get("materials", [])

        # Transform materials to response format
        material_responses = []
        for mat in materials:
            material_responses.append(MaterialResponse(
                id=mat.get("id", ""),
                name=mat.get("name", ""),
                type=mat.get("type", "document"),
                url=mat.get("url", ""),
                description=mat.get("description"),
                file_size=mat.get("fileSize"),
                mime_type=mat.get("mimeType"),
                uploaded_at=mat.get("uploadedAt"),
                lesson_id=lesson_id,
            ))

        return MaterialsListResponse(
            materials=material_responses,
            total=len(material_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lesson materials: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener materiales")


@router.post("/{lesson_id}/materials", response_model=MaterialResponse)
async def add_link_material(
    lesson_id: str,
    request: MaterialCreateRequest,
    current_user: dict = Depends(require_author),
):
    """
    Add a link-based material to a lesson.
    Use this for external URLs, YouTube links, etc.
    """
    try:
        lesson_path = await get_lesson_path(lesson_id)

        if not lesson_path:
            raise HTTPException(status_code=404, detail="Lección no encontrada")

        # Create material object
        material_id = str(uuid.uuid4())
        now = datetime.utcnow()

        material_data = {
            "id": material_id,
            "name": request.title,
            "type": request.type,
            "url": request.url,
            "description": request.description,
            "uploadedAt": now,
        }

        # Get current materials
        lesson_data = lesson_path["lessonData"]
        materials = lesson_data.get("materials", [])
        materials.append(material_data)

        # Update lesson
        lesson_path["lessonRef"].update({
            "materials": materials,
            "updatedAt": now,
        })

        return MaterialResponse(
            id=material_id,
            name=request.title,
            type=request.type,
            url=request.url,
            description=request.description,
            uploaded_at=now,
            lesson_id=lesson_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding link material: {e}")
        raise HTTPException(status_code=500, detail="Error al agregar material")


@router.post("/{lesson_id}/materials/upload", response_model=MaterialResponse)
async def upload_material(
    lesson_id: str,
    file: UploadFile = File(...),
    title: str = Form(None),
    description: str = Form(None),
    current_user: dict = Depends(require_author),
):
    """
    Upload a file as lesson material.
    Supports PDF, PPT, videos, audio, documents, and images.
    Max file size: 100MB
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size (100MB max)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Máximo: 100MB"
            )

        # Find lesson
        lesson_path = await get_lesson_path(lesson_id)

        if not lesson_path:
            raise HTTPException(status_code=404, detail="Lección no encontrada")

        # Determine file type
        file_type = get_file_type(file.filename, file.content_type or "")

        # Generate storage path
        storage_service = get_storage_service()
        storage_path = storage_service.generate_unique_filename(
            file.filename,
            prefix=f"lesson_materials/{lesson_id}/"
        )

        # Upload to Firebase Storage
        public_url = await storage_service.upload_file(
            file_data=file_content,
            destination_path=storage_path,
            content_type=file.content_type or "application/octet-stream",
        )

        # Create material object
        material_id = str(uuid.uuid4())
        now = datetime.utcnow()

        material_data = {
            "id": material_id,
            "name": title or file.filename,
            "type": file_type,
            "url": public_url,
            "description": description,
            "fileSize": file_size,
            "mimeType": file.content_type,
            "storagePath": storage_path,
            "uploadedAt": now,
        }

        # Get current materials and append new one
        lesson_data = lesson_path["lessonData"]
        materials = lesson_data.get("materials", [])
        materials.append(material_data)

        # Update lesson
        lesson_path["lessonRef"].update({
            "materials": materials,
            "updatedAt": now,
        })

        logger.info(f"Material uploaded: {material_id} for lesson {lesson_id}")

        return MaterialResponse(
            id=material_id,
            name=title or file.filename,
            type=file_type,
            url=public_url,
            description=description,
            file_size=file_size,
            mime_type=file.content_type,
            uploaded_at=now,
            lesson_id=lesson_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading material: {e}")
        raise HTTPException(status_code=500, detail="Error al subir material")


@router.delete("/materials/{material_id}")
async def delete_material(
    material_id: str,
    lesson_id: str = None,
    current_user: dict = Depends(require_author),
):
    """
    Delete a material from a lesson.
    Also deletes the file from storage if it was uploaded.
    """
    try:
        db = get_firestore()
        storage_service = get_storage_service()

        # If lesson_id is not provided, search all lessons for this material
        if not lesson_id:
            # This is inefficient, but necessary if lesson_id is not provided
            # In production, you'd want to require lesson_id or store material metadata separately
            courses_ref = db.collection("courses")
            courses = courses_ref.stream()

            for course in courses:
                lesson_path = await get_lesson_path_with_material(course.id, material_id, db)
                if lesson_path:
                    break
            else:
                raise HTTPException(status_code=404, detail="Material no encontrado")
        else:
            lesson_path = await get_lesson_path(lesson_id)
            if not lesson_path:
                raise HTTPException(status_code=404, detail="Lección no encontrada")

        # Find and remove the material
        lesson_data = lesson_path["lessonData"]
        materials = lesson_data.get("materials", [])

        material_to_delete = None
        new_materials = []

        for mat in materials:
            if mat.get("id") == material_id:
                material_to_delete = mat
            else:
                new_materials.append(mat)

        if not material_to_delete:
            raise HTTPException(status_code=404, detail="Material no encontrado")

        # Delete from storage if it has a storage path
        storage_path = material_to_delete.get("storagePath")
        if storage_path:
            try:
                await storage_service.delete_file(storage_path)
            except Exception as e:
                logger.warning(f"Could not delete file from storage: {e}")

        # Update lesson
        lesson_path["lessonRef"].update({
            "materials": new_materials,
            "updatedAt": datetime.utcnow(),
        })

        logger.info(f"Material deleted: {material_id}")

        return {"message": "Material eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting material: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar material")


async def get_lesson_path_with_material(course_id: str, material_id: str, db) -> Optional[dict]:
    """Helper to find a lesson containing a specific material"""
    courses_ref = db.collection("courses")

    levels_ref = courses_ref.document(course_id).collection("levels")
    levels = levels_ref.stream()

    for level in levels:
        modules_ref = levels_ref.document(level.id).collection("modules")
        modules = modules_ref.stream()

        for module in modules:
            sections_ref = modules_ref.document(module.id).collection("sections")
            sections = sections_ref.stream()

            for section in sections:
                lessons_ref = sections_ref.document(section.id).collection("lessons")
                lessons = lessons_ref.stream()

                for lesson in lessons:
                    lesson_data = lesson.to_dict()
                    materials = lesson_data.get("materials", [])

                    for mat in materials:
                        if mat.get("id") == material_id:
                            return {
                                "courseId": course_id,
                                "levelId": level.id,
                                "moduleId": module.id,
                                "sectionId": section.id,
                                "lessonRef": lessons_ref.document(lesson.id),
                                "lessonData": lesson_data
                            }

    return None
