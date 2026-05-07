"""
app/agents/actions.py

CHANGE FROM PREVIOUS VERSION:
    - Removed internal transcript truncation (handled by runner.py).
    - max_tokens reduced from 1,000 to 700.
"""

from app.core.config import settings, groq_key_cycle
from app.core.logging import log
import litellm


ACTIONS_PROMPT = """You are an expert at identifying action items from conversations.

STRICT RULES:
- Extract ONLY action items explicitly stated in the transcript.
- Do not infer or suggest tasks not directly mentioned.
- If no action items are present, write "No action items identified."

TRANSCRIPT:
{transcript}

## Action Items
For each action item found:
- Task: [what needs to be done]
  Owner: [speaker label or name, else "Unassigned"]
  Deadline: [date or timeframe, else "Not specified"]
  Context: [brief quote confirming this task]

## Key Decisions Made
Decisions that were finalized during the discussion.

## Deadlines and Dates Mentioned
Any specific dates, deadlines, or time references."""


async def run_action_extractor(transcript: str) -> dict:
    """Extract action items and decisions from the compressed transcript."""
    log.info("Action extractor agent starting")

    api_key = next(groq_key_cycle)

    response = await litellm.acompletion(
        model=f"groq/{settings.groq_llm_model}",
        api_key=api_key,
        messages=[{
            "role": "user",
            "content": ACTIONS_PROMPT.format(transcript=transcript),
        }],
        max_tokens=700,       # Reduced from 1000
        temperature=0.1,
    )

    content = response.choices[0].message.content
    log.info("Action extractor agent complete")

    return {
        "action_items": content,
        "tokens_used": response.usage.total_tokens,
    }
