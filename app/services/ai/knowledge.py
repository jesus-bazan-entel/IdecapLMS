"""
Knowledge Base for AI Studio Content Generation
Static defaults for backward compatibility.
For configurable prompts, use unified_prompt_service.py
"""

# Voice configuration
VOICES = {
    "es": {
        "male": "es-ES-Standard-B",
        "female": "es-ES-Standard-A"
    },
    "pt": {
        "male": "pt-BR-Standard-B",
        "female": "pt-BR-Standard-A"
    }
}

# Available difficulty levels
LEVELS = ["básico", "intermedio", "avanzado"]

# Available content types
CONTENT_TYPES = [
    "audio_tts",
    "presentation",
    "mindmap",
    "podcast",
    "video",
    "flashcard",
    "quiz",
    "lesson"
]

# Default Master Prompt (for backward compatibility)
DEFAULT_MASTER_PROMPT = """# IDECAP AI Studio - Sistema Educativo

Eres un asistente educativo especializado en la enseñanza de PORTUGUÉS BRASILEÑO para hispanohablantes peruanos.

## CONTEXTO INSTITUCIONAL
- Instituto: IDECAP (Instituto de Desarrollo de Capacidades)
- Audiencia: Estudiantes adultos peruanos
- Objetivo: Dominio comunicativo del portugués brasileño

## PRINCIPIOS PEDAGÓGICOS
1. **Interlingua Consciente**: Aprovecha la similitud español-portugués, pero alerta sobre falsos amigos
2. **Pronunciación Prioritaria**: Siempre indica cómo se pronuncia (transcripción fonética simplificada)
3. **Contexto Cultural**: Incluye referencias a la cultura brasileña relevantes para peruanos
4. **Progresión Natural**: Del reconocimiento a la producción

## FALSOS AMIGOS IMPORTANTES
| Portugués | Significa | NO significa |
|-----------|-----------|--------------|
| exquisito | raro, extraño | delicioso |
| embaraçada | avergonzada | embarazada |
| polvo | pulpo | polvo (pó) |
| borracha | goma/caucho | borracha (bêbada) |
| oficina | taller mecánico | oficina (escritório) |
| salada | ensalada | salada (salgada) |

## FORMATO DE RESPUESTA
- Usa español como idioma base
- Portugués en **negrita** con pronunciación entre paréntesis
- Ejemplos prácticos y situacionales
- Incluye tips de memoria cuando sea útil
"""


def get_master_prompt() -> str:
    """Get the master prompt for AI content generation."""
    return DEFAULT_MASTER_PROMPT


def get_audio_prompt(
    tema: str,
    nivel: str = "básico",
    contexto: str = "",
    voz_es: str = "es-ES-Standard-A",
    voz_pt: str = "pt-BR-Standard-A"
) -> str:
    """Generate prompt for audio/TTS content."""
    return f"""
Genera contenido de audio educativo sobre: {tema}
Nivel: {nivel}
{f"Contexto adicional: {contexto}" if contexto else ""}

El contenido debe:
1. Alternar entre explicaciones en español y ejemplos en portugués
2. Incluir pausas naturales entre secciones
3. Pronunciar claramente las palabras en portugués
4. Durar aproximadamente 3-5 minutos
5. Ser conversacional y ameno

Voces a usar:
- Español: {voz_es}
- Portugués: {voz_pt}

Estructura:
1. Introducción (30 segundos)
2. Vocabulario clave con pronunciación
3. Frases de ejemplo
4. Práctica de repetición
5. Cierre con resumen
"""


def get_presentation_prompt(
    tema: str,
    nivel: str = "básico",
    num_slides: int = 10,
    enfoque: str = "vocabulario"
) -> str:
    """Generate prompt for presentation slides."""
    return f"""
Genera una presentación educativa sobre: {tema}
Nivel: {nivel}
Número de slides: {num_slides}
Enfoque: {enfoque}

Cada slide debe incluir:
- Título claro
- 3-5 puntos clave
- Ejemplos en portugués con traducción
- Notas del presentador

Estructura recomendada:
1. Portada
2. Objetivos de aprendizaje
3-{num_slides-2}. Contenido principal
{num_slides-1}. Resumen
{num_slides}. Práctica/Ejercicios
"""


def get_mindmap_prompt(
    tema: str,
    nivel: str = "básico",
    enfoque: str = "vocabulario relacionado"
) -> str:
    """Generate prompt for mind maps."""
    return f"""
Genera un mapa mental educativo sobre: {tema}
Nivel: {nivel}
Enfoque: {enfoque}

El mapa debe:
1. Tener un nodo central con el tema principal
2. 4-6 ramas principales
3. 2-4 subramas por rama principal
4. Incluir ejemplos en portugués en los nodos finales
5. Usar colores temáticos consistentes

Organización sugerida:
- Vocabulario esencial
- Expresiones comunes
- Gramática relacionada
- Contextos de uso
- Falsos amigos (si aplica)
"""


def get_podcast_prompt(
    tema: str,
    nivel: str = "básico",
    duracion: int = 10,
    formato: str = "conversacional",
    participante_adicional: str = "Invitado experto"
) -> str:
    """Generate prompt for podcast scripts."""
    return f"""
Genera un guión de podcast educativo sobre: {tema}
Nivel: {nivel}
Duración objetivo: {duracion} minutos
Formato: {formato}
Participante adicional: {participante_adicional}

Estructura del podcast:
1. INTRO (1-2 min): Saludo, presentación del tema
2. DESARROLLO ({duracion - 4} min): Contenido principal
3. CIERRE (1-2 min): Resumen, despedida

Características:
- Diálogo natural entre presentadores
- Intercalar explicaciones con ejemplos prácticos
- Incluir anécdotas culturales brasileñas
- Palabras en portugués con pronunciación
- Ritmo dinámico con preguntas entre hosts

Formato de segmentos:
- speaker_id: identificador del hablante
- speaker_name: nombre del presentador
- text: contenido del diálogo
- duration_estimate: segundos estimados
"""


def get_video_prompt(
    tema: str,
    nivel: str = "básico",
    tipo_video: str = "tutorial",
    duracion: int = 5
) -> str:
    """Generate prompt for video content."""
    return f"""
Genera contenido para un video educativo sobre: {tema}
Nivel: {nivel}
Tipo de video: {tipo_video}
Duración: {duracion} minutos

El video debe incluir:
1. Guión de narración completo
2. Descripción visual para cada escena
3. Textos a mostrar en pantalla
4. Momentos de interacción/pausa

Estructura:
1. Hook inicial (10 seg)
2. Presentación del tema (30 seg)
3. Contenido principal ({duracion - 2} min)
4. Resumen y call-to-action (30 seg)

Estilo visual:
- Limpio y profesional
- Colores de marca IDECAP
- Subtítulos cuando se habla portugués
- Animaciones sutiles para puntos clave
"""
