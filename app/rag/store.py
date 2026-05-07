import chromadb
import hashlib
from typing import List, Dict

from app.core.config import settings
from app.core.logging import log


_client = None
_collection = None


def get_collection():
    """
    Initialize or return existing ChromaDB collection.
    """
    global _client, _collection

    if _collection is None:
        _client = chromadb.PersistentClient(
            path=f"{settings.data_dir}/embeddings"
        )

        _collection = _client.get_or_create_collection(
            name="voiceiq_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

        log.info("ChromaDB collection initialized")

    return _collection


def store_transcript_chunks(
    turns: List[Dict],
    job_id: str,
    source_type: str
) -> int:
    """
    Chunk speaker turns into ~200-word semantic blocks and store in ChromaDB.
    Returns number of chunks stored.
    """
    collection = get_collection()

    chunks = _create_semantic_chunks(turns, max_words=200)

    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        # Build text with speaker labels
        lines = [
            f"{t['speaker_label']}: {t['text']}"
            for t in chunk["turns"]
        ]
        doc_text = " ".join(lines)

        chunk_id = hashlib.md5(
            f"{job_id}_{i}".encode()
        ).hexdigest()

        documents.append(doc_text)

        metadatas.append({
            "job_id": job_id,
            "chunk_index": i,
            "start_sec": chunk["start"],
            "end_sec": chunk["end"],
            "speakers": ", ".join(chunk["speakers"]),
            "source_type": source_type,
            "word_count": len(doc_text.split()),
        })

        ids.append(chunk_id)

    if documents:
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            log.info(f"Stored {len(documents)} chunks for job {job_id}")
        except Exception as e:
            log.error(f"ChromaDB insert failed: {e}")
            raise

    return len(documents)


def _create_semantic_chunks(
    turns: List[Dict],
    max_words: int = 200
) -> List[Dict]:
    """
    Create overlapping semantic chunks (~200 words each).
    """
    chunks = []
    current_turns = []
    current_words = 0

    for turn in turns:
        word_count = len(turn["text"].split())

        if current_words + word_count > max_words and current_turns:
            chunks.append(_build_chunk_meta(current_turns))

            # overlap last turn
            current_turns = [current_turns[-1], turn]
            current_words = (
                len(current_turns[0]["text"].split()) + word_count
            )
        else:
            current_turns.append(turn)
            current_words += word_count

    if current_turns:
        chunks.append(_build_chunk_meta(current_turns))

    return chunks


def _build_chunk_meta(turns: List[Dict]) -> Dict:
    """
    Build metadata for a chunk.
    """
    return {
        "turns": turns,
        "start": turns[0]["start"],
        "end": turns[-1]["end"],
        "speakers": list(
            set(t["speaker_label"] for t in turns)
        ),
    }