from unittest.mock import patch, MagicMock, call
import pytest
from config import Config
from rag_system import RAGSystem


@pytest.fixture
def fake_config():
    return Config(
        ANTHROPIC_API_KEY="test-key",
        ANTHROPIC_MODEL="claude-test",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        MAX_RESULTS=5,
        MAX_HISTORY=2,
        CHROMA_PATH="/tmp/test_chroma",
    )


@pytest.fixture
def rag_system(fake_config, mock_ai_generator, mock_tool_manager, mock_session_manager):
    with patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator", return_value=mock_ai_generator), \
         patch("rag_system.SessionManager", return_value=mock_session_manager), \
         patch("rag_system.ToolManager", return_value=mock_tool_manager), \
         patch("rag_system.CourseSearchTool"), \
         patch("rag_system.CourseOutlineTool"):
        system = RAGSystem(config=fake_config)
        system.ai_generator = mock_ai_generator
        system.session_manager = mock_session_manager
        system.tool_manager = mock_tool_manager
    return system


# ---------------------------------------------------------------------------
# Group A: Return value shape
# ---------------------------------------------------------------------------

def test_query_returns_tuple(rag_system, mock_ai_generator, mock_tool_manager):
    mock_ai_generator.generate_response.return_value = "AI response"
    mock_tool_manager.get_last_sources.return_value = []
    result = rag_system.query("What is a transformer?")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] == "AI response"
    assert result[1] == []


# ---------------------------------------------------------------------------
# Group B: Sources come from tool_manager
# ---------------------------------------------------------------------------

def test_sources_come_from_tool_manager(rag_system, mock_tool_manager):
    sources = [{"label": "CourseA - Lesson 1", "url": "http://x"}]
    mock_tool_manager.get_last_sources.return_value = sources
    result = rag_system.query("anything")
    assert result[1] == sources
    assert mock_tool_manager.get_last_sources.call_count == 1


# ---------------------------------------------------------------------------
# Group C: Sources reset after query
# ---------------------------------------------------------------------------

def test_reset_sources_called_after_retrieval(rag_system, mock_tool_manager):
    rag_system.query("test")
    assert mock_tool_manager.reset_sources.called
    # Verify ordering: get_last_sources before reset_sources
    method_names = [c[0] for c in mock_tool_manager.method_calls]
    get_idx = next(i for i, n in enumerate(method_names) if n == "get_last_sources")
    reset_idx = next(i for i, n in enumerate(method_names) if n == "reset_sources")
    assert get_idx < reset_idx


# ---------------------------------------------------------------------------
# Group D: Session handling — with session_id
# ---------------------------------------------------------------------------

def test_session_history_fetched_when_session_id_given(
    rag_system, mock_ai_generator, mock_session_manager
):
    mock_session_manager.get_conversation_history.return_value = (
        "User: Hi\nAssistant: Hello"
    )
    rag_system.query("follow-up", session_id="session_1")
    mock_session_manager.get_conversation_history.assert_called_once_with("session_1")
    call_kwargs = mock_ai_generator.generate_response.call_args[1]
    assert call_kwargs["conversation_history"] == "User: Hi\nAssistant: Hello"


def test_add_exchange_called_with_session_id(
    rag_system, mock_ai_generator, mock_session_manager
):
    mock_ai_generator.generate_response.return_value = "The answer"
    rag_system.query("My question", session_id="session_1")
    mock_session_manager.add_exchange.assert_called_once_with(
        "session_1", "My question", "The answer"
    )


# ---------------------------------------------------------------------------
# Group E: Query without session_id
# ---------------------------------------------------------------------------

def test_no_session_manager_calls_without_session_id(
    rag_system, mock_ai_generator, mock_session_manager
):
    rag_system.query("standalone question")
    mock_session_manager.get_conversation_history.assert_not_called()
    mock_session_manager.add_exchange.assert_not_called()
    call_kwargs = mock_ai_generator.generate_response.call_args[1]
    assert call_kwargs["conversation_history"] is None


# ---------------------------------------------------------------------------
# Group F: Prompt wrapping
# ---------------------------------------------------------------------------

def test_query_wraps_in_prompt_template(rag_system, mock_ai_generator):
    rag_system.query("What is embeddings?")
    call_kwargs = mock_ai_generator.generate_response.call_args[1]
    assert call_kwargs["query"] == (
        "Answer this question about course materials: What is embeddings?"
    )


def test_add_exchange_receives_original_query_not_prompt(
    rag_system, mock_session_manager
):
    rag_system.query("original question", session_id="s1")
    args = mock_session_manager.add_exchange.call_args[0]
    # args: (session_id, query, response)
    assert args[1] == "original question"
    assert "Answer this question" not in args[1]


# ---------------------------------------------------------------------------
# Group G: Tools passed to ai_generator
# ---------------------------------------------------------------------------

def test_tool_definitions_passed_to_generate_response(
    rag_system, mock_ai_generator, mock_tool_manager
):
    tool_defs = [
        {"name": "search_course_content"},
        {"name": "get_course_outline"},
    ]
    mock_tool_manager.get_tool_definitions.return_value = tool_defs
    rag_system.query("anything")
    call_kwargs = mock_ai_generator.generate_response.call_args[1]
    assert call_kwargs["tools"] == tool_defs
    assert call_kwargs["tool_manager"] is rag_system.tool_manager
