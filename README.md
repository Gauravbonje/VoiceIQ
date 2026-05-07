# VoiceIQ

## AI-Powered Audio Intelligence Platform Using Multi-Agent LLMs and Retrieval-Augmented Generation

VoiceIQ is an end-to-end AI audio intelligence platform designed to transform long-form audio, meetings, lectures, interviews, and YouTube content into structured, searchable, and interactive knowledge.

The system combines Speech Recognition, Speaker Diarization, Large Language Models (LLMs), Vector Databases, and Retrieval-Augmented Generation (RAG) to generate intelligent summaries, extract action items, analyze speaker contributions, and answer contextual questions directly from transcript data.

---

# Features

- Audio and YouTube Processing
- Speech-to-Text Transcription
- Speaker Diarization
- AI-Generated Summaries
- Action Item Extraction
- Speaker Profiling
- Semantic Search with ChromaDB
- RAG-Based Conversational Querying
- Async Multi-Agent AI Pipeline
- Background Task Processing with Celery
- Scalable FastAPI Backend
- Streamlit Frontend UI

---

# System Architecture

The VoiceIQ pipeline follows these stages:

1. Audio / YouTube Input
2. Audio Normalization using FFmpeg
3. Deepgram Speech Recognition
4. Transcript Cleaning
5. Multi-Agent AI Analysis
6. Semantic Chunking
7. ChromaDB Vector Storage
8. Retrieval-Augmented Querying

---

# Core Technologies Used

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Frontend | Streamlit |
| Speech Recognition | Deepgram Nova-2 |
| LLM Inference | Groq + Llama 3.3 |
| Vector Database | ChromaDB |
| Async Workers | Celery |
| Task Queue | Redis |
| Audio Processing | FFmpeg |
| Semantic Retrieval | RAG |
| Language | Python 3.11 |

---
# Project Structure

```bash
voiceiq_production/
│
├── app/
│   ├── agents/
│   ├── api/
│   ├── core/
│   ├── pipeline/
│   ├── rag/
│   ├── utils/
│   └── workers/
│
├── data/
├── logs/
├── main.py
├── ui.py
├── requirements.txt
└── README.md
```
-------

# Multi-Agent AI Pipeline

VoiceIQ uses specialized AI agents running asynchronously.

---

## Summarizer Agent

Generates:

- Executive summaries
- Key discussion topics
- Important statements

---

## Action Extraction Agent

Extracts:

- Tasks
- Deadlines
- Decisions

---

## Speaker Profiling Agent

Analyzes:

- Speaker contributions
- Discussion roles
- Key topics discussed by each speaker

---

# Retrieval-Augmented Generation (RAG)

VoiceIQ implements RAG to enable grounded conversational querying.

## Workflow

1. Transcript chunks are stored in ChromaDB
2. User asks a question
3. Relevant semantic chunks are retrieved
4. LLM generates grounded answers using transcript context

This improves factual accuracy and reduces hallucinations.

---

# Engineering Challenges Solved

During development, several real-world AI engineering challenges were encountered and solved:

- Groq TPM (Tokens Per Minute) rate limits
- Parallel LLM burst failures
- Invalid API key propagation
- Large transcript token overflow
- Async orchestration instability
- Multilingual diarization inconsistencies

## Solutions Implemented

- Transcript compression
- Speaker batching
- Token optimization
- Multi-key API rotation
- Controlled concurrency
- Async task orchestration

---

# Screenshots

## Dashboard UI

Add project dashboard screenshot here.

---

## Transcript Analysis

Add transcript screenshot here.

---

## RAG Chat Query

Add chat screenshot here.

---

# Installation and Setup

## 1. Clone Repository

```bash
git clone https://github.com/Gauravbonje/VoiceIQ.git
cd VoiceIQ
```

---

## 2. Create Virtual Environment

```bash
python3.11 -m venv venv311
source venv311/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file and add:

```env
DEEPGRAM_API_KEY=your_deepgram_key

GROQ_API_KEY_1=your_groq_key_1
GROQ_API_KEY_2=your_groq_key_2
GROQ_API_KEY_3=your_groq_key_3
```

---

## 5. Start Redis

```bash
brew services start redis
```

Verify Redis:

```bash
redis-cli ping
```

Expected output:

```bash
PONG
```

---

# Running the Project

## Terminal 1 — FastAPI Backend

```bash
source venv311/bin/activate
uvicorn main:app --reload
```

---

## Terminal 2 — Celery Worker

```bash
source venv311/bin/activate
celery -A app.workers.worker.celery worker --loglevel=info -c 2
```

---

## Terminal 3 — Streamlit UI

```bash
source venv311/bin/activate
streamlit run ui.py
```

---

# Access URLs

| Service | URL |
|---|---|
| FastAPI Backend | http://127.0.0.1:8000 |
| Streamlit UI | http://localhost:8501 |
| API Documentation | http://127.0.0.1:8000/docs |

---

# Future Improvements

- Real-time streaming transcription
- Multi-language translation support
- Speaker emotion detection
- Advanced analytics dashboard
- Cloud-native Kubernetes deployment
- Enterprise authentication and RBAC
- Vector database scaling optimization
- Live collaborative meeting intelligence

---

# Use Cases

- Business Meeting Analysis
- Podcast Intelligence
- Lecture Summarization
- Interview Processing
- Customer Support Call Analysis
- YouTube Knowledge Extraction
- Research Discussion Analysis
- AI-Powered Meeting Assistants

---
---

# Performance Optimizations

Implemented optimizations include:

- Async processing with Celery
- Transcript compression
- Reduced token usage
- Speaker batching
- Multi-key API rotation
- Semantic chunking
- Background task execution

---

# Future Scope

- Real-time transcription
- WhisperX diarization
- Emotion and sentiment analysis
- Multi-language translation
- Local GPU inference
- Hybrid retrieval systems
- Enterprise collaboration tools

---


# Conclusion

VoiceIQ demonstrates how modern AI systems can combine Speech Recognition, Multi-Agent LLM orchestration, Vector Databases, and Retrieval-Augmented Generation to build scalable and intelligent audio understanding systems.

The project focuses heavily on real-world AI engineering challenges including async scalability, token optimization, fault tolerance, semantic retrieval, and grounded conversational AI.

---
---

# Performance Optimizations

Implemented optimizations include:

- Async processing with Celery
- Transcript compression
- Reduced token usage
- Speaker batching
- Multi-key API rotation
- Semantic chunking
- Background task execution

---

# Future Scope

- Real-time transcription
- WhisperX diarization
- Emotion and sentiment analysis
- Multi-language translation
- Local GPU inference
- Hybrid retrieval systems
- Enterprise collaboration tools

---

# References

1. Deepgram Nova-2 Documentation  
2. Groq LLM API Documentation  
3. ChromaDB Documentation  
4. FastAPI Documentation  
5. Celery Distributed Task Queue Documentation  
6. Retrieval-Augmented Generation (NeurIPS 2020)

---
