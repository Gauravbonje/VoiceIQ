import uuid
import shutil
import os
import json

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.workers.tasks import process_audio_task
from app.rag.query import answer_question
from app.workers.worker import celery
from app.core.config import settings


router = APIRouter(prefix="/api/v1")


# ── Upload File ─────────────────────────────────────────────
@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    source_type: str = "meeting"
):
    """Upload an audio or video file for processing."""

    allowed = {
        ".mp3", ".mp4", ".wav", ".m4a",
        ".webm", ".ogg", ".flac", ".aac"
    }

    ext = os.path.splitext(file.filename or "")[1].lower()

    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}"
        )

    job_id = str(uuid.uuid4())[:12]
    save_path = f"{settings.data_dir}/raw/{job_id}{ext}"

    try:
        with open(save_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")

    task = process_audio_task.delay(
        save_path,
        job_id,
        source_type,
        False
    )

    return {
        "job_id": job_id,
        "task_id": task.id,
        "status": "queued"
    }


# ── YouTube Request ─────────────────────────────────────────
class YouTubeRequest(BaseModel):
    url: str
    source_type: str = "youtube"


@router.post("/youtube")
async def process_youtube(req: YouTubeRequest):
    """Submit a YouTube URL for processing."""

    if not req.url.startswith((
        "https://www.youtube.com",
        "https://youtu.be"
    )):
        raise HTTPException(
            status_code=400,
            detail="Must be a valid YouTube URL"
        )

    job_id = str(uuid.uuid4())[:12]

    task = process_audio_task.delay(
        req.url,
        job_id,
        req.source_type,
        True
    )

    return {
        "job_id": job_id,
        "task_id": task.id,
        "status": "queued"
    }


# ── Task Status ─────────────────────────────────────────────
@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Check background task status."""

    task = celery.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
    }


# ── Query (RAG Chat) ────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    job_id: str


@router.post("/query")
async def query_content(req: QueryRequest):
    """Ask a question about processed audio."""

    return await answer_question(
        req.question,
        job_id=req.job_id
    )


# ── Get Transcript ──────────────────────────────────────────
@router.get("/transcript/{job_id}")
async def get_transcript(job_id: str):
    """Return cleaned transcript."""

    path = f"{settings.data_dir}/transcripts/{job_id}.json"

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Transcript not ready or job not found"
        )

    with open(path) as f:
        return json.load(f)


# ── Get Summary ─────────────────────────────────────────────
@router.get("/summary/{job_id}")
async def get_summary(job_id: str):
    """Return summary + analysis."""

    path = f"{settings.data_dir}/transcripts/{job_id}_summary.json"

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Summary not ready"
        )

    with open(path) as f:
        return json.load(f)