"""Unit tests for agent.py."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import ollama
import pytest

import agent
from agent import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM,
    MAX_MESSAGES,
    handle_command,
    read_input,
    stream_reply,
    trim,
)

SYSTEM = {"role": "system", "content": DEFAULT_SYSTEM}


# ---------------------------------------------------------------------------
# trim
# ---------------------------------------------------------------------------


def test_trim_empty_history_returns_system_only():
    assert trim([SYSTEM], SYSTEM) == [SYSTEM]


def test_trim_under_limit_unchanged():
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    history = [SYSTEM] + msgs
    assert trim(history, SYSTEM) == history


def test_trim_drops_oldest_over_limit():
    msgs = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": str(i)}
        for i in range(MAX_MESSAGES + 4)
    ]
    history = [SYSTEM] + msgs
    result = trim(history, SYSTEM)
    assert result[0] == SYSTEM
    assert len(result) == MAX_MESSAGES + 1
    assert result[1:] == msgs[-MAX_MESSAGES:]


def test_trim_system_always_at_index_zero():
    msgs = [{"role": "user", "content": str(i)} for i in range(MAX_MESSAGES + 10)]
    result = trim([SYSTEM] + msgs, SYSTEM)
    assert result[0] == SYSTEM


def test_trim_excludes_system_from_window_count():
    msgs = [{"role": "user", "content": str(i)} for i in range(MAX_MESSAGES)]
    history = [SYSTEM] + msgs
    result = trim(history, SYSTEM)
    assert len(result) == MAX_MESSAGES + 1


# ---------------------------------------------------------------------------
# stream_reply
# ---------------------------------------------------------------------------


def _chunk(content):
    return {"message": {"content": content}}


def _done_chunk():
    return {"message": {}}


@patch("agent.ollama.chat")
def test_stream_reply_returns_concatenated_text(mock_chat, capsys):
    mock_chat.return_value = [_chunk("hello "), _chunk("world"), _done_chunk()]
    result = stream_reply([SYSTEM], DEFAULT_MODEL)
    assert result == "hello world"


@patch("agent.ollama.chat")
def test_stream_reply_skips_empty_tokens(mock_chat):
    mock_chat.return_value = [_chunk(""), _chunk("hi"), _done_chunk()]
    result = stream_reply([SYSTEM], DEFAULT_MODEL)
    assert result == "hi"


@patch("agent.ollama.chat")
def test_stream_reply_ollama_response_error(mock_chat, capsys):
    mock_chat.side_effect = ollama.ResponseError("model not found", 404)
    result = stream_reply([SYSTEM], DEFAULT_MODEL)
    assert result == ""
    assert "Error" in capsys.readouterr().out


@patch("agent.ollama.chat")
def test_stream_reply_connection_refused(mock_chat, capsys):
    mock_chat.side_effect = Exception("Connection refused")
    result = stream_reply([SYSTEM], DEFAULT_MODEL)
    assert result == ""
    assert "ollama serve" in capsys.readouterr().out


@patch("agent.ollama.chat")
def test_stream_reply_unknown_exception(mock_chat, capsys):
    mock_chat.side_effect = Exception("something unexpected")
    result = stream_reply([SYSTEM], DEFAULT_MODEL)
    assert result == ""
    out = capsys.readouterr().out
    assert "Error" in out
    assert "ollama serve" not in out


@patch("agent.ollama.chat")
def test_stream_reply_passes_model_and_history(mock_chat):
    mock_chat.return_value = [_done_chunk()]
    history = [SYSTEM, {"role": "user", "content": "hi"}]
    stream_reply(history, "mymodel")
    mock_chat.assert_called_once_with(model="mymodel", messages=history, stream=True)


# ---------------------------------------------------------------------------
# read_input
# ---------------------------------------------------------------------------


@patch("builtins.input", return_value="hello world")
def test_read_input_single_line(mock_input):
    assert read_input("You: ") == "hello world"
    mock_input.assert_called_once_with("You: ")


@patch("builtins.input", side_effect=["", "line one", "line two", ""])
def test_read_input_multiline_blank_line_submits(mock_input, capsys):
    result = read_input("You: ")
    assert result == "line one\nline two"
    assert "multiline" in capsys.readouterr().out


@patch("builtins.input", side_effect=["", "only line", EOFError])
def test_read_input_multiline_eof_submits(mock_input):
    result = read_input("You: ")
    assert result == "only line"


@patch("builtins.input", side_effect=["", "only line", KeyboardInterrupt])
def test_read_input_multiline_interrupt_submits(mock_input):
    result = read_input("You: ")
    assert result == "only line"


@patch("builtins.input", side_effect=["", ""])
def test_read_input_multiline_blank_before_any_content_keeps_reading(mock_input):
    # blank line with no prior lines should not submit; loop continues
    # second call also blank — with no lines collected, it loops again
    # third call raises EOFError to break
    with patch("builtins.input", side_effect=["", "", EOFError]):
        result = read_input("You: ")
    assert result == ""


# ---------------------------------------------------------------------------
# handle_command — /help
# ---------------------------------------------------------------------------


def test_handle_command_help_prints_help(capsys):
    handle_command("/help", "", "model", [SYSTEM], SYSTEM)
    assert "/reset" in capsys.readouterr().out


def test_handle_command_help_returns_unchanged(capsys):
    model, history = handle_command("/help", "", "mymodel", [SYSTEM], SYSTEM)
    assert model == "mymodel"
    assert history == [SYSTEM]


# ---------------------------------------------------------------------------
# handle_command — /reset
# ---------------------------------------------------------------------------


def test_handle_command_reset_clears_history(capsys):
    history = [SYSTEM, {"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
    _, new_history = handle_command("/reset", "", "model", history, SYSTEM)
    assert new_history == [SYSTEM]


def test_handle_command_reset_preserves_model(capsys):
    model, _ = handle_command("/reset", "", "mymodel", [SYSTEM], SYSTEM)
    assert model == "mymodel"


# ---------------------------------------------------------------------------
# handle_command — /model
# ---------------------------------------------------------------------------


def test_handle_command_model_no_args_prints_current(capsys):
    handle_command("/model", "", "wizardcoder:7b-python", [SYSTEM], SYSTEM)
    assert "wizardcoder:7b-python" in capsys.readouterr().out


def test_handle_command_model_with_arg_switches(capsys):
    model, _ = handle_command("/model", "llama3", "old", [SYSTEM], SYSTEM)
    assert model == "llama3"


def test_handle_command_model_strips_whitespace(capsys):
    model, _ = handle_command("/model", "  llama3  ", "old", [SYSTEM], SYSTEM)
    assert model == "llama3"


# ---------------------------------------------------------------------------
# handle_command — /models
# ---------------------------------------------------------------------------


@patch("agent.ollama.list")
def test_handle_command_models_lists_names(mock_list, capsys):
    m1, m2 = MagicMock(), MagicMock()
    m1.model = "wizardcoder:7b-python"
    m2.model = "llama3"
    mock_list.return_value = MagicMock(models=[m1, m2])
    handle_command("/models", "", "model", [SYSTEM], SYSTEM)
    out = capsys.readouterr().out
    assert "wizardcoder:7b-python" in out
    assert "llama3" in out


@patch("agent.ollama.list", side_effect=Exception("connection refused"))
def test_handle_command_models_error(mock_list, capsys):
    handle_command("/models", "", "model", [SYSTEM], SYSTEM)
    assert "Error" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# handle_command — /save
# ---------------------------------------------------------------------------


def test_handle_command_save_writes_json(tmp_path, capsys):
    path = tmp_path / "history.json"
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    handle_command("/save", str(path), "model", [SYSTEM] + msgs, SYSTEM)
    data = json.loads(path.read_text())
    assert data == msgs


def test_handle_command_save_excludes_system(tmp_path, capsys):
    path = tmp_path / "history.json"
    handle_command("/save", str(path), "model", [SYSTEM], SYSTEM)
    assert json.loads(path.read_text()) == []


def test_handle_command_save_default_filename(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    handle_command("/save", "", "model", [SYSTEM], SYSTEM)
    assert (tmp_path / "history.json").exists()


# ---------------------------------------------------------------------------
# handle_command — /load
# ---------------------------------------------------------------------------


def test_handle_command_load_restores_history(tmp_path, capsys):
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    path = tmp_path / "history.json"
    path.write_text(json.dumps(msgs))
    _, history = handle_command("/load", str(path), "model", [SYSTEM], SYSTEM)
    assert history == [SYSTEM] + msgs


def test_handle_command_load_missing_file(capsys):
    _, history = handle_command("/load", "/nonexistent/path.json", "model", [SYSTEM], SYSTEM)
    assert "not found" in capsys.readouterr().out
    assert history == [SYSTEM]


def test_handle_command_load_default_filename(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    msgs = [{"role": "user", "content": "test"}]
    (tmp_path / "history.json").write_text(json.dumps(msgs))
    _, history = handle_command("/load", "", "model", [SYSTEM], SYSTEM)
    assert history == [SYSTEM] + msgs


# ---------------------------------------------------------------------------
# handle_command — unknown command
# ---------------------------------------------------------------------------


def test_handle_command_unknown_prints_message(capsys):
    handle_command("/foo", "", "model", [SYSTEM], SYSTEM)
    assert "Unknown" in capsys.readouterr().out


def test_handle_command_unknown_returns_unchanged():
    model, history = handle_command("/foo", "", "mymodel", [SYSTEM], SYSTEM)
    assert model == "mymodel"
    assert history == [SYSTEM]


# ---------------------------------------------------------------------------
# main — CLI arg parsing and startup behaviour
# ---------------------------------------------------------------------------


def _make_stream(tokens):
    return [_chunk(t) for t in tokens] + [_done_chunk()]


@patch("agent.ollama.chat")
@patch("agent.read_input", side_effect=["quit"])
def test_main_default_model(mock_input, mock_chat, capsys):
    with patch("sys.argv", ["agent.py"]):
        with pytest.raises(SystemExit):
            agent.main()
    assert DEFAULT_MODEL in capsys.readouterr().out


@patch("agent.ollama.chat")
@patch("agent.read_input", side_effect=["quit"])
def test_main_custom_model_flag(mock_input, mock_chat, capsys):
    with patch("sys.argv", ["agent.py", "--model", "llama3"]):
        with pytest.raises(SystemExit):
            agent.main()
    assert "llama3" in capsys.readouterr().out


@patch("agent.ollama.chat")
@patch("agent.read_input", side_effect=["quit"])
def test_main_load_flag_restores_history(mock_input, mock_chat, tmp_path, capsys):
    msgs = [{"role": "user", "content": "prior"}]
    path = tmp_path / "h.json"
    path.write_text(json.dumps(msgs))
    with patch("sys.argv", ["agent.py", "--load", str(path)]):
        with pytest.raises(SystemExit):
            agent.main()
    assert "Loaded" in capsys.readouterr().out


@patch("agent.ollama.chat")
@patch("agent.read_input", side_effect=["quit"])
def test_main_load_flag_missing_file_warns(mock_input, mock_chat, capsys):
    with patch("sys.argv", ["agent.py", "--load", "/no/such/file.json"]):
        with pytest.raises(SystemExit):
            agent.main()
    assert "Warning" in capsys.readouterr().out


@patch("agent.stream_reply", return_value="def hello(): pass")
@patch("agent.read_input", side_effect=["write hello world", "quit"])
def test_main_sends_user_message_and_records_reply(mock_input, mock_reply):
    with patch("sys.argv", ["agent.py"]):
        with pytest.raises(SystemExit):
            agent.main()
    mock_reply.assert_called_once()
    history_sent = mock_reply.call_args[0][0]
    assert any(m["content"] == "write hello world" for m in history_sent)


@patch("agent.stream_reply", return_value="")
@patch("agent.read_input", side_effect=["ask something", "quit"])
def test_main_empty_reply_not_appended(mock_input, mock_reply):
    with patch("sys.argv", ["agent.py"]):
        with pytest.raises(SystemExit):
            agent.main()
    history_sent = mock_reply.call_args[0][0]
    assert not any(m.get("role") == "assistant" for m in history_sent)


@patch("agent.read_input", side_effect=KeyboardInterrupt)
def test_main_keyboard_interrupt_exits(mock_input, capsys):
    with patch("sys.argv", ["agent.py"]):
        with pytest.raises(SystemExit):
            agent.main()
    assert "Bye" in capsys.readouterr().out
