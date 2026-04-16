import sys
import os
from unittest.mock import MagicMock
import pytest

# Insert backend/ at the front of sys.path so bare imports like
# "from vector_store import VectorStore" resolve correctly.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from vector_store import SearchResults
from search_tools import CourseSearchTool


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
    store.get_lesson_link.return_value = None
    return store


@pytest.fixture
def course_search_tool(mock_vector_store):
    return CourseSearchTool(vector_store=mock_vector_store)


@pytest.fixture
def make_mock_response():
    def _make(stop_reason="end_turn", text="Hello", content_blocks=None):
        response = MagicMock()
        response.stop_reason = stop_reason
        if content_blocks is not None:
            response.content = content_blocks
        else:
            block = MagicMock()
            block.text = text
            response.content = [block]
        return response
    return _make


@pytest.fixture
def mock_tool_manager():
    tm = MagicMock()
    tm.get_tool_definitions.return_value = [{"name": "search_course_content"}]
    tm.get_last_sources.return_value = []
    return tm


@pytest.fixture
def mock_ai_generator():
    gen = MagicMock()
    gen.generate_response.return_value = "mocked AI answer"
    return gen


@pytest.fixture
def mock_session_manager():
    sm = MagicMock()
    sm.get_conversation_history.return_value = None
    return sm
