"""
API endpoint tests for the RAG chatbot.

app.py mounts static files at module level, which breaks imports in a test
environment where ../frontend doesn't exist. This file builds a minimal test
app that mirrors only the API routes from app.py so no static-file path or
live ChromaDB instance is needed.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Minimal models (mirrors app.py)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class Source(BaseModel):
    label: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Test-app factory (mirrors app.py routes, no static files)
# ---------------------------------------------------------------------------

def create_test_app(rag) -> FastAPI:
    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        rag.session_manager.clear_session(session_id)
        return {"status": "cleared", "session_id": session_id}

    return app


@pytest.fixture
def api_client(mock_rag_system):
    return TestClient(create_test_app(mock_rag_system))


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

def test_query_returns_answer_and_sources(api_client, mock_rag_system):
    sources = [{"label": "Python Basics - Lesson 1", "url": "http://example.com/1"}]
    mock_rag_system.query.return_value = ("Great answer", sources)

    response = api_client.post("/api/query", json={"query": "What is RAG?", "session_id": "s1"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Great answer"
    assert data["sources"] == sources
    assert data["session_id"] == "s1"


def test_query_auto_creates_session_when_none_given(api_client, mock_rag_system):
    mock_rag_system.query.return_value = ("Answer", [])
    mock_rag_system.session_manager.create_session.return_value = "generated-id"

    response = api_client.post("/api/query", json={"query": "Q"})

    assert response.status_code == 200
    assert response.json()["session_id"] == "generated-id"
    mock_rag_system.session_manager.create_session.assert_called_once()


def test_query_uses_provided_session_id(api_client, mock_rag_system):
    mock_rag_system.query.return_value = ("Answer", [])

    response = api_client.post("/api/query", json={"query": "Q", "session_id": "existing"})

    assert response.status_code == 200
    assert response.json()["session_id"] == "existing"
    mock_rag_system.session_manager.create_session.assert_not_called()


def test_query_passes_query_and_session_to_rag(api_client, mock_rag_system):
    mock_rag_system.query.return_value = ("Answer", [])

    api_client.post("/api/query", json={"query": "Explain embeddings", "session_id": "sess-42"})

    mock_rag_system.query.assert_called_once_with("Explain embeddings", "sess-42")


def test_query_returns_empty_sources_list(api_client, mock_rag_system):
    mock_rag_system.query.return_value = ("Answer with no sources", [])

    response = api_client.post("/api/query", json={"query": "Q", "session_id": "s1"})

    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_query_returns_500_when_rag_raises(api_client, mock_rag_system):
    mock_rag_system.query.side_effect = RuntimeError("DB connection lost")

    response = api_client.post("/api/query", json={"query": "Q", "session_id": "s1"})

    assert response.status_code == 500
    assert "DB connection lost" in response.json()["detail"]


def test_query_requires_query_field(api_client):
    response = api_client.post("/api/query", json={})
    assert response.status_code == 422


def test_query_rejects_non_json_body(api_client):
    response = api_client.post("/api/query", content="not json", headers={"Content-Type": "text/plain"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

def test_courses_returns_course_stats(api_client, mock_rag_system):
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Python Basics", "ML Fundamentals", "Deep Learning"],
    }

    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 3
    assert data["course_titles"] == ["Python Basics", "ML Fundamentals", "Deep Learning"]


def test_courses_returns_empty_catalog(api_client, mock_rag_system):
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }

    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 0
    assert data["course_titles"] == []


def test_courses_calls_get_course_analytics(api_client, mock_rag_system):
    api_client.get("/api/courses")
    mock_rag_system.get_course_analytics.assert_called_once()


def test_courses_returns_500_on_analytics_error(api_client, mock_rag_system):
    mock_rag_system.get_course_analytics.side_effect = RuntimeError("Analytics unavailable")

    response = api_client.get("/api/courses")

    assert response.status_code == 500
    assert "Analytics unavailable" in response.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

def test_clear_session_returns_cleared_status(api_client, mock_rag_system):
    response = api_client.delete("/api/session/my-session")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cleared"
    assert data["session_id"] == "my-session"


def test_clear_session_calls_session_manager(api_client, mock_rag_system):
    api_client.delete("/api/session/abc-123")

    mock_rag_system.session_manager.clear_session.assert_called_once_with("abc-123")


def test_clear_session_echoes_session_id_from_path(api_client, mock_rag_system):
    response = api_client.delete("/api/session/unique-session-xyz")

    assert response.json()["session_id"] == "unique-session-xyz"
