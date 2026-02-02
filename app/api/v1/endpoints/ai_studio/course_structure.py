"""
AI Studio - Course Structure Parser
Extract course hierarchy from PDF documents using AI
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import logging
import io

from google import genai
from google.genai import types

from app.core.security import get_current_user, require_author
from app.config import settings
from app.core.firebase_admin import get_document

logger = logging.getLogger(__name__)

router = APIRouter()


# ============== SCHEMAS ==============

class ParsedLesson(BaseModel):
    name: str
    order: int
    content_type: str = "video"
    metadata: Optional[dict] = None


class ParsedSection(BaseModel):
    name: str
    order: int
    description: Optional[str] = None
    lessons: List[ParsedLesson] = []
    metadata: Optional[dict] = None


class ParsedModule(BaseModel):
    name: str
    order: int
    description: Optional[str] = None
    total_classes: Optional[int] = None
    sections: List[ParsedSection] = []
    metadata: Optional[dict] = None


class ParsedLevel(BaseModel):
    name: str
    order: int
    description: Optional[str] = None
    modules: List[ParsedModule] = []
    metadata: Optional[dict] = None


class ParsedCourseStructure(BaseModel):
    course_name: str
    course_description: Optional[str] = None
    levels: List[ParsedLevel] = []


# ============== GEMINI CLIENT ==============

_gemini_client = None


async def get_gemini_client():
    """Get or create Gemini client"""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = settings.gemini_api_key

    # Try Firestore if not in env
    if not api_key:
        try:
            app_settings = await get_document("settings", "app")
            if app_settings:
                api_key = app_settings.get("gemini_api_key")
        except Exception as e:
            logger.warning(f"Could not fetch Gemini API key from Firestore: {e}")

    if not api_key:
        raise ValueError("Gemini API key not configured")

    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ============== ENDPOINTS ==============

@router.post("/parse-course-structure", response_model=ParsedCourseStructure)
async def parse_course_structure(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_author),
):
    """
    Parse a PDF document to extract course structure using AI.

    The PDF should contain the course hierarchy (levels, modules, sections, lessons).
    The AI will analyze the document and extract a structured hierarchy.

    Author or Admin only.
    """
    # Validate file type
    if not file.content_type or "pdf" not in file.content_type.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    # Read file content
    try:
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 10MB limit"
            )
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error reading file"
        )

    # Get Gemini client
    try:
        client = await get_gemini_client()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    # Create the prompt for structure extraction
    extraction_prompt = """Eres un asistente que extrae estructuras de cursos educativos de documentos PDF.

TAREA: Analiza el PDF y extrae la estructura del curso en formato JSON.

ESTRUCTURA ESPERADA DEL JSON:
{
  "course_name": "Nombre del curso detectado",
  "course_description": "Descripción breve",
  "levels": [
    {
      "name": "Nivel Básico",
      "order": 1,
      "description": "Duración: X meses",
      "modules": [
        {
          "name": "Módulo 1",
          "order": 1,
          "total_classes": 16,
          "sections": [
            {
              "name": "Contenido del módulo",
              "order": 1,
              "lessons": [
                {"name": "Clase 1: Tema", "order": 1, "content_type": "video"},
                {"name": "Clase 2: Tema", "order": 2, "content_type": "video"}
              ]
            }
          ]
        }
      ]
    }
  ]
}

REGLAS:
1. NIVELES = Básico, Intermedio, Avanzado (o Nivel 1, 2, 3)
2. MÓDULOS = Unidades o bloques dentro de cada nivel
3. SECCIONES = Agrupa las lecciones por tema. Si no hay agrupación clara, crea una sección "Contenido" por módulo
4. LECCIONES = Cada tema individual (ej: "Saludos formales", "Números del 1 al 10")
5. Cada lección debe tener: name, order (número secuencial), content_type: "video"
6. Si el PDF menciona "16 clases" en un módulo, crea 16 lecciones con los temas listados

RESPONDE SOLO CON EL JSON, sin texto adicional, sin markdown, sin explicaciones."""

    # Call Gemini with PDF
    try:
        logger.info(f"Parsing PDF structure with Gemini: {file.filename}")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=file_content,
                            mime_type="application/pdf"
                        ),
                        types.Part(text=extraction_prompt)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for more consistent structure
                max_output_tokens=16384,
            )
        )

        result_text = response.text.strip()
        logger.info(f"Gemini raw response length: {len(result_text)} chars")
        logger.info(f"Gemini response preview: {result_text[:300]}...")

        # Clean up response - remove markdown code blocks
        import re
        import json

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result_text)
        if json_match:
            result_text = json_match.group(1)
            logger.info("Extracted JSON from markdown code block")
        else:
            # Try to find JSON object directly
            json_start = result_text.find('{')
            json_end = result_text.rfind('}')
            if json_start != -1 and json_end != -1:
                result_text = result_text[json_start:json_end + 1]
                logger.info("Extracted JSON by finding braces")

        result_text = result_text.strip()
        logger.info(f"Cleaned JSON preview: {result_text[:200]}...")

        # Parse JSON
        try:
            structure_data = json.loads(result_text)
            logger.info(f"Successfully parsed JSON with keys: {list(structure_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Full response text: {result_text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI returned invalid JSON structure. Error: {str(e)[:100]}"
            )

        # Validate and convert to response model
        parsed_structure = ParsedCourseStructure(
            course_name=structure_data.get("course_name", "Curso sin nombre"),
            course_description=structure_data.get("course_description"),
            levels=[
                ParsedLevel(
                    name=level.get("name", f"Nivel {i+1}"),
                    order=level.get("order", i+1),
                    description=level.get("description"),
                    metadata=level.get("metadata"),
                    modules=[
                        ParsedModule(
                            name=module.get("name", f"Módulo {j+1}"),
                            order=module.get("order", j+1),
                            description=module.get("description"),
                            total_classes=module.get("total_classes"),
                            metadata=module.get("metadata"),
                            sections=[
                                ParsedSection(
                                    name=section.get("name", f"Sección {k+1}"),
                                    order=section.get("order", k+1),
                                    description=section.get("description"),
                                    metadata=section.get("metadata"),
                                    lessons=[
                                        ParsedLesson(
                                            name=lesson.get("name", f"Lección {l+1}"),
                                            order=lesson.get("order", l+1),
                                            content_type=lesson.get("content_type", "video"),
                                            metadata=lesson.get("metadata"),
                                        )
                                        for l, lesson in enumerate(section.get("lessons", []))
                                    ]
                                )
                                for k, section in enumerate(module.get("sections", []))
                            ]
                        )
                        for j, module in enumerate(level.get("modules", []))
                    ]
                )
                for i, level in enumerate(structure_data.get("levels", []))
            ]
        )

        # Log summary
        total_modules = sum(len(l.modules) for l in parsed_structure.levels)
        total_sections = sum(len(m.sections) for l in parsed_structure.levels for m in l.modules)
        total_lessons = sum(len(s.lessons) for l in parsed_structure.levels for m in l.modules for s in m.sections)

        logger.info(
            f"Successfully parsed course structure: {len(parsed_structure.levels)} levels, "
            f"{total_modules} modules, {total_sections} sections, {total_lessons} lessons"
        )

        return parsed_structure

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing PDF with Gemini: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )
