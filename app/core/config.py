from pydantic_settings import BaseSettings
from pathlib import Path
import itertools


class Settings(BaseSettings):
    # ── API Keys ─────────────────────────────
    deepgram_api_key: str = ""

    groq_api_key_1: str = ""
    groq_api_key_2: str = ""
    groq_api_key_3: str = ""

    groq_llm_model: str = "llama-3.3-70b-versatile"

    # ── Infra ───────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    data_dir: str = "data"
    log_level: str = "INFO"

    # ── ENV Config ──────────────────────────
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ── Multi-key rotation (SOP logic) ──────
    def groq_keys(self):
        keys = [
            k for k in [
                self.groq_api_key_1,
                self.groq_api_key_2,
                self.groq_api_key_3
            ] if k
        ]

        # cycle → infinite rotation
        return itertools.cycle(keys) if keys else itertools.cycle([""])


# ── Init settings ──────────────────────────
settings = Settings()

# Global iterator (IMPORTANT: don't recreate every call)
groq_key_cycle = settings.groq_keys()

# ── Create directories ─────────────────────
for _d in [
    "data/raw",
    "data/processed",
    "data/transcripts",
    "data/embeddings",
    "logs"
]:
    Path(_d).mkdir(parents=True, exist_ok=True)