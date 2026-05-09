# Local Code Assistant

An interactive code-focused chat agent backed by a local [Ollama](https://ollama.com/) model.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) running locally (`ollama serve`)
- At least one model pulled, e.g. `ollama pull wizardcoder:7b-python`

```bash
pip install ollama
```

## Usage

Run from the VA-Claim-Checker project root:

```bash
python3 tools/local_agent/agent.py                                   # default model
python3 tools/local_agent/agent.py --model llama3                    # different model
python3 tools/local_agent/agent.py --load history.json               # resume a saved session
python3 tools/local_agent/agent.py --system "You are a bash expert"  # custom system prompt
```

Or run directly from this directory:

```bash
cd tools/local_agent
python3 agent.py
```

## In-session commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/reset` | Clear conversation history |
| `/model [name]` | Show or switch the active model |
| `/models` | List all locally available Ollama models |
| `/save [file]` | Save history to JSON (default: `history.json`) |
| `/load [file]` | Load history from JSON (default: `history.json`) |
| `quit` / `exit` | Exit |

**Multiline input:** press Enter on a blank line to enter multiline mode. End your submission with another blank line. Useful for pasting code blocks.

## Running tests

```bash
# From the VA-Claim-Checker project root:
python3 -m pytest tools/local_agent/test_agent.py -v

# Or from this directory:
python3 -m pytest test_agent.py -v
```

40 tests cover `trim`, `stream_reply`, `read_input`, `handle_command`, and `main`.
