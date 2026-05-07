"""
app/agents/speaker_profile.py

ROOT CAUSE OF PREVIOUS BUG (9-speaker video):
    asyncio.gather(*tasks) fired 9 simultaneous LLM calls.
    9 speakers * ~1,200 tokens each = 10,800 tokens in 1 second.
    Combined with summary + actions already in flight = guaranteed 429.

FIX:
    - Each speaker's text is capped at 2,000 characters before sending.
    - If there are more than 3 speakers, profiles run in sequential batches of 3.
      Batch size 3 * ~800 tokens = 2,400 tokens — well within the remaining budget
      after summary + actions have consumed their share.
    - For 1-3 speakers: true parallel (asyncio.gather).
    - For 4+ speakers: batches of 3 with no sleep needed (sequential is fast enough).
"""

import asyncio
from typing import Dict

from app.core.config import settings, groq_key_cycle
from app.core.logging import log
import litellm


SPEAKER_PROMPT = """You are analyzing a speaker's contribution to a conversation.

STRICT RULES:
- Describe ONLY what this speaker actually said in the text below.
- Do not infer personality or expertise not expressed in the text.
- Keep each section concise: 2-4 bullet points maximum.

SPEAKER: {speaker_label}
SPEAKER TEXT:
{speaker_text}

## Main Topics Addressed
What subjects did this speaker raise or discuss?

## Key Points Made
The main arguments, statements, or information this speaker provided.

## Questions Asked
Questions this speaker asked (write "None" if none).

## Role in Discussion
What role did this speaker play? (presenter / questioner / decision-maker / participant)"""


# Maximum characters sent per speaker — keeps token cost per call low
SPEAKER_CHAR_LIMIT = 2_000

# Maximum speakers profiled in parallel — prevents token burst with many speakers
BATCH_SIZE = 3


async def _profile_one(label: str, text: str) -> tuple:
    """Profile a single speaker. Returns (label, profile_text)."""
    if len(text.split()) < 15:
        return label, "Insufficient speech data to generate a profile."

    trimmed = text[:SPEAKER_CHAR_LIMIT]
    api_key = next(groq_key_cycle)

    response = await litellm.acompletion(
        model=f"groq/{settings.groq_llm_model}",
        api_key=api_key,
        messages=[{
            "role": "user",
            "content": SPEAKER_PROMPT.format(
                speaker_label=label,
                speaker_text=trimmed,
            ),
        }],
        max_tokens=500,       # Reduced from 600
        temperature=0.2,
    )

    return label, response.choices[0].message.content


async def run_speaker_profiler(speaker_texts: Dict[str, str]) -> dict:
    """
    Generate per-speaker profiles.

    For 1-3 speakers: all run in parallel.
    For 4+ speakers: run in sequential batches of BATCH_SIZE to control
    token burst without blocking the overall pipeline for long.
    """
    n = len(speaker_texts)
    log.info(f"Speaker profiler starting for {n} speakers")

    items = list(speaker_texts.items())
    profiles = {}

    if n <= BATCH_SIZE:
        # Small number of speakers — full parallel
        tasks = [_profile_one(label, text) for label, text in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.warning(f"Speaker profile failed for one speaker: {result}")
            else:
                label, profile = result
                profiles[label] = profile
    else:
        # Many speakers — batch to control TPM
        log.info(f"Batching {n} speakers into groups of {BATCH_SIZE}")
        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i:i + BATCH_SIZE]
            tasks = [_profile_one(label, text) for label, text in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.warning(f"Speaker profile failed: {result}")
                else:
                    label, profile = result
                    profiles[label] = profile
            # Small pause between batches when there are many speakers
            if i + BATCH_SIZE < len(items):
                await asyncio.sleep(2)

    log.info("Speaker profiler complete")
    return {"speaker_profiles": profiles}
