from __future__ import annotations

import base64
import io
import logging
import os
import shutil
import torch
from dataclasses import dataclass
from typing import Any, Generator, Optional, Literal, Dict, Tuple, TYPE_CHECKING

_MISSING_TTS_DEPS: list[str] = []

try:
    import torch
except ModuleNotFoundError:
    _MISSING_TTS_DEPS.append("torch")

    class _TorchStub:
        class cuda:
            @staticmethod
            def is_available() -> bool:
                return False

        dtype = object
        float16 = "float16"
        float32 = "float32"
        bfloat16 = "bfloat16"

    torch = _TorchStub()

try:
    import soundfile as sf
except ModuleNotFoundError:
    sf = None
    _MISSING_TTS_DEPS.append("soundfile")

from pydantic import BaseModel, Field
from langchain_core.tools import tool
try:
    from qwen_tts import Qwen3TTSModel
except ModuleNotFoundError:
    Qwen3TTSModel = None
    _MISSING_TTS_DEPS.append("qwen_tts")

if TYPE_CHECKING:
    from qwen_tts import Qwen3TTSModel as Qwen3TTSModelType
else:
    Qwen3TTSModelType = Any

logger = logging.getLogger("tts_stream_tool")
logger.addHandler(logging.NullHandler())

AudioFormat = Literal["wav", "mp3"]
Profile = Literal["fast", "quality", "auto"]


@dataclass(frozen=True)
class TTSConfig:
    # Set these in env if you want to override
    model_fast_id: str = os.getenv("QWEN_TTS_MODEL_FAST_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
    model_quality_id: str = os.getenv("QWEN_TTS_MODEL_QUALITY_ID", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")

    # You can split device placement if you want:
    device_fast: str = os.getenv("QWEN_TTS_DEVICE_FAST", "cuda:0" if torch.cuda.is_available() else "cpu")
    device_quality: str = os.getenv("QWEN_TTS_DEVICE_QUALITY", "cuda:0" if torch.cuda.is_available() else "cpu")

    dtype_fast: Any = torch.float16 if torch.cuda.is_available() else torch.float32
    dtype_quality: Any = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    attn_implementation: str = os.getenv("QWEN_TTS_ATTN_IMPL", "flash_attention_2")


_CFG = TTSConfig()

# Cache: {("fast"|"quality"): model}
_MODELS: Dict[str, Any] = {}


def _ensure_tts_dependencies() -> None:
    if _MISSING_TTS_DEPS:
        raise RuntimeError(
            "Missing optional TTS dependencies: " + ", ".join(_MISSING_TTS_DEPS)
        )


def _load_model(model_id: str, device: str, dtype: Any) -> Any:
    _ensure_tts_dependencies()
    model_cls = Qwen3TTSModel
    if model_cls is None:
        raise RuntimeError("qwen_tts is not installed")
    try:
        return model_cls.from_pretrained(
            model_id,
            device_map=device,
            dtype=dtype,
            attn_implementation=_CFG.attn_implementation,
        )
    except Exception as e:
        logger.warning("Model load with attn_implementation failed, retrying default: %s", e)
        return model_cls.from_pretrained(
            model_id,
            device_map=device,
            dtype=dtype,
        )


def _get_model(profile: Literal["fast", "quality"]) -> Any:
    if profile in _MODELS:
        return _MODELS[profile]

    if profile == "fast":
        m = _load_model(_CFG.model_fast_id, _CFG.device_fast, _CFG.dtype_fast)
    else:
        m = _load_model(_CFG.model_quality_id, _CFG.device_quality, _CFG.dtype_quality)

    _MODELS[profile] = m
    return m


def _choose_profile(text: str, requested: Profile) -> Literal["fast", "quality"]:
    if requested in ("fast", "quality"):
        return requested

    # Auto heuristic: simple, predictable, and easy to tune
    n = len(text)
    # long text => quality
    if n >= 350:
        return "quality"
    # short interactive => fast
    if n <= 160:
        return "fast"
    # medium: bump to quality if it "looks like narration"
    punct = sum(text.count(c) for c in ".?!;:")
    if punct >= 6:
        return "quality"
    return "fast"


def _encode_wav_bytes(wav, sr: int) -> bytes:
    _ensure_tts_dependencies()
    if sf is None:
        raise RuntimeError("soundfile is not installed")
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV")
    return buf.getvalue()


def _encode_mp3_bytes_from_wav_bytes(wav_bytes: bytes, bitrate: str = "192k") -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found. Install ffmpeg or use format='wav'.")

    import subprocess
    proc = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-vn",
            "-acodec", "libmp3lame",
            "-b:a", bitrate,
            "-f", "mp3",
            "pipe:1",
        ],
        input=wav_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg MP3 encode failed: {proc.stderr.decode(errors='ignore')}")
    return proc.stdout


def text_to_audio_stream_local(
    text: str,
    *,
    speaker: str = "Vivian",
    language: str = "English",
    instruct: str = "",
    profile: Profile = "auto",
    fmt: AudioFormat = "wav",
    mp3_bitrate: str = "192k",
    chunk_size: int = 64 * 1024,
) -> Generator[bytes, None, None]:
    _ensure_tts_dependencies()
    chosen = _choose_profile(text, profile)
    model = _get_model(chosen)

    wavs, sr = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
        instruct=instruct,
    )

    wav0 = wavs[0] if isinstance(wavs, (list, tuple)) else wavs
    wav_bytes = _encode_wav_bytes(wav0, sr)

    if fmt == "mp3":
        wav_bytes = _encode_mp3_bytes_from_wav_bytes(wav_bytes, bitrate=mp3_bitrate)

    for i in range(0, len(wav_bytes), chunk_size):
        yield wav_bytes[i : i + chunk_size]


class _TTSInput(BaseModel):
    text: str = Field(..., description="Plain text to synthesise via local Qwen3-TTS")
    speaker: str = Field("Vivian", description="Speaker/voice preset")
    language: str = Field("English", description="Language label (e.g., English, Chinese)")
    instruct: str = Field("", description="Style/voice instruction prompt")
    profile: Profile = Field("auto", description="fast | quality | auto")
    format: AudioFormat = Field("wav", description="wav (default) or mp3 (requires ffmpeg)")
    mp3_bitrate: str = Field("192k", description="MP3 bitrate if format='mp3'")


@tool("tts_stream_tool", args_schema=_TTSInput, return_direct=True)
def tts_stream_tool(
    text: str,
    speaker: str = "Vivian",
    language: str = "English",
    instruct: str = "",
    profile: Profile = "auto",
    format: AudioFormat = "wav",
    mp3_bitrate: str = "192k",
) -> str:
    """Synthesize text to audio and return a base64-encoded audio payload."""
    buf = bytearray()
    for b in text_to_audio_stream_local(
        text,
        speaker=speaker,
        language=language,
        instruct=instruct,
        profile=profile,
        fmt=format,
        mp3_bitrate=mp3_bitrate,
    ):
        buf.extend(b)
    return base64.b64encode(buf).decode("ascii")


__all__ = ["tts_stream_tool", "text_to_audio_stream_local"]

