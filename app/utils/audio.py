import subprocess
from pathlib import Path


ALLOWED_EXTENSIONS = {
    ".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg", ".flac", ".aac"
}


def is_valid_audio_file(path: str) -> bool:
    """Check if file exists and has a valid extension."""
    p = Path(path)
    return p.exists() and p.suffix.lower() in ALLOWED_EXTENSIONS


def get_audio_duration(path: str) -> float:
    """
    Get audio duration in seconds using ffprobe.
    Returns 0.0 if failed.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return float(result.stdout.strip())
    except:
        return 0.0


def is_audio_too_short(path: str, min_seconds: float = 3.0) -> bool:
    """Reject extremely short audio (likely invalid)."""
    duration = get_audio_duration(path)
    return duration < min_seconds


def is_audio_too_large(path: str, max_mb: float = 500) -> bool:
    """Optional safety: reject extremely large files."""
    size_mb = Path(path).stat().st_size / (1024 * 1024)
    return size_mb > max_mb