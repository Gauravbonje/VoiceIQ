import re
from typing import List


# Filler words to remove from transcript
FILLER_WORDS = {
    "um", "uh", "uh-huh", "hmm", "hm", "mhm", "uhh",
    "umm", "err", "ah", "ahh",
    # Hindi fillers
    "haan", "matlab", "woh", "arre", "bas",
}

# Minimum word confidence to keep (Deepgram 0.0 - 1.0)
CONFIDENCE_THRESHOLD = 0.55

# Pause gap that signals a new speaker turn (seconds)
TURN_GAP_SECONDS = 1.5

# Minimum words per paragraph before merging with next turn
MIN_PARAGRAPH_WORDS = 8


def is_filler(word: str) -> bool:
    return word.lower().strip(".,!?;:") in FILLER_WORDS


def normalize_text(text: str) -> str:
    """
    Remove extra whitespace and normalize punctuation spacing.
    """
    # Remove extra spaces
    text = re.sub(r" +", " ", text)

    # Remove space before punctuation
    text = re.sub(r" ([.,!?;:])", r"\1", text)

    # Add space after punctuation if missing (e.g., "Hello.World" → "Hello. World")
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)

    return text.strip()