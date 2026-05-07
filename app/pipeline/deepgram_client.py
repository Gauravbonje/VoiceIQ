import httpx
from pathlib import Path
from typing import List, Dict

from app.core.config import settings
from app.core.logging import log


DEEPGRAM_URL = (
    "https://api.deepgram.com/v1/listen"
    "?model=nova-2"
    "&diarize=true"
    "&punctuate=true"
    "&smart_format=true"
    "&filler_words=true"
    "&utterances=true"
    "&language=hi"
)


async def transcribe_file(audio_path: str) -> List[Dict]:
    """
    Send the full audio file to Deepgram in one request.
    Returns a list of word dicts with keys:
      word, start, end, confidence, speaker, punctuated_word
    """
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    file_size_mb = path.stat().st_size / (1024 * 1024)
    log.info(f"Sending {file_size_mb:.1f} MB to Deepgram: {path.name}")

    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "audio/wav",
    }

    # Timeout settings (important for large files)
    timeout = httpx.Timeout(
        connect=30.0,
        read=300.0,
        write=300.0,
        pool=30.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        with open(audio_path, "rb") as f:
            response = await client.post(
                DEEPGRAM_URL,
                headers=headers,
                content=f.read(),
            )

    if response.status_code != 200:
        raise RuntimeError(
            f"Deepgram error {response.status_code}: {response.text[:400]}"
        )

    data = response.json()

    try:
        words = data["results"]["channels"][0]["alternatives"][0]["words"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Deepgram response structure: {e}")

    if not words:
        raise RuntimeError("Deepgram returned empty word list — check audio quality")

    # Quality metrics
    confidences = [w.get("confidence", 0) for w in words]
    avg_conf = sum(confidences) / len(confidences)
    speakers = set(w.get("speaker", 0) for w in words)

    log.info(
        f"Deepgram complete: {len(words)} words, "
        f"{len(speakers)} speakers, "
        f"{avg_conf:.2%} avg confidence"
    )

    return words


def extract_confidence_report(words: List[Dict]) -> Dict:
    """
    Return quality metrics for the transcript.
    """
    confidences = [w.get("confidence", 0) for w in words]
    speakers = sorted(set(str(w.get("speaker", "?")) for w in words))

    return {
        "word_count": len(words),
        "avg_confidence": round(sum(confidences) / len(confidences), 4)
        if confidences else 0,
        "min_confidence": round(min(confidences), 4)
        if confidences else 0,
        "speaker_count": len(speakers),
        "speakers_detected": speakers,
    }