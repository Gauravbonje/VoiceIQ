"""
app/rag/query.py

ROOT CAUSE OF PREVIOUS BUG:
    litellm.acompletion was called without api_key= parameter.
    litellm then fell back to the environment variable GROQ_API_KEY.
    The .env file only defined groq_api_key_1, groq_api_key_2, groq_api_key_3
    — not groq_api_key — so litellm received no key and returned Invalid API Key.

FIX:
    Pass api_key=next(groq_key_cycle) explicitly on every litellm call,
    exactly as done in the agent files.
"""

from app.rag.store import get_collection
from app.core.config import settings, groq_key_cycle
from app.core.logging import log
from typing import Optional, List, Dict
import litellm


CHAT_PROMPT = """You are an intelligent assistant with access to a transcript.

CRITICAL RULES:
1. Answer ONLY using the CONTEXT sections provided below.
2. If the answer is not in the context, say exactly: "That information is not in this recording."
3. When possible, attribute answers to specific speakers by name (Speaker A, Speaker B, etc.).
4. Be precise and direct. Do not pad the answer with caveats.
5. If asked who said something, search the context for speaker attribution first.
6. For Hindi content, respond in the same language as the question.

CONTEXT FROM TRANSCRIPT:
{context}

---
USER QUESTION: {question}

Answer:"""


def semantic_search(
    query: str,
    job_id: Optional[str] = None,
    n_results: int = 5,
) -> List[Dict]:
    """
    Retrieve semantically relevant chunks from ChromaDB.
    Returns empty list on any failure — never raises.
    """
    try:
        collection = get_collection()
        where = {"job_id": {"$eq": job_id}} if job_id else None

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return []

        formatted = []
        for i in range(len(documents)):
            dist = distances[i] if distances else 0.0
            formatted.append({
                "text": documents[i],
                "metadata": metadatas[i],
                "relevance_score": round(1.0 - dist, 3),
            })

        return sorted(formatted, key=lambda x: x["relevance_score"], reverse=True)

    except Exception as e:
        log.error(f"Semantic search failed: {e}")
        return []


async def answer_question(
    question: str,
    job_id: Optional[str] = None,
) -> Dict:
    """
    Full RAG pipeline:
    1. Retrieve top-5 relevant chunks from ChromaDB.
    2. Build numbered context blocks with speaker + timestamp metadata.
    3. Send to Groq with strict grounding prompt and explicit api_key.
    4. Return structured response — never raises to the caller.
    """
    log.info(f"RAG query: {question[:60]}...")

    # ── Step 1: Retrieve ────────────────────────────────────────────
    chunks = semantic_search(question, job_id=job_id, n_results=5)

    if not chunks:
        log.warning(f"No chunks found for job_id={job_id}")
        return {
            "answer": (
                "No relevant content found. "
                "Make sure the job has finished processing and the job ID is correct."
            ),
            "sources": [],
            "chunks_used": 0,
            "tokens_used": 0,
        }

    # ── Step 2: Build context ───────────────────────────────────────
    context_blocks = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        start = meta.get("start_sec", 0)
        end = meta.get("end_sec", 0)
        speakers = meta.get("speakers", "Unknown")
        context_blocks.append(
            f"[Chunk {i} | {start:.0f}s\u2013{end:.0f}s | {speakers}]\n{chunk.get('text', '')}"
        )

    context_text = "\n\n".join(context_blocks)

    # ── Step 3: LLM call ────────────────────────────────────────────
    # FIX: api_key is now explicitly passed so litellm does not fall
    # back to the missing GROQ_API_KEY environment variable.
    api_key = next(groq_key_cycle)

    try:
        response = await litellm.acompletion(
            model=f"groq/{settings.groq_llm_model}",
            api_key=api_key,                      # <-- THE FIX
            messages=[{
                "role": "user",
                "content": CHAT_PROMPT.format(
                    context=context_text,
                    question=question,
                ),
            }],
            max_tokens=600,
            temperature=0.1,
            timeout=30,
        )
    except litellm.RateLimitError as e:
        log.warning(f"RAG rate limit hit: {e}. Returning cached context summary.")
        # Graceful degradation: return the raw context so the user gets something useful
        fallback = "\n\n".join(
            f"[{c['metadata'].get('start_sec', 0):.0f}s] {c['text'][:300]}"
            for c in chunks[:3]
        )
        return {
            "answer": (
                "The AI assistant is temporarily rate-limited. "
                "Here are the most relevant transcript sections:\n\n" + fallback
            ),
            "sources": [c.get("metadata", {}) for c in chunks],
            "chunks_used": len(chunks),
            "tokens_used": 0,
        }
    except Exception as e:
        log.error(f"RAG LLM call failed: {e}")
        return {
            "answer": "The assistant encountered an error. Please try again in a few seconds.",
            "sources": [c.get("metadata", {}) for c in chunks],
            "chunks_used": len(chunks),
            "tokens_used": 0,
        }

    # ── Step 4: Parse response ──────────────────────────────────────
    try:
        choices = getattr(response, "choices", None)
        if not choices:
            raise ValueError("Empty choices in response")
        answer = choices[0].message.content or "Model returned an empty response."
    except Exception as e:
        log.error(f"Response parsing failed: {e}")
        answer = "Error reading model response. Please try again."

    try:
        usage = getattr(response, "usage", None)
        tokens_used = usage.total_tokens if usage else 0
    except Exception:
        tokens_used = 0

    log.info(f"RAG answered. Tokens: {tokens_used}")

    return {
        "answer": answer,
        "sources": [c.get("metadata", {}) for c in chunks],
        "chunks_used": len(chunks),
        "tokens_used": tokens_used,
    }
