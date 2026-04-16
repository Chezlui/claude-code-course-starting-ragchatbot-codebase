from vector_store import SearchResults


# ---------------------------------------------------------------------------
# Group A: Error path
# ---------------------------------------------------------------------------

def test_execute_returns_error_message(course_search_tool, mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=[], metadata=[], distances=[], error="Connection failed"
    )
    result = course_search_tool.execute(query="python basics")
    assert result == "Connection failed"
    mock_vector_store.search.assert_called_once_with(
        query="python basics", course_name=None, lesson_number=None
    )


# ---------------------------------------------------------------------------
# Group B: Empty results, no filters
# ---------------------------------------------------------------------------

def test_execute_empty_no_filters(course_search_tool, mock_vector_store):
    result = course_search_tool.execute(query="quantum physics")
    assert result == "No relevant content found."
    mock_vector_store.get_lesson_link.assert_not_called()


# ---------------------------------------------------------------------------
# Group C: Empty results with course_name filter
# ---------------------------------------------------------------------------

def test_execute_empty_with_course_name(course_search_tool, mock_vector_store):
    result = course_search_tool.execute(query="loops", course_name="Python Basics")
    assert result == "No relevant content found in course 'Python Basics'."
    mock_vector_store.search.assert_called_once_with(
        query="loops", course_name="Python Basics", lesson_number=None
    )


# ---------------------------------------------------------------------------
# Group D: Empty results with lesson_number filter
# ---------------------------------------------------------------------------

def test_execute_empty_with_lesson_number(course_search_tool, mock_vector_store):
    result = course_search_tool.execute(query="loops", lesson_number=3)
    assert result == "No relevant content found in lesson 3."


# ---------------------------------------------------------------------------
# Group E: Empty results with both filters
# ---------------------------------------------------------------------------

def test_execute_empty_with_both_filters(course_search_tool, mock_vector_store):
    result = course_search_tool.execute(
        query="loops", course_name="Python Basics", lesson_number=3
    )
    assert result == "No relevant content found in course 'Python Basics' in lesson 3."


# ---------------------------------------------------------------------------
# Group F: Success — header without lesson_number in metadata
# ---------------------------------------------------------------------------

def test_execute_header_without_lesson(course_search_tool, mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Content A"],
        metadata=[{"course_title": "AI Basics"}],
        distances=[0.1],
    )
    result = course_search_tool.execute(query="transformers")
    assert result == "[AI Basics]\nContent A"
    assert "Lesson" not in result
    mock_vector_store.get_lesson_link.assert_not_called()


# ---------------------------------------------------------------------------
# Group G: Success — header with lesson_number in metadata
# ---------------------------------------------------------------------------

def test_execute_header_with_lesson(course_search_tool, mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Content B"],
        metadata=[{"course_title": "AI Basics", "lesson_number": 2}],
        distances=[0.2],
    )
    mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"
    result = course_search_tool.execute(query="attention")
    assert result == "[AI Basics - Lesson 2]\nContent B"
    mock_vector_store.get_lesson_link.assert_called_once_with("AI Basics", 2)


# ---------------------------------------------------------------------------
# Group H: last_sources population
# ---------------------------------------------------------------------------

def test_execute_populates_last_sources_with_url(course_search_tool, mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Content B"],
        metadata=[{"course_title": "AI Basics", "lesson_number": 2}],
        distances=[0.2],
    )
    mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"
    course_search_tool.execute(query="attention")
    assert course_search_tool.last_sources == [
        {"label": "AI Basics - Lesson 2", "url": "https://example.com/lesson2"}
    ]


def test_execute_populates_last_sources_with_none_url(course_search_tool, mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Some content"],
        metadata=[{"course_title": "SomeCourse", "lesson_number": 5}],
        distances=[0.3],
    )
    mock_vector_store.get_lesson_link.return_value = None
    course_search_tool.execute(query="any")
    assert course_search_tool.last_sources == [
        {"label": "SomeCourse - Lesson 5", "url": None}
    ]


def test_execute_last_sources_label_without_lesson_when_no_lesson_number(
    course_search_tool, mock_vector_store
):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Doc content"],
        metadata=[{"course_title": "Intro Course"}],
        distances=[0.1],
    )
    course_search_tool.execute(query="any")
    assert course_search_tool.last_sources == [{"label": "Intro Course", "url": None}]
    assert "Lesson" not in course_search_tool.last_sources[0]["label"]


# ---------------------------------------------------------------------------
# Group I: Multi-result joining
# ---------------------------------------------------------------------------

def test_execute_joins_multiple_results_with_double_newline(
    course_search_tool, mock_vector_store
):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Doc A", "Doc B"],
        metadata=[
            {"course_title": "CourseX", "lesson_number": 1},
            {"course_title": "CourseY", "lesson_number": 2},
        ],
        distances=[0.1, 0.2],
    )
    mock_vector_store.get_lesson_link.return_value = None
    result = course_search_tool.execute(query="anything")
    assert result == "[CourseX - Lesson 1]\nDoc A\n\n[CourseY - Lesson 2]\nDoc B"
    assert len(course_search_tool.last_sources) == 2
