from typing import List, Dict

from app.utils.text import (
    is_filler,
    normalize_text,
    CONFIDENCE_THRESHOLD,
    TURN_GAP_SECONDS,
    MIN_PARAGRAPH_WORDS,
)
from app.core.logging import log


def clean_words(raw_words: List[Dict]) -> List[Dict]:
    """
    Step 1: Filter raw Deepgram word objects.
    Remove fillers, low-confidence tokens, and empty strings.
    """
    cleaned = []
    removed = 0

    for w in raw_words:
        word_text = (w.get("punctuated_word") or w.get("word") or "").strip()

        if not word_text:
            continue

        if w.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
            removed += 1
            continue

        if is_filler(w.get("word", "")):
            removed += 1
            continue

        cleaned.append(
            {
                "word": word_text,
                "start": w.get("start", 0.0),
                "end": w.get("end", 0.0),
                "speaker": w.get("speaker", 0),
                "confidence": w.get("confidence", 1.0),
            }
        )

    log.debug(
        f"Cleaned words: {len(raw_words)} in, {len(cleaned)} kept, {removed} removed"
    )
    return cleaned


def build_speaker_turns(words: List[Dict]) -> List[Dict]:
    """
    Step 2: Group words into speaker turns.
    A new turn begins when the speaker changes OR when a pause
    longer than TURN_GAP_SECONDS occurs (even same speaker).
    """
    if not words:
        return []

    turns = []

    current = {
        "speaker": words[0]["speaker"],
        "words": [words[0]["word"]],
        "start": words[0]["start"],
        "end": words[0]["end"],
    }

    for prev, curr in zip(words, words[1:]):
        gap = curr["start"] - prev["end"]
        same_speaker = curr["speaker"] == current["speaker"]

        if same_speaker and gap < TURN_GAP_SECONDS:
            current["words"].append(curr["word"])
            current["end"] = curr["end"]
        else:
            turns.append(
                {
                    **current,
                    "text": normalize_text(" ".join(current["words"])),
                }
            )
            current = {
                "speaker": curr["speaker"],
                "words": [curr["word"]],
                "start": curr["start"],
                "end": curr["end"],
            }

    # Append last turn
    turns.append(
        {
            **current,
            "text": normalize_text(" ".join(current["words"])),
        }
    )

    return [t for t in turns if t["text"].strip()]


def merge_short_turns(turns: List[Dict]) -> List[Dict]:
    """
    Step 3: Merge consecutive same-speaker turns that are too short
    to stand alone as a paragraph.
    """
    if not turns:
        return []

    merged = [turns[0].copy()]

    for turn in turns[1:]:
        last = merged[-1]
        last_word_count = len(last["text"].split())

        if (
            turn["speaker"] == last["speaker"]
            and last_word_count < MIN_PARAGRAPH_WORDS
        ):
            last["text"] = normalize_text(last["text"] + " " + turn["text"])
            last["end"] = turn["end"]
            last["words"] = last.get("words", []) + turn.get("words", [])
        else:
            merged.append(turn.copy())

    return merged


def label_speakers(turns: List[Dict]) -> List[Dict]:
    """
    Step 4: Convert numeric speaker IDs into Speaker A, B, C...
    """
    id_map = {}
    label_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    counter = 0

    labeled = []

    for turn in turns:
        sid = turn["speaker"]

        if sid not in id_map:
            id_map[sid] = f"Speaker {label_chars[counter % 26]}"
            counter += 1

        labeled.append({**turn, "speaker_label": id_map[sid]})

    return labeled


def run_cleaner(raw_words: List[Dict]) -> Dict:
    """
    Full cleaning pipeline.
    """
    words = clean_words(raw_words)
    turns = build_speaker_turns(words)
    turns = merge_short_turns(turns)
    turns = label_speakers(turns)

    # Build transcript
    transcript_lines = []

    for t in turns:
        transcript_lines.append(
            f"{t['speaker_label']} [{t['start']:.0f}s]: {t['text']}"
        )

    full_transcript = "\n\n".join(transcript_lines)

    # Speaker aggregation
    speaker_texts: Dict[str, List[str]] = {}

    for t in turns:
        label = t["speaker_label"]
        speaker_texts.setdefault(label, [])
        speaker_texts[label].append(t["text"])

    speaker_summaries = {
        label: " ".join(paragraphs)
        for label, paragraphs in speaker_texts.items()
    }

    log.info(f"Cleaner: {len(turns)} turns, {len(speaker_texts)} speakers")

    return {
        "turns": turns,
        "full_transcript": full_transcript,
        "speaker_texts": speaker_summaries,
        "word_count": sum(len(t["text"].split()) for t in turns),
    }