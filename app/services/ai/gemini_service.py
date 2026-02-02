"""
Gemini AI Service
Content generation using Google Gemini (new google-genai SDK)
Supports both static prompts (backward compatible) and configurable prompts (unified prompt service)
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from google import genai
from google.genai import types

from app.config import settings
from app.core.firebase_admin import get_document
from app.services.ai.knowledge import (
    get_master_prompt,
    get_audio_prompt,
    get_presentation_prompt,
    get_mindmap_prompt,
    get_podcast_prompt,
    get_video_prompt,
    VOICES,
)
from app.models.domain.ai.prompt_config import AIModule, GenerationContext

logger = logging.getLogger(__name__)

# Master prompt for Portuguese language learning content (static fallback)
PORTUGUESE_LEARNING_CONTEXT = get_master_prompt()


class GeminiService:
    """Service for generating content with Gemini"""

    def __init__(self):
        self._client = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Initialize Gemini with API key from settings or Firestore"""
        if self._initialized:
            return

        api_key = settings.gemini_api_key

        # Try to get API key from Firestore settings if not in env
        if not api_key:
            try:
                app_settings = await get_document("settings", "app")
                if app_settings:
                    api_key = app_settings.get("gemini_api_key")
            except Exception as e:
                logger.warning(f"Could not fetch Gemini API key from Firestore: {e}")

        if not api_key:
            raise ValueError("Gemini API key not configured")

        # Initialize the new google-genai client
        self._client = genai.Client(api_key=api_key)
        self._initialized = True

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text content"""
        await self._ensure_initialized()

        try:
            # Build the full prompt with system instruction
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"

            # Use the new google-genai SDK
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text

        except Exception as e:
            logger.error(f"Gemini text generation error: {e}")
            raise

    async def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict:
        """Generate structured JSON content"""
        await self._ensure_initialized()

        # Add JSON formatting instructions
        json_instruction = """
IMPORTANTE: Responde ÚNICAMENTE con JSON válido.
- No uses markdown (no ```json)
- No agregues explicaciones
- El JSON debe seguir exactamente el esquema proporcionado.
"""
        if schema:
            json_instruction += f"\nEsquema esperado: {json.dumps(schema, indent=2)}"

        # Build complete prompt with all instructions
        full_prompt = ""
        if system_instruction:
            full_prompt += f"{system_instruction}\n\n"
        full_prompt += f"{json_instruction}\n\n{prompt}"

        try:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                )
            )
            text = response.text.strip()

            # Clean up response if wrapped in markdown code blocks
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            return json.loads(text.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Gemini JSON generation error: {e}")
            raise

    async def generate_lesson_content(
        self,
        topic: str,
        lesson_type: str = "article",
        language: str = "es",
        difficulty: str = "intermediate",
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate lesson content for a specific topic"""
        system_instruction = f"""
Eres un experto educador creando contenido para un curso de idiomas.
Idioma del contenido: {language}
Nivel de dificultad: {difficulty}

Genera contenido educativo estructurado y atractivo.
"""

        prompt = f"""
Genera contenido para una lección sobre: {topic}

Tipo de lección: {lesson_type}

{f"Contexto adicional: {additional_context}" if additional_context else ""}

El contenido debe incluir:
1. Título atractivo
2. Objetivos de aprendizaje (3-5 puntos)
3. Contenido principal (en HTML para artículos)
4. Puntos clave (resumen)
5. Preguntas de práctica (3-5 preguntas de opción múltiple)

Responde en JSON con esta estructura:
{{
    "title": "Título de la lección",
    "objectives": ["Objetivo 1", "Objetivo 2", ...],
    "content": "<div>Contenido HTML...</div>",
    "key_points": ["Punto 1", "Punto 2", ...],
    "questions": [
        {{
            "question": "¿Pregunta?",
            "options": ["Opción A", "Opción B", "Opción C", "Opción D"],
            "correct_index": 0,
            "explanation": "Explicación de la respuesta correcta"
        }}
    ]
}}
"""

        return await self.generate_json(prompt, system_instruction=system_instruction)

    async def generate_presentation_slides(
        self,
        topic: str,
        num_slides: int = 10,
        language: str = "es",
        additional_context: Optional[str] = None,
        use_knowledge_base: bool = True,
    ) -> List[Dict]:
        """Generate presentation slides for a topic"""
        knowledge_context = ""
        if use_knowledge_base and language in ["pt", "es"]:
            knowledge_context = f"""
BASE DE CONOCIMIENTO EDUCATIVO (Portugués Brasileño para Hispanohablantes):
{PORTUGUESE_LEARNING_CONTEXT}

---
"""
        system_instruction = f"""
Eres un experto en crear presentaciones educativas profesionales.
Idioma: {language}
Crea slides claras, concisas y visualmente atractivas.

{knowledge_context}

IMPORTANTE para contenido de portugués:
- Incluir falsos amigos relevantes al tema
- Indicar pronunciación de palabras difíciles
- Usar ejemplos prácticos para estudiantes peruanos
"""

        prompt = f"""
Genera {num_slides} slides para una presentación sobre: {topic}

{f"Contexto adicional: {additional_context}" if additional_context else ""}

Cada slide debe tener:
- Título conciso
- 3-5 puntos clave (bullet points)
- Notas del presentador (opcional)
- Tipo de slide (title, content, summary, quote)

Responde en JSON con esta estructura:
{{
    "title": "Título de la presentación",
    "slides": [
        {{
            "order": 1,
            "title": "Título del slide",
            "type": "title",
            "bullet_points": ["Punto 1", "Punto 2"],
            "notes": "Notas para el presentador"
        }}
    ]
}}
"""

        result = await self.generate_json(prompt, system_instruction=system_instruction)
        return result.get("slides", [])

    async def generate_mindmap(
        self,
        topic: str,
        depth: int = 3,
        language: str = "es",
        additional_context: Optional[str] = None,
        use_knowledge_base: bool = True,
    ) -> Dict:
        """Generate a mind map structure for a topic"""
        knowledge_context = ""
        if use_knowledge_base and language in ["pt", "es"]:
            knowledge_context = f"""
BASE DE CONOCIMIENTO EDUCATIVO (Portugués Brasileño para Hispanohablantes):
{PORTUGUESE_LEARNING_CONTEXT}

---
"""
        system_instruction = f"""
Eres un experto en organización del conocimiento y mapas mentales.
Idioma: {language}
Crea estructuras jerárquicas claras y lógicas.

{knowledge_context}

Para contenido de portugués brasileño:
- Organiza el contenido de forma progresiva
- Incluye nodos con falsos amigos cuando sea relevante
- Añade ejemplos de pronunciación en los nodos finales
"""

        prompt = f"""
Genera un mapa mental sobre: {topic}

Profundidad máxima: {depth} niveles
{f"Contexto adicional: {additional_context}" if additional_context else ""}

El mapa debe tener:
- Un nodo central con el tema principal
- Ramas principales (nivel 1)
- Sub-ramas según la profundidad

Responde en JSON con esta estructura recursiva:
{{
    "id": "root",
    "label": "Tema central",
    "level": 0,
    "children": [
        {{
            "id": "node1",
            "label": "Subtema 1",
            "level": 1,
            "children": [...]
        }}
    ]
}}
"""

        return await self.generate_json(prompt, system_instruction=system_instruction)

    async def generate_podcast_script(
        self,
        topic: str,
        style: str = "conversational",
        duration_minutes: int = 10,
        speakers: List[Dict] = None,
        language: str = "es",
        additional_context: Optional[str] = None,
        use_knowledge_base: bool = True,
    ) -> List[Dict]:
        """Generate a podcast script with multiple speakers for Portuguese language learning"""
        if speakers is None:
            speakers = [
                {"id": "host_male", "name": "Carlos", "role": "host"},
                {"id": "host_female", "name": "Ana", "role": "expert"}
            ]

        # Build speaker descriptions
        speakers_info = []
        for s in speakers:
            gender = "masculina" if "male" in s.get("id", "") else "femenina"
            speakers_info.append(f"{s['name']} (voz {gender}, rol: {s['role']})")
        speakers_desc = " y ".join(speakers_info)

        # Use knowledge base context if enabled
        knowledge_context = ""
        if use_knowledge_base:
            knowledge_context = f"""
BASE DE CONOCIMIENTO EDUCATIVO:
{PORTUGUESE_LEARNING_CONTEXT}

---
"""

        system_instruction = f"""
Eres un guionista experto en podcasts educativos para enseñanza de idiomas.
Tu especialidad es crear contenido para hispanohablantes que aprenden PORTUGUÉS BRASILEÑO.

{knowledge_context}

CONTEXTO EDUCATIVO:
- Audiencia: Estudiantes peruanos hispanohablantes aprendiendo portugués brasileño
- Instituto: IDECAP (Instituto de Desarrollo de Capacidades)
- Objetivo: Enseñar portugués de forma amena y práctica
- El contenido debe estar EN ESPAÑOL pero incluir palabras, frases y ejemplos EN PORTUGUÉS
- Siempre que menciones una palabra o frase en portugués, incluye su pronunciación aproximada y significado
- IMPORTANTE: Incluir falsos amigos (palabras que parecen similares pero tienen significados diferentes)

HABLANTES: {speakers_desc}

ESTILO DE CONVERSACIÓN:
- Diálogo NATURAL y fluido, como dos amigos conversando
- Usa muletillas naturales: "mira", "fíjate", "¿sabes qué?", "exacto", "claro"
- Incluye reacciones: risas, sorpresa, entusiasmo
- Alterna turnos de forma dinámica (no monólogos largos)
- Cada intervención debe ser de 2-4 oraciones máximo
- Los hablantes deben tener personalidades distintas

FORMATO DEL CONTENIDO:
- Introducir palabras en portugués con su pronunciación: "obrigado" (se pronuncia "obrigádu")
- Comparar con español cuando sea útil: "En portugués decimos 'bom dia', similar a 'buen día'"
- Incluir tips de pronunciación y falsos amigos de la tabla de referencia
- Usar ejemplos prácticos y situaciones cotidianas relevantes para peruanos
"""

        prompt = f"""
Genera un guión de podcast educativo sobre: {topic}

PARÁMETROS:
- Duración: {duration_minutes} minutos (aproximadamente {duration_minutes * 130} palabras total)
- Estilo: {style}
- Idioma principal: español con ejemplos en portugués
{f"- Contexto adicional: {additional_context}" if additional_context else ""}

HABLANTES (usar exactamente estos IDs):
{json.dumps(speakers, indent=2)}

ESTRUCTURA DEL PODCAST:
1. INTRO (10%): Saludo animado, presentación del tema de hoy
2. DESARROLLO (75%): Contenido principal con ejemplos prácticos en portugués
3. CIERRE (15%): Resumen de lo aprendido, despedida amigable

REGLAS IMPORTANTES:
- Alternar constantemente entre los hablantes (máximo 3-4 oraciones por turno)
- Incluir al menos 5-8 palabras/frases en portugués con pronunciación
- Hacer el diálogo dinámico con preguntas entre los hablantes
- Incluir algún dato curioso o anécdota sobre la cultura brasileña/portuguesa

Responde SOLO con JSON válido:
{{
    "title": "Título atractivo del episodio",
    "segments": [
        {{
            "order": 1,
            "speaker_id": "host_male",
            "speaker_name": "Carlos",
            "text": "Texto natural del diálogo...",
            "duration_estimate": 15
        }},
        {{
            "order": 2,
            "speaker_id": "host_female",
            "speaker_name": "Ana",
            "text": "Respuesta natural...",
            "duration_estimate": 12
        }}
    ]
}}
"""

        result = await self.generate_json(prompt, system_instruction=system_instruction)
        return result.get("segments", [])

    async def generate_quiz_questions(
        self,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "intermediate",
        language: str = "es",
    ) -> List[Dict]:
        """Generate quiz questions for a topic"""
        system_instruction = f"""
Eres un experto en evaluación educativa.
Idioma: {language}
Dificultad: {difficulty}

Crea preguntas que evalúen comprensión real, no memorización.
"""

        prompt = f"""
Genera {num_questions} preguntas de opción múltiple sobre: {topic}

Cada pregunta debe:
- Ser clara y sin ambigüedades
- Tener 4 opciones de respuesta
- Una sola respuesta correcta
- Una explicación de por qué esa es la respuesta correcta

Responde en JSON:
{{
    "questions": [
        {{
            "id": "q1",
            "question_text": "¿Pregunta?",
            "options": [
                {{"text": "Opción A", "is_correct": true}},
                {{"text": "Opción B", "is_correct": false}},
                {{"text": "Opción C", "is_correct": false}},
                {{"text": "Opción D", "is_correct": false}}
            ],
            "explanation": "Explicación de la respuesta correcta"
        }}
    ]
}}
"""

        result = await self.generate_json(prompt, system_instruction=system_instruction)
        return result.get("questions", [])

    async def generate_video_prompt(
        self,
        topic: str,
        style: str = "explainer",
        duration_seconds: int = 60,
        language: str = "es",
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate a detailed video generation prompt for Veo 3"""
        system_instruction = f"""
Eres un director de video educativo experto.
Idioma: {language}
Crea descripciones detalladas para generación de video con IA.
"""

        prompt = f"""
Crea una descripción detallada para generar un video sobre: {topic}

Estilo: {style}
Duración: {duration_seconds} segundos
{f"Contexto adicional: {additional_context}" if additional_context else ""}

La descripción debe incluir:
- Prompt visual detallado para el generador de video
- Guión de narración (si aplica)
- Descripción de escenas principales
- Notas de estilo y tono

Responde en JSON:
{{
    "visual_prompt": "Descripción visual detallada para el generador...",
    "narration_script": "Texto de narración...",
    "scenes": [
        {{
            "order": 1,
            "description": "Descripción de la escena",
            "duration_seconds": 10
        }}
    ],
    "style_notes": "Notas sobre estilo visual y tono"
}}
"""

        return await self.generate_json(prompt, system_instruction=system_instruction)


    # ============== UNIFIED PROMPT METHODS ==============
    # These methods use the configurable 3-layer prompt architecture

    async def generate_with_unified_prompt(
        self,
        module: AIModule,
        context: GenerationContext,
        output_format: str = "json",
        schema: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Any:
        """
        Generate content using the unified 3-layer prompt system.

        Args:
            module: AI module (audio, presentation, mindmap, etc.)
            context: Generation context with topic, level, etc.
            output_format: "json" or "text"
            schema: Optional JSON schema for structured output
            temperature: Generation temperature
            max_tokens: Maximum output tokens

        Returns:
            Generated content (dict for JSON, str for text)
        """
        from app.services.ai.unified_prompt_service import get_unified_prompt_service

        await self._ensure_initialized()

        # Get assembled prompt from unified service
        prompt_service = get_unified_prompt_service()
        full_prompt = await prompt_service.assemble_prompt(module, context)

        # Add output format instructions
        if output_format == "json":
            format_instruction = """
IMPORTANTE: Responde ÚNICAMENTE con JSON válido.
- No uses markdown (no ```json)
- No agregues explicaciones antes o después del JSON
- El JSON debe estar correctamente formateado
"""
            if schema:
                format_instruction += f"\nEsquema esperado:\n{json.dumps(schema, indent=2, ensure_ascii=False)}"

            full_prompt = f"{full_prompt}\n\n{format_instruction}"

        logger.info(f"Generating {module.value} content with unified prompt ({len(full_prompt)} chars)")

        try:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            result_text = response.text.strip()

            if output_format == "json":
                # Clean up JSON response
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.startswith("```"):
                    result_text = result_text[3:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]

                return json.loads(result_text.strip())

            return result_text

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise

    async def generate_podcast_unified(
        self,
        topic: str,
        level: str = "básico",
        duration_minutes: int = 10,
        speakers: List[Dict] = None,
        additional_context: Optional[str] = None,
    ) -> Dict:
        """
        Generate podcast script using unified prompts.

        Args:
            topic: Topic of the podcast
            level: Difficulty level
            duration_minutes: Target duration
            speakers: List of speaker configs
            additional_context: Extra context

        Returns:
            Dict with title and segments
        """
        if speakers is None:
            speakers = [
                {"id": "host_male", "name": "Carlos", "role": "host"},
                {"id": "host_female", "name": "Ana", "role": "expert"}
            ]

        context = GenerationContext(
            tema=topic,
            nivel=level,
            duracion=f"{duration_minutes} minutos",
            additional_context=additional_context,
            module_params={
                "speakers": speakers,
                "format": "conversacional",
                "word_count": duration_minutes * 130,
            }
        )

        schema = {
            "title": "string",
            "segments": [
                {
                    "order": "number",
                    "speaker_id": "string",
                    "speaker_name": "string",
                    "text": "string",
                    "duration_estimate": "number"
                }
            ]
        }

        return await self.generate_with_unified_prompt(
            module=AIModule.PODCAST,
            context=context,
            output_format="json",
            schema=schema,
            temperature=0.8,
        )

    async def generate_presentation_unified(
        self,
        topic: str,
        level: str = "básico",
        num_slides: int = 10,
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate presentation using unified prompts."""
        context = GenerationContext(
            tema=topic,
            nivel=level,
            additional_context=additional_context,
            module_params={
                "num_slides": num_slides,
            }
        )

        return await self.generate_with_unified_prompt(
            module=AIModule.PRESENTATION,
            context=context,
            output_format="json",
        )

    async def generate_mindmap_unified(
        self,
        topic: str,
        level: str = "básico",
        depth: int = 3,
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate mind map using unified prompts."""
        context = GenerationContext(
            tema=topic,
            nivel=level,
            additional_context=additional_context,
            module_params={
                "depth": depth,
            }
        )

        return await self.generate_with_unified_prompt(
            module=AIModule.MINDMAP,
            context=context,
            output_format="json",
        )

    async def generate_audio_unified(
        self,
        topic: str,
        level: str = "básico",
        duration_minutes: int = 5,
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate audio script using unified prompts."""
        context = GenerationContext(
            tema=topic,
            nivel=level,
            duracion=f"{duration_minutes} minutos",
            additional_context=additional_context,
        )

        return await self.generate_with_unified_prompt(
            module=AIModule.AUDIO,
            context=context,
            output_format="json",
        )

    async def generate_flashcards_unified(
        self,
        topic: str,
        level: str = "básico",
        num_cards: int = 10,
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate flashcards using unified prompts."""
        context = GenerationContext(
            tema=topic,
            nivel=level,
            additional_context=additional_context,
            module_params={
                "num_cards": num_cards,
            }
        )

        return await self.generate_with_unified_prompt(
            module=AIModule.FLASHCARD,
            context=context,
            output_format="json",
        )

    async def generate_quiz_unified(
        self,
        topic: str,
        level: str = "básico",
        num_questions: int = 10,
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate quiz using unified prompts."""
        context = GenerationContext(
            tema=topic,
            nivel=level,
            additional_context=additional_context,
            module_params={
                "num_questions": num_questions,
            }
        )

        return await self.generate_with_unified_prompt(
            module=AIModule.QUIZ,
            context=context,
            output_format="json",
        )

    async def generate_video_unified(
        self,
        topic: str,
        level: str = "básico",
        duration_seconds: int = 60,
        style: str = "tutorial",
        additional_context: Optional[str] = None,
    ) -> Dict:
        """Generate video content using unified prompts."""
        context = GenerationContext(
            tema=topic,
            nivel=level,
            duracion=f"{duration_seconds} segundos",
            additional_context=additional_context,
            module_params={
                "style": style,
            }
        )

        return await self.generate_with_unified_prompt(
            module=AIModule.VIDEO,
            context=context,
            output_format="json",
        )


# Singleton instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Get the Gemini service singleton"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
