import asyncio
import json
import time

from app.workers.worker import celery
from app.pipeline.ingest import normalize_audio, download_youtube
from app.pipeline.deepgram_client import (
    transcribe_file,
    extract_confidence_report,
)
from app.pipeline.cleaner import run_cleaner
from app.agents.runner import run_all_agents
from app.rag.store import store_transcript_chunks
from app.core.config import settings
from app.core.logging import log


@celery.task(bind=True, max_retries=2, soft_time_limit=600)
def process_audio_task(
    self,
    input_path: str,
    job_id: str,
    source_type: str = "meeting",
    is_url: bool = False,
) -> dict:
    """
    Full pipeline execution.
    """
    start_total = time.time()

    try:
        # ── Step 1: Normalize ───────────────────────────────
        log.info(f"[{job_id}] Step 1: Normalizing audio")

        if is_url:
            audio_path = download_youtube(input_path)
        else:
            audio_path = normalize_audio(input_path)

        # ── Step 2: Deepgram ────────────────────────────────
        log.info(f"[{job_id}] Step 2: Deepgram transcription")
        t2 = time.time()

        raw_words = asyncio.run(transcribe_file(audio_path))
        quality = extract_confidence_report(raw_words)

        log.info(
            f"[{job_id}] Deepgram done in {time.time() - t2:.1f}s | {quality}"
        )

        # ── Step 3: Cleaning ────────────────────────────────
        log.info(f"[{job_id}] Step 3: Cleaning transcript")
        clean_result = run_cleaner(raw_words)

        # ── Step 4: Agents ──────────────────────────────────
        log.info(f"[{job_id}] Step 4: Running agents")
        t4 = time.time()

        agent_result = asyncio.run(run_all_agents(clean_result))

        log.info(
            f"[{job_id}] Agents done in {time.time() - t4:.1f}s"
        )

        # ── Step 5: RAG storage ─────────────────────────────
        log.info(f"[{job_id}] Step 5: Storing chunks")

        n_chunks = store_transcript_chunks(
            clean_result["turns"],
            job_id,
            source_type,
        )

        # ── Step 6: Save transcript ─────────────────────────
        transcript_path = f"{settings.data_dir}/transcripts/{job_id}.json"

        with open(transcript_path, "w") as f:
            json.dump(
                {
                    "job_id": job_id,
                    "source_type": source_type,
                    "quality": quality,
                    "turns": clean_result["turns"],
                    "word_count": clean_result["word_count"],
                },
                f,
                indent=2,
            )

        # ── Step 7: Save summary ────────────────────────────
        summary_path = (
            f"{settings.data_dir}/transcripts/{job_id}_summary.json"
        )

        with open(summary_path, "w") as f:
            json.dump(
                {
                    "job_id": job_id,
                    "source_type": source_type,
                    "summary": agent_result["summary"],
                    "action_items": agent_result["action_items"],
                    "speaker_profiles": agent_result["speaker_profiles"],
                    "rag_chunks_stored": n_chunks,
                    "total_tokens_used": agent_result["total_tokens_used"],
                    "processing_time_sec": round(
                        time.time() - start_total, 1
                    ),
                },
                f,
                indent=2,
            )

        # ── Final result ────────────────────────────────────
        total_time = round(time.time() - start_total, 1)

        log.info(f"[{job_id}] Pipeline complete in {total_time}s")

        return {
            "status": "complete",
            "job_id": job_id,
            "processing_time_sec": total_time,
            "word_count": clean_result["word_count"],
            "speaker_count": quality["speaker_count"],
            "rag_chunks": n_chunks,
        }

    except Exception as e:
        log.error(f"[{job_id}] Pipeline failed: {e}")

        # Retry task
        raise self.retry(exc=e, countdown=15)