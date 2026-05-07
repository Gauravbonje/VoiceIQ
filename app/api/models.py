from pydantic import BaseModel, Field
from typing import List, Dict, Optional


# ── Upload Response ─────────────────────────────────────────────
class UploadResponse(BaseModel):
    job_id: str
    task_id: str
    status: str


# ── Status Response ─────────────────────────────────────────────
class StatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict] = None


# ── YouTube Request ─────────────────────────────────────────────
class YouTubeRequest(BaseModel):
    url: str = Field(..., example="https://www.youtube.com/watch?v=abc123")
    source_type: str = "youtube"


# ── Query Request ───────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    job_id: str


# ── Query Response ──────────────────────────────────────────────
class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    chunks_used: int
    tokens_used: Optional[int] = None


# ── Transcript Response ─────────────────────────────────────────
class TranscriptTurn(BaseModel):
    speaker_label: str
    text: str
    start: float
    end: float


class TranscriptResponse(BaseModel):
    job_id: str
    source_type: str
    turns: List[TranscriptTurn]
    word_count: int
    quality: Dict


# ── Summary Response ────────────────────────────────────────────
class SummaryResponse(BaseModel):
    job_id: str
    source_type: str
    summary: str
    action_items: str
    speaker_profiles: Dict[str, str]
    rag_chunks_stored: int
    total_tokens_used: int
    processing_time_sec: float