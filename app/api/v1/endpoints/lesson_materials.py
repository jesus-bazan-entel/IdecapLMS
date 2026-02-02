"""
Lesson Materials API Endpoints
Upload, manage, and retrieve lesson materials (files, links, etc.)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from pydantic import BaseModel, Field

from app.core.firebase_admin import get_firestore
from app.core.security import get_current_user, require_author
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[str] = None
    lesson_id: Optional[str] = None


class MaterialsListResponse(BaseModel):
    """Response model for list of materials"""
    materials: List[MaterialResponse]
    total: int


# ============== HELPER FUNCTIONS ==============

def get_file_type(filename: str, content_type: str) -> str:
    """Determine file type from filename and content type"""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

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


def find_lesson_in_hierarchy(db, lesson_id: str):
    """Find a lesson by ID in the course hierarchy"""
    courses_ref = db.collection("courses")

    for course in courses_ref.stream():
        levels_ref = courses_ref.document(course.id).collection("levels")

        for level in levels_ref.stream():
            modules_ref = levels_ref.document(level.id).collection("modules")

            for module in modules_ref.stream():
                sections_ref = modules_ref.document(module.id).collection("sections")

                for section in sections_ref.stream():
                    lesson_ref = sections_ref.document(section.id).collection("lessons").document(lesson_id)
                    lesson_doc = lesson_ref.get()

                    if lesson_doc.exists:
                        return {
                            "ref": lesson_ref,
                            "data": lesson_doc.to_dict(),
                            "course_id": course.id,
                            "level_id": level.id,
                            "module_id": module.id,
                            "section_id": section.id,
                        }

    return None


# ============== ENDPOINTS ==============

@router.get("/lessons/{lesson_id}/materials", response_model=MaterialsListResponse)
def get_lesson_materials(
    lesson_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get all materials for a specific lesson."""
    try:
        db = get_firestore()
        lesson_info = find_lesson_in_hierarchy(db, lesson_id)

        if not lesson_info:
            raise HTTPException(status_code=404, detail="Lección no encontrada")

        materials_data = lesson_info["data"].get("materials", [])

        materials = []
        for mat in materials_data:
            uploaded_at = mat.get("uploadedAt")
            if uploaded_at and hasattr(uploaded_at, 'isoformat'):
                uploaded_at = uploaded_at.isoformat()
            elif uploaded_at and hasattr(uploaded_at, 'seconds'):
                uploaded_at = datetime.fromtimestamp(uploaded_at.seconds, tz=timezone.utc).isoformat()

            materials.append(MaterialResponse(
                id=mat.get("id", ""),
                name=mat.get("name", ""),
                type=mat.get("type", "document"),
                url=mat.get("url", ""),
                description=mat.get("description"),
                file_size=mat.get("fileSize"),
                mime_type=mat.get("mimeType"),
                uploaded_at=uploaded_at,
                lesson_id=lesson_id,
            ))

        return MaterialsListResponse(materials=materials, total=len(materials))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lesson materials: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener materiales")


@router.post("/lessons/{lesson_id}/materials", response_model=MaterialResponse)
def add_link_material(
    lesson_id: str,
    request: MaterialCreateRequest,
    current_user: dict = Depends(require_author),
):
    """Add a link-based material to a lesson."""
    try:
        db = get_firestore()
        lesson_info = find_lesson_in_hierarchy(db, lesson_id)

        if not lesson_info:
            raise HTTPException(status_code=404, detail="Lección no encontrada")

        material_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        material_data = {
            "id": material_id,
            "name": request.title,
            "type": request.type,
            "url": request.url,
            "description": request.description,
            "uploadedAt": now,
        }

        materials = lesson_info["data"].get("materials", [])
        materials.append(material_data)

        lesson_info["ref"].update({
            "materials": materials,
            "updatedAt": now,
        })

        return MaterialResponse(
            id=material_id,
            name=request.title,
            type=request.type,
            url=request.url,
            description=request.description,
            uploaded_at=now.isoformat(),
            lesson_id=lesson_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding link material: {e}")
        raise HTTPException(status_code=500, detail="Error al agregar material")


@router.post("/lessons/{lesson_id}/materials/upload", response_model=MaterialResponse)
async def upload_material(
    lesson_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(require_author),
):
    """Upload a file as lesson material. Max file size: 100MB"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

        file_content = await file.read()
        file_size = len(file_content)

        max_size = 100 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(status_code=400, detail="Archivo demasiado grande. Máximo: 100MB")

        db = get_firestore()
        lesson_info = find_lesson_in_hierarchy(db, lesson_id)

        if not lesson_info:
            raise HTTPException(status_code=404, detail="Lección no encontrada")

        file_type = get_file_type(file.filename, file.content_type or "")

        storage_service = get_storage_service()
        storage_path = storage_service.generate_unique_filename(
            file.filename,
            prefix=f"lesson_materials/{lesson_id}/"
        )

        public_url = await storage_service.upload_file(
            file_data=file_content,
            destination_path=storage_path,
            content_type=file.content_type or "application/octet-stream",
        )

        material_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

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

        materials = lesson_info["data"].get("materials", [])
        materials.append(material_data)

        lesson_info["ref"].update({
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
            uploaded_at=now.isoformat(),
            lesson_id=lesson_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading material: {e}")
        raise HTTPException(status_code=500, detail="Error al subir material")


@router.delete("/lessons/materials/{material_id}")
def delete_material(
    material_id: str,
    lesson_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_author),
):
    """Delete a material from a lesson."""
    try:
        db = get_firestore()
        storage_service = get_storage_service()
        lesson_info = None

        if lesson_id:
            lesson_info = find_lesson_in_hierarchy(db, lesson_id)
            if not lesson_info:
                raise HTTPException(status_code=404, detail="Lección no encontrada")
        else:
            # Search all courses for this material
            courses_ref = db.collection("courses")
            for course in courses_ref.stream():
                levels_ref = courses_ref.document(course.id).collection("levels")
                for level in levels_ref.stream():
                    modules_ref = levels_ref.document(level.id).collection("modules")
                    for module in modules_ref.stream():
                        sections_ref = modules_ref.document(module.id).collection("sections")
                        for section in sections_ref.stream():
                            lessons_ref = sections_ref.document(section.id).collection("lessons")
                            for lesson in lessons_ref.stream():
                                lesson_data = lesson.to_dict()
                                for mat in lesson_data.get("materials", []):
                                    if mat.get("id") == material_id:
                                        lesson_info = {
                                            "ref": lessons_ref.document(lesson.id),
                                            "data": lesson_data,
                                        }
                                        break
                                if lesson_info:
                                    break
                            if lesson_info:
                                break
                        if lesson_info:
                            break
                    if lesson_info:
                        break
                if lesson_info:
                    break

        if not lesson_info:
            raise HTTPException(status_code=404, detail="Material no encontrado")

        materials = lesson_info["data"].get("materials", [])
        material_to_delete = None
        new_materials = []

        for mat in materials:
            if mat.get("id") == material_id:
                material_to_delete = mat
            else:
                new_materials.append(mat)

        if not material_to_delete:
            raise HTTPException(status_code=404, detail="Material no encontrado")

        storage_path = material_to_delete.get("storagePath")
        if storage_path:
            try:
                import asyncio
                asyncio.get_event_loop().run_until_complete(
                    storage_service.delete_file(storage_path)
                )
            except Exception as e:
                logger.warning(f"Could not delete file from storage: {e}")

        lesson_info["ref"].update({
            "materials": new_materials,
            "updatedAt": datetime.now(timezone.utc),
        })

        logger.info(f"Material deleted: {material_id}")

        return {"message": "Material eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting material: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar material")
