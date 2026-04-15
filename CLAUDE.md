# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the application:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app is available at `http://localhost:8000` and API docs at `http://localhost:8000/docs`.

**Environment setup:** Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

No test suite exists in this project.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials. The backend is FastAPI, the frontend is plain HTML/JS/CSS served as static files from the same server.

**Request flow:**
1. Frontend sends `POST /api/query` with `{query, session_id}`
2. `app.py` routes to `RAGSystem.query()`
3. `RAGSystem` passes the query and session history to `AIGenerator`
4. `AIGenerator` calls Claude with tool definitions from `search_tools.py`
5. Claude invokes `CourseSearchTool` which queries `VectorStore` (ChromaDB)
6. `VectorStore` uses SentenceTransformer embeddings (`all-MiniLM-L6-v2`) for semantic search
7. Search results return as sources; Claude generates the final answer
8. Response `{answer, sources, session_id}` is returned to the frontend

**Key backend modules (`backend/`):**
- `rag_system.py` — top-level orchestrator; initializes all components and exposes `query()` and `add_course_document()`
- `ai_generator.py` — manages Claude API calls; uses tool-use loop with temperature=0, max_tokens=800
- `vector_store.py` — ChromaDB persistent client; stores chunks with course/lesson metadata
- `document_processor.py` — parses PDF/DOCX/TXT files, chunks at sentence boundaries (800 chars, 100 overlap), extracts course metadata
- `session_manager.py` — per-session conversation history, capped at `MAX_HISTORY * 2` messages
- `search_tools.py` — `CourseSearchTool` wraps vector search; supports filtering by course name and lesson number
- `models.py` — Pydantic models for `Course`, `Lesson`, `CourseChunk`, `QueryRequest`, `QueryResponse`
- `config.py` — all tunable constants (`CHUNK_SIZE`, `MAX_RESULTS`, model names, etc.)

**Document ingestion:** On startup, `app.py` calls `RAGSystem.add_course_folder("../docs")` to load all `.txt`/`.pdf`/`.docx` files. ChromaDB persists to `backend/chroma_db/` (gitignored).

**Frontend (`frontend/`):** Single-page app. `script.js` handles chat UI, session ID generation, and calls to the FastAPI backend. The frontend is served as `StaticFiles` mounted at `/` in `app.py`.
