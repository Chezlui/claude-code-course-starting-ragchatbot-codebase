from unittest.mock import patch, MagicMock
from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers: build mock Anthropic content blocks
# ---------------------------------------------------------------------------

def make_text_block(text):
    block = MagicMock()
    block.text = text
    block.type = "text"
    return block


def make_tool_use_block(name, input_dict, tool_id="tool_abc123"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_dict
    block.id = tool_id
    return block


def _make_response(stop_reason="end_turn", content_blocks=None, text="Hello"):
    response = MagicMock()
    response.stop_reason = stop_reason
    if content_blocks is not None:
        response.content = content_blocks
    else:
        response.content = [make_text_block(text)]
    return response


# ---------------------------------------------------------------------------
# Group A: Direct response, no tools
# ---------------------------------------------------------------------------

def test_direct_response_no_tools():
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response(
            stop_reason="end_turn", text="Direct answer"
        )
        generator = AIGenerator(api_key="test", model="claude-test")
        result = generator.generate_response(query="What is RAG?")

    assert result == "Direct answer"
    assert mock_client.messages.create.call_count == 1
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


def test_system_prompt_includes_history():
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response(stop_reason="end_turn")
        generator = AIGenerator(api_key="test", model="claude-test")
        generator.generate_response(query="Q", conversation_history="User: Hi")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert AIGenerator.SYSTEM_PROMPT in call_kwargs["system"]
    assert "Previous conversation:\nUser: Hi" in call_kwargs["system"]


def test_system_prompt_without_history():
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response(stop_reason="end_turn")
        generator = AIGenerator(api_key="test", model="claude-test")
        generator.generate_response(query="Q")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["system"] == AIGenerator.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Group B: Direct response even when tools provided (stop_reason = end_turn)
# ---------------------------------------------------------------------------

def test_end_turn_with_tools_provided():
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response(
            stop_reason="end_turn", text="No tool needed"
        )
        mock_tm = MagicMock()
        generator = AIGenerator(api_key="test", model="claude-test")
        result = generator.generate_response(
            query="Q",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tm,
        )

    assert result == "No tool needed"
    assert mock_client.messages.create.call_count == 1
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" in call_kwargs
    assert "tool_choice" in call_kwargs
    mock_tm.execute_tool.assert_not_called()


# ---------------------------------------------------------------------------
# Group C: Tool-use path
# ---------------------------------------------------------------------------

def test_tool_use_calls_execute_tool():
    first_response = _make_response(
        stop_reason="tool_use",
        content_blocks=[
            make_tool_use_block("search_course_content", {"query": "python loops"}, "id_001")
        ],
    )
    second_response = _make_response(stop_reason="end_turn", text="Final answer after tool")

    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "tool result text"
        generator = AIGenerator(api_key="test", model="claude-test")
        result = generator.generate_response(
            query="python loops?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tm,
        )

    mock_tm.execute_tool.assert_called_once_with(
        "search_course_content", query="python loops"
    )
    assert result == "Final answer after tool"


def test_tool_use_message_structure():
    tool_block = make_tool_use_block(
        "search_course_content", {"query": "python loops"}, "id_001"
    )
    first_response = _make_response(
        stop_reason="tool_use", content_blocks=[tool_block]
    )
    second_response = _make_response(stop_reason="end_turn", text="Done")

    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "tool result text"
        generator = AIGenerator(api_key="test", model="claude-test")
        generator.generate_response(
            query="python loops?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tm,
        )

    # Inspect the messages sent in the second API call
    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]
    assert messages[0] == {"role": "user", "content": "python loops?"}
    assert messages[1] == {"role": "assistant", "content": first_response.content}
    assert messages[2] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "id_001",
                "content": "tool result text",
            }
        ],
    }


def test_final_api_call_has_no_tools_key():
    first_response = _make_response(
        stop_reason="tool_use",
        content_blocks=[make_tool_use_block("search_course_content", {"query": "x"})],
    )
    second_response = _make_response(stop_reason="end_turn", text="Done")

    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        generator = AIGenerator(api_key="test", model="claude-test")
        generator.generate_response(
            query="Q", tools=[{"name": "search_course_content"}], tool_manager=mock_tm
        )

    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    assert "tools" not in second_call_kwargs
    assert "tool_choice" not in second_call_kwargs


def test_final_api_call_preserves_system_prompt():
    first_response = _make_response(
        stop_reason="tool_use",
        content_blocks=[make_tool_use_block("search_course_content", {"query": "x"})],
    )
    second_response = _make_response(stop_reason="end_turn", text="Done")

    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        generator = AIGenerator(api_key="test", model="claude-test")
        generator.generate_response(
            query="Q",
            conversation_history="User: prior message",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tm,
        )

    first_call_kwargs = mock_client.messages.create.call_args_list[0][1]
    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    assert second_call_kwargs["system"] == first_call_kwargs["system"]


def test_multiple_tool_calls_all_executed():
    block1 = make_tool_use_block("search_course_content", {"query": "A"}, "id_1")
    block2 = make_tool_use_block("search_course_content", {"query": "B"}, "id_2")
    first_response = _make_response(
        stop_reason="tool_use", content_blocks=[block1, block2]
    )
    second_response = _make_response(stop_reason="end_turn", text="Combined answer")

    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        generator = AIGenerator(api_key="test", model="claude-test")
        generator.generate_response(
            query="Q", tools=[{"name": "search_course_content"}], tool_manager=mock_tm
        )

    assert mock_tm.execute_tool.call_count == 2
    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    tool_results_msg = second_call_kwargs["messages"][2]
    tool_results = tool_results_msg["content"]
    assert len(tool_results) == 2
    assert tool_results[0]["tool_use_id"] == "id_1"
    assert tool_results[1]["tool_use_id"] == "id_2"


def test_generate_response_returns_final_text_not_intermediate():
    first_response = _make_response(
        stop_reason="tool_use",
        content_blocks=[make_tool_use_block("search_course_content", {"query": "x"})],
    )
    second_response = _make_response(
        stop_reason="end_turn", text="Final synthesized answer"
    )

    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"
        generator = AIGenerator(api_key="test", model="claude-test")
        result = generator.generate_response(
            query="Q", tools=[{"name": "search_course_content"}], tool_manager=mock_tm
        )

    assert result == "Final synthesized answer"
