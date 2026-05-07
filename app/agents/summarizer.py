"""
app/agents/summarizer.py

CHANGE FROM PREVIOUS VERSION:
    - Removed internal transcript truncation (now handled by runner.py _compress_transcript).
    - max_tokens reduced from 1,500 to 1,000 to leave room for other parallel agents.
    - api_key always passed explicitly via groq_key_cycle.
"""

from app.core.config import settings, groq_key_cycle
from app.core.logging import log
import litellm


SUMMARY_PROMPT = """You are an expert analyst producing a structured analysis of a transcript.

STRICT RULES:
- Answer ONLY from the transcript content below.
- Do not add external knowledge, context, or assumptions.
- If something is not stated in the transcript, write "Not mentioned."
- Be specific. Name speakers when attributing statements.

TRANSCRIPT:
{transcript}

Produce exactly these sections:

## Executive Summary
3-4 sentences capturing the core purpose and main conclusion.

## Key Topics Discussed
Each major topic with a 1-2 sentence description of what was actually said.

## Important Statements
The 3-5 most significant statements, with speaker attribution (e.g., "Speaker A stated...").

## Context and Background
What situation, problem, or goal was being discussed?"""


async def run_summarizer(transcript: str) -> dict:
    """
    Generate structured summary from the compressed transcript.
    The transcript is already within token budget — no further truncation needed.
    """
    log.info("Summarizer agent starting")

    api_key = next(groq_key_cycle)

    response = await litellm.acompletion(
        model=f"groq/{settings.groq_llm_model}",
        api_key=api_key,
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT.format(transcript=transcript),
        }],
        max_tokens=1000,      # Reduced from 1500 to stay within TPM budget
        temperature=0.2,
    )

    content = response.choices[0].message.content
    log.info("Summarizer agent complete")

    return {
        "summary": content,
        "tokens_used": response.usage.total_tokens,
    }
