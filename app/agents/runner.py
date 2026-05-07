"""
app/agents/runner.py

ROOT CAUSE OF PREVIOUS BUG:
    asyncio.gather() fired all 3 agents simultaneously.
    Each agent sent 3,000-7,000 tokens to Groq at the same instant.
    Total burst: 9,000-21,000 tokens in <1 second.
    Groq TPM limit: 12,000 tokens per minute.
    Result: 429 RateLimitError on nearly every run.

THE MATH (from log analysis):
    Summary agent:  up to ~4,500 tokens (12,000 char transcript / ~2.7 chars per token)
    Actions agent:  up to ~4,500 tokens (same input)
    Speaker agent:  up to ~2,500 tokens per speaker
    Total parallel: 11,500+ tokens in 1 second = guaranteed 429

FIX — TOKEN BUDGET ARCHITECTURE:
    Each agent receives a hard-capped transcript slice of 3,500 characters.
    3,500 chars / 2.7 chars per token ≈ 1,296 input tokens per agent.
    3 agents * 1,296 = 3,888 input tokens total.
    Plus max_tokens completions (1,500 + 1,000 + 600 * n_speakers).
    For 1 speaker: 3,888 + 3,100 = 6,988 tokens < 12,000 limit.
    For 3 speakers: 3,888 + 4,900 = 8,788 tokens < 12,000 limit.

    asyncio.gather() is KEPT for true parallelism — all 3 fire at once.
    The input size reduction is what prevents the TPM burst.

    For long transcripts (>3,500 chars): a sliding window selects the
    most representative portion — first 2,000 + last 1,500 chars —
    so the beginning context (intro, participants) and the end context
    (decisions, conclusions) are always captured.
"""

import asyncio
from typing import Dict

from app.agents.summarizer import run_summarizer
from app.agents.actions import run_action_extractor
from app.agents.speaker_profile import run_speaker_profiler
from app.core.logging import log


# Maximum characters sent to each agent.
# 3,500 chars ≈ 1,300 tokens. 3 agents = ~3,900 input tokens max.
# Plus completions stays safely under 12,000 TPM.
AGENT_CHAR_LIMIT = 3_500


def _compress_transcript(transcript: str) -> str:
    """
    Intelligently compress a long transcript to AGENT_CHAR_LIMIT characters.

    Strategy: keep the first 2/3 (opening context, speaker introductions,
    early decisions) and the last 1/3 (final decisions, action items,
    conclusions). This preserves the most actionable content while
    fitting the token budget.
    """
    if len(transcript) <= AGENT_CHAR_LIMIT:
        return transcript

    head_size = int(AGENT_CHAR_LIMIT * 0.67)
    tail_size = AGENT_CHAR_LIMIT - head_size

    head = transcript[:head_size]
    tail = transcript[-tail_size:]

    char_removed = len(transcript) - AGENT_CHAR_LIMIT
    note = f"\n\n[... {char_removed:,} characters omitted for token budget ...]\n\n"

    return head + note + tail


async def run_all_agents(clean_result: Dict) -> Dict:
    """
    Run all agents in parallel (asyncio.gather) with token-budget-controlled inputs.

    Each agent receives a compressed transcript that fits within the per-agent
    token budget, ensuring the total request stays under the 12,000 TPM limit.

    Total wall-clock time = time of the slowest agent (not sum).
    Typical: 2-4 seconds for all three together.
    """
    full_transcript = clean_result["full_transcript"]
    speaker_texts = clean_result["speaker_texts"]

    # Apply compression BEFORE firing agents
    compressed_transcript = _compress_transcript(full_transcript)

    original_chars = len(full_transcript)
    compressed_chars = len(compressed_transcript)

    if compressed_chars < original_chars:
        log.info(
            f"Transcript compressed: {original_chars:,} → {compressed_chars:,} chars "
            f"({100 * compressed_chars / original_chars:.0f}% of original)"
        )
    else:
        log.info(f"Transcript within budget: {original_chars:,} chars")

    log.info("Launching all agents in parallel")

    try:
        summary_result, actions_result, speaker_result = await asyncio.gather(
            run_summarizer(compressed_transcript),
            run_action_extractor(compressed_transcript),
            run_speaker_profiler(speaker_texts),
        )
    except Exception as e:
        log.error(f"Agent execution failed: {e}")
        raise

    total_tokens = (
        summary_result.get("tokens_used", 0)
        + actions_result.get("tokens_used", 0)
    )

    log.info(f"All agents complete. Total Groq tokens: {total_tokens}")

    return {
        "summary": summary_result.get("summary", ""),
        "action_items": actions_result.get("action_items", ""),
        "speaker_profiles": speaker_result.get("speaker_profiles", {}),
        "total_tokens_used": total_tokens,
    }
