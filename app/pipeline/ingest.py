import subprocess
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import log


def normalize_audio(input_path: str) -> str:
    """
    Convert any audio/video container to mono 16kHz WAV.
    This is the only format Deepgram accepts with guaranteed accuracy.
    """
    stem = Path(input_path).stem
    output_path = f"{settings.data_dir}/processed/{stem}_norm.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ac",
        "1",  # force mono
        "-ar",
        "16000",  # 16 kHz sample rate
        "-acodec",
        "pcm_s16le",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:400]}")

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    log.info(f"Normalized audio: {output_path} ({size_mb:.1f} MB)")

    return output_path


def download_youtube(url: str) -> str:
    """
    Download audio from a YouTube URL using yt-dlp.
    Returns path to normalized WAV ready for Deepgram.
    """
    job_id = str(uuid.uuid4())[:8]
    raw_path = f"{settings.data_dir}/raw/yt_{job_id}"

    cmd = [
        "yt-dlp",
        "--format",
        "bestaudio/best",
        "--extract-audio",
        "--audio-format",
        "wav",
        "--audio-quality",
        "0",
        "--output",
        f"{raw_path}.%(ext)s",
        "--no-playlist",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:400]}")

    wav_path = f"{raw_path}.wav"
    log.info(f"Downloaded YouTube audio: {wav_path}")

    return normalize_audio(wav_path)


def get_audio_duration_seconds(path: str) -> float:
    """
    Return duration in seconds using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0