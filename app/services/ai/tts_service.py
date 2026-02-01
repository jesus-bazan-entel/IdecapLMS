"""
Text-to-Speech Service
Audio generation using edge-tts (Microsoft Edge voices) with fallbacks
"""
import logging
from typing import Optional, List
from io import BytesIO
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


# Available TTS voices using Microsoft Edge TTS (natural sounding)
# Format: voice_id -> edge-tts voice name
EDGE_TTS_VOICES = {
    # Spanish - Spain (Male)
    "es-ES-Standard-B": "es-ES-AlvaroNeural",
    "es-ES-Standard-D": "es-ES-AlvaroNeural",
    # Spanish - Spain (Female)
    "es-ES-Standard-A": "es-ES-ElviraNeural",
    "es-ES-Standard-C": "es-ES-ElviraNeural",
    # Spanish - Mexico (Male)
    "es-MX-Standard-B": "es-MX-JorgeNeural",
    # Spanish - Mexico (Female)
    "es-MX-Standard-A": "es-MX-DaliaNeural",
    # Portuguese - Brazil (Male)
    "pt-BR-Standard-B": "pt-BR-AntonioNeural",
    # Portuguese - Brazil (Female)
    "pt-BR-Standard-A": "pt-BR-FranciscaNeural",
    # Portuguese - Portugal (Male)
    "pt-PT-Standard-B": "pt-PT-DuarteNeural",
    # Portuguese - Portugal (Female)
    "pt-PT-Standard-A": "pt-PT-RaquelNeural",
    # English - US (Male)
    "en-US-Standard-B": "en-US-GuyNeural",
    # English - US (Female)
    "en-US-Standard-A": "en-US-JennyNeural",
}

# Voice metadata for the API
AVAILABLE_VOICES = [
    {"id": "es-ES-Standard-A", "name": "Elvira", "language": "es-ES", "gender": "female", "edge_voice": "es-ES-ElviraNeural"},
    {"id": "es-ES-Standard-B", "name": "Álvaro", "language": "es-ES", "gender": "male", "edge_voice": "es-ES-AlvaroNeural"},
    {"id": "es-ES-Standard-C", "name": "Elvira", "language": "es-ES", "gender": "female", "edge_voice": "es-ES-ElviraNeural"},
    {"id": "es-ES-Standard-D", "name": "Álvaro", "language": "es-ES", "gender": "male", "edge_voice": "es-ES-AlvaroNeural"},
    {"id": "es-MX-Standard-A", "name": "Dalia", "language": "es-MX", "gender": "female", "edge_voice": "es-MX-DaliaNeural"},
    {"id": "es-MX-Standard-B", "name": "Jorge", "language": "es-MX", "gender": "male", "edge_voice": "es-MX-JorgeNeural"},
    {"id": "pt-BR-Standard-A", "name": "Francisca", "language": "pt-BR", "gender": "female", "edge_voice": "pt-BR-FranciscaNeural"},
    {"id": "pt-BR-Standard-B", "name": "Antônio", "language": "pt-BR", "gender": "male", "edge_voice": "pt-BR-AntonioNeural"},
    {"id": "pt-PT-Standard-A", "name": "Raquel", "language": "pt-PT", "gender": "female", "edge_voice": "pt-PT-RaquelNeural"},
    {"id": "pt-PT-Standard-B", "name": "Duarte", "language": "pt-PT", "gender": "male", "edge_voice": "pt-PT-DuarteNeural"},
    {"id": "en-US-Standard-A", "name": "Jenny", "language": "en-US", "gender": "female", "edge_voice": "en-US-JennyNeural"},
    {"id": "en-US-Standard-B", "name": "Guy", "language": "en-US", "gender": "male", "edge_voice": "en-US-GuyNeural"},
]


class TTSService:
    """Service for text-to-speech generation using edge-tts"""

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize TTS service"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("TTS Service initialized with edge-tts")

    def get_voice_info(self, voice_id: str) -> Optional[dict]:
        """Get voice information by ID"""
        for voice in AVAILABLE_VOICES:
            if voice["id"] == voice_id:
                return voice
        return None

    def _get_edge_voice(self, voice_id: str) -> str:
        """Get edge-tts voice name from voice_id"""
        return EDGE_TTS_VOICES.get(voice_id, "es-ES-AlvaroNeural")

    async def generate_audio(
        self,
        text: str,
        voice_id: str = "es-ES-Standard-A",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        Generate audio from text using edge-tts

        Args:
            text: Text to convert to speech
            voice_id: TTS voice identifier
            speed: Speech rate (0.5 to 2.0)
            pitch: Pitch adjustment (-20.0 to 20.0)

        Returns:
            Audio content as bytes (MP3 format)
        """
        self._ensure_initialized()

        # Get edge-tts voice
        edge_voice = self._get_edge_voice(voice_id)

        # Convert speed to edge-tts rate format (+X% or -X%)
        rate_percent = int((speed - 1.0) * 100)
        rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        # Convert pitch to edge-tts format
        pitch_hz = int(pitch * 5)  # Approximate conversion
        pitch_str = f"+{pitch_hz}Hz" if pitch_hz >= 0 else f"{pitch_hz}Hz"

        try:
            import edge_tts

            # Create communicate object
            communicate = edge_tts.Communicate(text, edge_voice, rate=rate_str, pitch=pitch_str)

            # Generate audio to bytes
            audio_data = BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])

            audio_data.seek(0)
            return audio_data.read()

        except ImportError:
            logger.warning("edge-tts not installed, falling back to gtts")
            return await self._generate_with_gtts(text, voice_id)
        except Exception as e:
            logger.error(f"edge-tts generation error: {e}, falling back to gtts")
            return await self._generate_with_gtts(text, voice_id)

    async def _generate_with_gtts(self, text: str, voice_id: str) -> bytes:
        """Fallback to gtts if edge-tts fails"""
        from gtts import gTTS
        import io

        # Determine language from voice_id
        lang = "es"
        if "pt-BR" in voice_id or "pt-PT" in voice_id:
            lang = "pt"
        elif "en-US" in voice_id:
            lang = "en"

        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return audio_buffer.read()
        except Exception as e:
            logger.error(f"gtts generation error: {e}")
            raise

    async def generate_audio_segments(
        self,
        segments: list,
    ) -> bytes:
        """
        Generate audio from multiple segments with different voices

        Args:
            segments: List of dicts with 'text', 'voice_id', 'speed', 'pitch'

        Returns:
            Combined audio content as bytes (MP3 format)
        """
        from pydub import AudioSegment
        import io

        self._ensure_initialized()

        combined = AudioSegment.empty()
        total_segments = len(segments)

        logger.info(f"Generating audio for {total_segments} segments with distinct voices")

        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            voice_id = segment.get("voice_id", "es-ES-Standard-A")
            speed = segment.get("speed", 1.0)
            pitch = segment.get("pitch", 0.0)

            if not text.strip():
                continue

            voice_info = self.get_voice_info(voice_id)
            voice_name = voice_info.get("name", "Unknown") if voice_info else "Unknown"
            logger.info(f"Segment {i+1}/{total_segments}: {voice_name} ({voice_id}) - {len(text)} chars")

            try:
                # Generate audio for this segment
                audio_bytes = await self.generate_audio(text, voice_id, speed, pitch)

                # Convert to AudioSegment
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

                # Add a natural pause between segments (300ms)
                combined += audio_segment + AudioSegment.silent(duration=300)

            except Exception as e:
                logger.error(f"Error generating segment {i+1}: {e}")
                continue

        if len(combined) == 0:
            raise ValueError("No audio segments were generated successfully")

        # Export combined audio
        output = io.BytesIO()
        combined.export(output, format="mp3")
        output.seek(0)

        duration_seconds = len(combined) / 1000
        logger.info(f"Audio generation complete: {duration_seconds:.1f}s total duration")

        return output.read()

    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """
        Estimate audio duration in seconds

        Based on average speech rate of ~150 words per minute
        """
        words = len(text.split())
        words_per_second = 150 / 60 / speed
        return words / words_per_second


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get the TTS service singleton"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
