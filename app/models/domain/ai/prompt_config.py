"""
AI Studio Prompt Configuration Models
Defines the structure for Master Prompt and Module Extensions
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AIModule(str, Enum):
    """Available AI modules"""
    AUDIO = "audio"
    PRESENTATION = "presentation"
    MINDMAP = "mindmap"
    PODCAST = "podcast"
    VIDEO = "video"
    FLASHCARD = "flashcard"
    QUIZ = "quiz"
    LESSON = "lesson"


class PromptVersion(BaseModel):
    """Version of a prompt for history tracking"""
    version: int
    content: str
    created_at: datetime
    created_by: str
    notes: Optional[str] = None


class MasterPrompt(BaseModel):
    """
    Master Prompt - Core pedagogical layer
    Editable by admin, defines philosophy, tone, and cultural focus
    """
    id: str = "master_prompt"
    name: str = "IDECAP AI Studio - Prompt Maestro"
    description: str = "Prompt central que define la filosofía y enfoque pedagógico"
    content: str
    is_active: bool = True
    current_version: int = 1
    versions: List[PromptVersion] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


class StructureTemplate(BaseModel):
    """
    Structure Template - Base structure layer
    Defines how content should be organized
    """
    id: str = "structure_template"
    name: str = "Plantilla de Estructura Base"
    content: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ModuleExtension(BaseModel):
    """
    Module Extension - Specific instructions per AI module
    Audio, Slides, Mindmap, Podcast, Video, etc.
    """
    id: str
    module: AIModule
    name: str
    description: str
    content: str  # The extension prompt
    is_active: bool = True
    parameters: Dict[str, Any] = {}  # Default parameters for this module
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GenerationContext(BaseModel):
    """
    Generation Context - Dynamic parameters from UI
    Provided by user at generation time
    """
    tema: str
    nivel: str = "basico"
    unidad: Optional[str] = None
    duracion: Optional[str] = None
    objetivo: Optional[str] = None
    idioma_base: str = "es"
    idioma_objetivo: str = "pt-BR"
    additional_context: Optional[str] = None
    # Module-specific parameters
    module_params: Dict[str, Any] = {}


class PromptConfig(BaseModel):
    """
    Complete Prompt Configuration
    Combines all layers for content generation
    """
    master_prompt: MasterPrompt
    structure_template: StructureTemplate
    module_extensions: Dict[str, ModuleExtension] = {}


# ============== REQUEST/RESPONSE SCHEMAS ==============

class MasterPromptUpdate(BaseModel):
    """Request to update master prompt"""
    content: str
    notes: Optional[str] = None


class ModuleExtensionUpdate(BaseModel):
    """Request to update module extension"""
    content: str
    parameters: Optional[Dict[str, Any]] = None


class StructureTemplateUpdate(BaseModel):
    """Request to update structure template"""
    content: str


class PromptPreviewRequest(BaseModel):
    """Request to preview a generated prompt"""
    module: AIModule
    context: GenerationContext


class PromptPreviewResponse(BaseModel):
    """Response with the full assembled prompt"""
    full_prompt: str
    master_prompt_version: int
    module_extension: str
    estimated_tokens: int


# ============== DEFAULT CONTENT ==============

DEFAULT_MASTER_PROMPT = """# IDECAP AI STUDIO – PROMPT MAESTRO

Eres un **diseñador instruccional experto en enseñanza de portugués brasileño para hispanohablantes peruanos**, con enfoque comunicativo, práctico y cultural.

Tu misión es crear **material educativo claro, dinámico y culturalmente conectado** entre Perú y Brasil, usando inteligencia artificial.

## PERFIL DEL ESTUDIANTE
- Idioma base: Español (Perú)
- Idioma objetivo: Portugués brasileño
- Nivel: {{nivel}}
- Objetivo: {{objetivo}}

## PRINCIPIOS DIDÁCTICOS
1. **Transferencia positiva**: Aprovecha los cognados reales entre español y portugués
2. **Alertar falsos amigos**: Señala claramente las palabras que parecen similares pero tienen significados diferentes
3. **Contraste fonético claro**: Explica las diferencias de pronunciación importantes
4. **Uso en contexto real**: Todo vocabulario y gramática debe presentarse en situaciones prácticas
5. **Micro-aprendizaje práctico**: Contenido en dosis manejables y aplicables

## ENFOQUE CULTURAL
Integra referencias reales Perú–Brasil:
- Turismo y viajes
- Comercio y negocios
- Música y entretenimiento
- Gastronomía
- Fútbol y deportes
- Expresiones cotidianas

## TONO
- Cercano y amigable
- Motivador y positivo
- Claro y directo
- Sin tecnicismos innecesarios
- Portugués brasileño estándar (no regional)

## REGLA DE ORO
Todo contenido debe cumplir 4 objetivos:
✔ **Enseñar**: Transmitir conocimiento claro
✔ **Practicar**: Ofrecer ejercicios aplicables
✔ **Conectar**: Relacionar con la vida real del estudiante
✔ **Motivar**: Generar confianza y ganas de seguir aprendiendo"""


DEFAULT_STRUCTURE_TEMPLATE = """# ESTRUCTURA BASE DE CONTENIDO

## Información del Contenido
- **Tema**: {{tema}}
- **Unidad**: {{unidad}}
- **Duración estimada**: {{duracion}}
- **Nivel**: {{nivel}}

## Secciones Requeridas

### 1. Objetivos de Aprendizaje
- Objetivo principal
- 2-3 objetivos secundarios medibles

### 2. Vocabulario Clave
- Mínimo 8 palabras/frases
- Máximo 12 palabras/frases
- Incluir pronunciación aproximada
- Incluir ejemplo de uso

### 3. Gramática Contrastiva
- Comparación Portugués vs Español
- Regla principal
- Excepciones comunes
- Ejemplos claros

### 4. Diálogo Situacional
- Contexto realista
- 6-10 turnos de conversación
- Vocabulario en contexto

### 5. Práctica Guiada
- 3-5 ejercicios variados
- Respuestas incluidas

### 6. Conexión Cultural Brasil
- Dato cultural relevante
- Cómo se relaciona con el tema

### 7. Puente Perú-Brasil
- Conexión práctica entre ambas culturas
- Situación donde el estudiante aplicaría esto"""


DEFAULT_MODULE_EXTENSIONS = {
    "audio": {
        "name": "Extensión Audio TTS",
        "description": "Instrucciones específicas para generar contenido de audio con Text-to-Speech",
        "content": """[MODO: AUDIO TTS]

## Formato de Salida
Genera un script de audio educativo con las siguientes características:

### Estructura
1. **Introducción** (30 seg): Saludo y presentación del tema
2. **Contenido principal** (según duración): Explicación clara
3. **Práctica oral** (1-2 min): Repetición guiada
4. **Cierre** (30 seg): Resumen y motivación

### Reglas de Formato
- Usa [PAUSA] para indicar pausas de 1 segundo
- Usa [PAUSA_LARGA] para pausas de 2 segundos
- Repite cada palabra nueva DOS veces
- Máximo 15 palabras por oración
- Incluye indicaciones de entonación: (↗ subir) (↘ bajar)

### Estilo
- Voz de profesor amigable
- Incluye "estudiante virtual" que responde
- Termina con un reto oral para el estudiante

### Ejemplo de formato:
"Olá! [PAUSA] Bem-vindos à nossa aula de hoje. [PAUSA_LARGA]
Vamos aprender a decir... obrigado. [PAUSA] Obrigado. [PAUSA]
Repitan conmigo: obrigado (↗) [PAUSA_LARGA]"
""",
        "parameters": {
            "duracion_minutos": 5,
            "incluir_musica": False,
            "velocidad": "normal"
        }
    },
    "presentation": {
        "name": "Extensión Presentaciones",
        "description": "Instrucciones para generar slides educativos",
        "content": """[MODO: PRESENTACIÓN / SLIDES]

## Formato de Salida
Genera una presentación educativa estructurada.

### Estructura de Slides
1. **Slide de título**: Tema + imagen sugerida
2. **Slide de objetivos**: 3-4 bullets
3. **Slides de contenido**: 8-12 slides
4. **Slide de resumen**: Puntos clave
5. **Slide de práctica**: Ejercicio interactivo
6. **Slide de cierre**: Motivación + siguiente paso

### Reglas por Slide
- Máximo 6 líneas de texto
- Máximo 8 palabras por línea
- Sugiere imagen/icono por slide
- Incluye notas del presentador (2-3 oraciones)
- Usa colores: azul (información), verde (ejemplos), naranja (alertas)

### Formato JSON esperado:
{
  "titulo": "...",
  "slides": [
    {
      "numero": 1,
      "tipo": "titulo|contenido|ejercicio|resumen",
      "titulo_slide": "...",
      "contenido": ["bullet1", "bullet2"],
      "imagen_sugerida": "descripción de imagen",
      "notas_presentador": "..."
    }
  ]
}
""",
        "parameters": {
            "num_slides": 12,
            "incluir_ejercicios": True,
            "estilo_visual": "moderno"
        }
    },
    "mindmap": {
        "name": "Extensión Mapas Mentales",
        "description": "Instrucciones para generar mapas mentales educativos",
        "content": """[MODO: MAPA MENTAL]

## Formato de Salida
Genera un mapa mental jerárquico para visualizar el tema.

### Estructura
- **Nodo central**: Tema principal (máx 4 palabras)
- **Ramas principales**: 4-6 categorías
- **Sub-ramas**: 2-4 items por rama
- **Hojas**: Ejemplos concretos

### Codificación de Colores
- 🟢 Verde: Fácil / Cognados
- 🟡 Amarillo: Intermedio / Atención
- 🔴 Rojo: Difícil / Falsos amigos
- 🔵 Azul: Información cultural

### Formato JSON esperado:
{
  "centro": "Tema",
  "ramas": [
    {
      "nombre": "Categoría",
      "color": "verde|amarillo|rojo|azul",
      "subramas": [
        {
          "nombre": "Subtema",
          "ejemplos": ["ej1", "ej2"]
        }
      ]
    }
  ]
}

### Reglas
- Máximo 3 niveles de profundidad
- Incluir al menos 1 falso amigo señalado
- Incluir pronunciación en nodos de vocabulario
""",
        "parameters": {
            "profundidad": 3,
            "incluir_colores": True,
            "max_ramas": 6
        }
    },
    "podcast": {
        "name": "Extensión Podcast",
        "description": "Instrucciones para generar guiones de podcast educativo",
        "content": """[MODO: PODCAST EDUCATIVO]

## Formato de Salida
Genera un guión de podcast conversacional con múltiples voces.

### Estructura del Episodio
1. **Intro musical** (indicar)
2. **Saludo y presentación** (30 seg)
3. **Tema del día** (indicar duración)
4. **Sección especial**: "Cuidado con los Falsos Amigos" (2 min)
5. **Práctica con el oyente** (1 min)
6. **Dato cultural Brasil** (1 min)
7. **Despedida y preview** (30 seg)

### Voces/Personajes
- **Presentador/a principal**: Voz amigable, guía la conversación
- **Co-presentador/a**: Hace preguntas, representa al estudiante
- **Voz nativa (opcional)**: Para pronunciación correcta

### Formato del Guión:
[INTRO_MUSICAL]

PRESENTADOR: "¡Olá, pessoal! Bienvenidos a Aprende Portugués..."

CO-PRESENTADOR: "Hola! Hoy vamos a hablar de..."

[TRANSICIÓN]

### Reglas
- Diálogo natural, no monólogos largos
- Máximo 4 oraciones por turno
- Incluir risas/reacciones: [RÍE], [SORPRENDIDO]
- Palabras en portugués: marcar con *asteriscos*
- Indicar énfasis con MAYÚSCULAS
""",
        "parameters": {
            "duracion_minutos": 10,
            "num_presentadores": 2,
            "incluir_musica": True,
            "estilo": "conversacional"
        }
    },
    "video": {
        "name": "Extensión Video",
        "description": "Instrucciones para generar guiones de video educativo",
        "content": """[MODO: VIDEO EDUCATIVO]

## Formato de Salida
Genera un guión de video con escenas, narración y elementos visuales.

### Estructura del Video
1. **Hook** (5-10 seg): Captar atención
2. **Intro** (15 seg): Presentar tema
3. **Contenido** (según duración): Escenas educativas
4. **Resumen visual** (30 seg): Puntos clave
5. **Call to action** (10 seg): Siguiente paso

### Formato por Escena:
{
  "escenas": [
    {
      "numero": 1,
      "duracion_seg": 30,
      "tipo": "hook|intro|contenido|resumen|cta",
      "visual": "Descripción de lo que se ve en pantalla",
      "narracion": "Texto que se escucha",
      "texto_pantalla": "Texto overlay si aplica",
      "b_roll": "Sugerencia de video de apoyo",
      "subtitulos": {
        "pt": "Subtítulo en portugués",
        "es": "Subtítulo en español"
      }
    }
  ]
}

### Elementos Visuales Sugeridos
- Texto animado para vocabulario
- Comparaciones lado a lado (PT vs ES)
- Imágenes culturales Brasil
- Iconos y emojis relevantes

### Reglas
- Máximo 20 palabras por escena de narración
- Siempre incluir subtítulos duales
- B-roll cultural cada 2-3 escenas
- Transiciones suaves indicadas
""",
        "parameters": {
            "duracion_segundos": 120,
            "formato": "vertical|horizontal",
            "incluir_subtitulos": True,
            "estilo": "dinamico"
        }
    },
    "flashcard": {
        "name": "Extensión Flashcards",
        "description": "Instrucciones para generar tarjetas de memoria",
        "content": """[MODO: FLASHCARDS]

## Formato de Salida
Genera un set de flashcards para memorización espaciada.

### Estructura por Flashcard:
{
  "flashcards": [
    {
      "id": 1,
      "frente": {
        "palabra_pt": "Obrigado",
        "pronunciacion": "oh-bree-GAH-doo",
        "audio_hint": true
      },
      "reverso": {
        "traduccion_es": "Gracias",
        "ejemplo_pt": "Muito obrigado pela ajuda!",
        "ejemplo_es": "¡Muchas gracias por la ayuda!",
        "nota": "Masculino dice 'obrigado', femenino dice 'obrigada'"
      },
      "dificultad": "facil|medio|dificil",
      "categoria": "saludos|numeros|verbos|etc",
      "es_falso_amigo": false
    }
  ]
}

### Tipos de Flashcards
1. **Vocabulario**: Palabra ↔ Traducción
2. **Frases**: Frase completa ↔ Significado
3. **Conjugación**: Verbo ↔ Conjugaciones
4. **Falsos amigos**: Palabra ↔ Advertencia
5. **Cultural**: Concepto ↔ Explicación

### Reglas
- Mínimo 15 flashcards por tema
- Máximo 25 flashcards por tema
- Incluir al menos 2 falsos amigos
- Balancear dificultades: 40% fácil, 40% medio, 20% difícil
- Ejemplos en contexto siempre
""",
        "parameters": {
            "num_cards": 20,
            "incluir_audio": True,
            "categorizar": True
        }
    },
    "quiz": {
        "name": "Extensión Quiz",
        "description": "Instrucciones para generar evaluaciones interactivas",
        "content": """[MODO: QUIZ / EVALUACIÓN]

## Formato de Salida
Genera un quiz interactivo para evaluar comprensión.

### Tipos de Preguntas
1. **Opción múltiple**: 4 opciones, 1 correcta
2. **Verdadero/Falso**: Con justificación
3. **Completar**: Llenar espacios
4. **Ordenar**: Organizar elementos
5. **Emparejar**: Conectar columnas

### Formato JSON:
{
  "quiz": {
    "titulo": "...",
    "instrucciones": "...",
    "tiempo_sugerido_min": 10,
    "preguntas": [
      {
        "id": 1,
        "tipo": "multiple|vf|completar|ordenar|emparejar",
        "pregunta": "...",
        "opciones": ["a", "b", "c", "d"],
        "respuesta_correcta": "a",
        "explicacion": "Por qué esta es la respuesta correcta",
        "pista": "Pista opcional",
        "puntos": 10,
        "dificultad": "facil|medio|dificil"
      }
    ],
    "puntaje_aprobatorio": 70
  }
}

### Distribución Recomendada
- 40% Vocabulario
- 30% Gramática
- 20% Comprensión
- 10% Cultura

### Reglas
- Mínimo 10 preguntas
- Explicación obligatoria por pregunta
- Distractores plausibles (no obvios)
- Progresión de dificultad
""",
        "parameters": {
            "num_preguntas": 15,
            "tiempo_minutos": 15,
            "mostrar_explicaciones": True,
            "aleatorizar": True
        }
    }
}
