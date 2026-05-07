"""
ui.py

BUGS FIXED FROM PREVIOUS VERSION:

1. INVISIBLE CHAT TEXT (CSS contrast bug):
   The .chat-user and .chat-ai divs had no explicit color: property.
   Streamlit's default theme renders these divs on a white background,
   and without a text color the browser inherits from the parent container
   which in some Streamlit versions is transparent/white-on-white.
   FIX: Added color: #1A1A1A explicitly to both chat CSS classes.

2. CHAT_JOB SCOPE BUG:
   chat_job was defined INSIDE the col_chat context block, then referenced
   in the sidebar button callbacks in col_meta which ran BEFORE col_chat
   was initialized on the first render pass. This caused NameError in some
   Streamlit versions and silent failures in others.
   FIX: Initialize chat_job from session state BEFORE the column split.

3. EXAMPLE QUESTION BUTTONS:
   Buttons in col_meta referenced chat_job but it wasn't guaranteed to be
   in scope. FIX: Read from st.session_state.job_id directly.
"""

import streamlit as st
import requests
import time

API = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="VoiceIQ",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Typography */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #0D0D0D;
        letter-spacing: -0.5px;
    }
    .sub-header {
        font-size: 1rem;
        color: #555;
        margin-bottom: 1.5rem;
    }

    /* Transcript speaker blocks */
    .speaker-block {
        background: #F8F8F8;
        border-left: 3px solid #0D7377;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
    }
    .speaker-label {
        font-weight: 600;
        color: #0D7377;
        font-size: 0.85rem;
    }
    .speaker-time {
        color: #999;
        font-size: 0.78rem;
        margin-left: 8px;
    }
    .speaker-text {
        color: #1A1A1A;           /* explicit color — prevents white-on-white */
        margin-top: 4px;
        line-height: 1.6;
    }

    /* Metric cards */
    .metric-card {
        background: #F0F4F4;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-val {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0D7377;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #666;
        margin-top: 2px;
    }

    /* Chat bubbles — FIX: explicit color on both classes */
    .chat-user {
        background: #F0F4F4;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        color: #1A1A1A;           /* FIX: was missing, caused invisible text */
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .chat-ai {
        background: #E8F4F4;
        border-left: 3px solid #0D7377;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        color: #1A1A1A;           /* FIX: was missing, caused invisible text */
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Source timestamp tags */
    .source-tag {
        font-size: 0.72rem;
        color: #555;
        background: #EBEBEB;
        border-radius: 4px;
        padding: 2px 7px;
        display: inline-block;
        margin: 2px 2px 0 0;
    }

    /* Tab styling */
    div[data-testid="stTabs"] button {
        font-size: 0.9rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">VoiceIQ</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Audio Intelligence — Meetings, Lectures, Podcasts, YouTube</div>',
    unsafe_allow_html=True,
)

# ── Session state ────────────────────────────────────────────────────────────
for key, default in [
    ("job_id", None),
    ("task_id", None),
    ("chat_history", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_process, tab_transcript, tab_analysis, tab_chat = st.tabs([
    "Process", "Transcript", "Analysis", "Chat",
])


# ── TAB 1: PROCESS ──────────────────────────────────────────────────────────
with tab_process:
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("Upload Audio or Video")
        source_type = st.selectbox(
            "Content Type",
            ["meeting", "lecture", "podcast", "interview", "youtube"],
        )
        uploaded = st.file_uploader(
            "Drop file here",
            type=["mp3", "mp4", "wav", "m4a", "webm", "ogg", "flac"],
            label_visibility="collapsed",
        )
        if uploaded and st.button("Start Processing", type="primary", use_container_width=True):
            with st.spinner("Uploading..."):
                res = requests.post(
                    f"{API}/upload?source_type={source_type}",
                    files={"file": (uploaded.name, uploaded, uploaded.type)},
                )
                if res.status_code == 200:
                    d = res.json()
                    st.session_state.job_id = d["job_id"]
                    st.session_state.task_id = d["task_id"]
                    st.success(f"Processing started. Job ID: {d['job_id']}")
                else:
                    st.error(f"Upload failed: {res.text}")

    with col2:
        st.subheader("YouTube URL")
        yt_url = st.text_input(
            "Paste a YouTube link",
            placeholder="https://www.youtube.com/watch?v=...",
        )
        yt_type = st.selectbox("Type", ["youtube", "lecture", "podcast"], key="yt_type")
        if yt_url and st.button("Process YouTube", use_container_width=True):
            with st.spinner("Queuing download..."):
                res = requests.post(
                    f"{API}/youtube",
                    json={"url": yt_url, "source_type": yt_type},
                )
                if res.status_code == 200:
                    d = res.json()
                    st.session_state.job_id = d["job_id"]
                    st.session_state.task_id = d["task_id"]
                    st.success(f"Download queued. Job ID: {d['job_id']}")
                else:
                    st.error(f"Error: {res.text}")

    # Status display
    if st.session_state.task_id:
        st.divider()
        try:
            status_res = requests.get(
                f"{API}/status/{st.session_state.task_id}", timeout=5
            )
            if status_res.ok:
                s = status_res.json()
                status = s.get("status", "UNKNOWN")
                result = s.get("result") or {}

                if status == "SUCCESS":
                    c1, c2, c3, c4 = st.columns(4)
                    for col, val_key, label in [
                        (c1, "processing_time_sec", "Processing time (s)"),
                        (c2, "word_count", "Words transcribed"),
                        (c3, "speaker_count", "Speakers detected"),
                        (c4, "rag_chunks", "RAG chunks stored"),
                    ]:
                        col.markdown(
                            f'<div class="metric-card">'
                            f'<div class="metric-val">{result.get(val_key, "?")}</div>'
                            f'<div class="metric-label">{label}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                elif status in ("STARTED", "PENDING"):
                    st.info(f"Status: {status} — processing in background...")
                    time.sleep(3)
                    st.rerun()
                elif status == "FAILURE":
                    st.error(
                        "Processing failed. Check logs/voiceiq.log for details. "
                        "Common causes: network timeout, audio too short, or API key issue."
                    )
        except requests.exceptions.ConnectionError:
            st.warning("Cannot reach API server. Is uvicorn running on port 8000?")


# ── TAB 2: TRANSCRIPT ────────────────────────────────────────────────────────
with tab_transcript:
    job_input = st.text_input(
        "Job ID",
        value=st.session_state.job_id or "",
        placeholder="Enter job ID",
        key="tx_job",
    )
    if job_input and st.button("Load Transcript", key="load_tx"):
        try:
            res = requests.get(f"{API}/transcript/{job_input}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                q = data.get("quality", {})
                st.caption(
                    f"Words: {q.get('word_count', '?')}  |  "
                    f"Speakers: {q.get('speaker_count', '?')}  |  "
                    f"Avg confidence: {q.get('avg_confidence', 0):.1%}"
                )
                turns = data.get("turns", [])
                if not turns:
                    st.warning("Transcript is empty. Audio may have been too short or unclear.")
                for turn in turns:
                    st.markdown(
                        f'<div class="speaker-block">'
                        f'<span class="speaker-label">{turn.get("speaker_label", "?")}</span>'
                        f'<span class="speaker-time">'
                        f'{turn.get("start", 0):.0f}s \u2014 {turn.get("end", 0):.0f}s'
                        f'</span>'
                        f'<div class="speaker-text">{turn.get("text", "")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            elif res.status_code == 404:
                st.warning("Transcript not ready yet. Check the Process tab for status.")
            else:
                st.error(f"Error {res.status_code}: {res.text}")
        except requests.exceptions.ConnectionError:
            st.warning("Cannot reach API server.")


# ── TAB 3: ANALYSIS ──────────────────────────────────────────────────────────
with tab_analysis:
    job_a = st.text_input(
        "Job ID",
        value=st.session_state.job_id or "",
        placeholder="Enter job ID",
        key="an_job",
    )
    if job_a and st.button("Load Analysis", key="load_an"):
        try:
            res = requests.get(f"{API}/summary/{job_a}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                sub1, sub2, sub3 = st.tabs(["Summary", "Action Items", "Speaker Profiles"])
                with sub1:
                    st.markdown(data.get("summary", "No summary available."))
                with sub2:
                    st.markdown(data.get("action_items", "No action items available."))
                with sub3:
                    profiles = data.get("speaker_profiles", {})
                    if not profiles:
                        st.info("No speaker profiles available.")
                    for speaker, profile in profiles.items():
                        with st.expander(speaker, expanded=True):
                            st.markdown(profile)
                st.caption(
                    f"Processing time: {data.get('processing_time_sec', '?')}s  |  "
                    f"Tokens used: {data.get('total_tokens_used', '?')}  |  "
                    f"RAG chunks: {data.get('rag_chunks_stored', '?')}"
                )
            elif res.status_code == 404:
                st.warning("Analysis not ready. Check the Process tab.")
            else:
                st.error(f"Error {res.status_code}: {res.text}")
        except requests.exceptions.ConnectionError:
            st.warning("Cannot reach API server.")


# ── TAB 4: CHAT ──────────────────────────────────────────────────────────────
with tab_chat:
    # FIX: Read chat_job BEFORE splitting into columns.
    # This ensures it is in scope for both col_chat and col_meta.
    chat_job_value = st.session_state.job_id or ""

    col_chat, col_meta = st.columns([3, 1], gap="large")

    with col_chat:
        # Render existing chat history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                sources_html = " ".join(
                    f'<span class="source-tag">'
                    f'{s.get("start_sec", 0):.0f}s\u2013{s.get("end_sec", 0):.0f}s'
                    f'</span>'
                    for s in msg.get("sources", [])
                )
                st.markdown(
                    f'<div class="chat-ai">'
                    f'{msg["content"]}'
                    f'{"<br><br>" + sources_html if sources_html else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Job ID input for chat
        chat_job = st.text_input(
            "Job ID for chat",
            value=chat_job_value,
            key="chat_job_input",
        )

        # Chat input
        question = st.chat_input("Ask anything about this recording...")

        if question:
            if not chat_job:
                st.warning("Enter a Job ID above before asking a question.")
            else:
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": question,
                })
                try:
                    with st.spinner("Searching transcript..."):
                        res = requests.post(
                            f"{API}/query",
                            json={"question": question, "job_id": chat_job},
                            timeout=30,
                        )
                    if res.ok:
                        r = res.json()
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": r.get("answer", "No answer returned."),
                            "sources": r.get("sources", []),
                        })
                    else:
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": f"Request failed ({res.status_code}). Check that the job ID is correct and processing is complete.",
                            "sources": [],
                        })
                except requests.exceptions.ConnectionError:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "Cannot reach API server. Is uvicorn running?",
                        "sources": [],
                    })
                st.rerun()

        if st.session_state.chat_history:
            if st.button("Clear conversation"):
                st.session_state.chat_history = []
                st.rerun()

    with col_meta:
        st.caption("About the Chat")
        st.markdown(
            "Every answer is grounded in the actual transcript. "
            "The assistant retrieves the most relevant sections and "
            "answers only from them. If something was not said in the "
            "recording, it will say so."
        )

        st.divider()
        st.caption("Example questions")

        example_questions = [
            "What decisions were made?",
            "What did Speaker A say about the deadline?",
            "Summarize the key points in one paragraph.",
            "What action items were assigned?",
            "What questions were left unanswered?",
        ]

        for q in example_questions:
            # FIX: use st.session_state.job_id directly — no scope dependency
            if st.button(q, key=f"example_{q[:20]}", use_container_width=True):
                job = st.session_state.get("job_id")
                if not job:
                    st.warning("Process a file first to enable example questions.")
                else:
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": q,
                    })
                    st.rerun()
