#!/usr/bin/env python3
"""Code assistant agent backed by a local Ollama model."""

import argparse
import json
import sys
from pathlib import Path

import ollama

DEFAULT_MODEL = "wizardcoder:7b-python"
DEFAULT_SYSTEM = (
    "You are an expert programming assistant. "
    "When asked to write or fix code, provide clean, working solutions with brief explanations. "
    "Default to Python unless another language is requested."
)
MAX_MESSAGES = 20

HELP = """\
Commands:
  /help           Show this message
  /reset          Clear conversation history
  /model [name]   Show or switch the active Ollama model
  /models         List all locally available Ollama models
  /save [file]    Save history to JSON (default: history.json)
  /load [file]    Load history from JSON (default: history.json)
  quit / exit     Exit

Multiline input:
  Press Enter on a blank line to enter multiline mode.
  End submission with another blank line.

CLI flags (at startup):
  --model <name>    Ollama model to use (default: wizardcoder:7b-python)
  --system <text>   Override the system prompt
  --load <file>     Load conversation history from a JSON file\
"""


def trim(history: list[dict], system: dict) -> list[dict]:
    non_system = [m for m in history if m["role"] != "system"]
    return [system] + non_system[-MAX_MESSAGES:]


def stream_reply(history: list[dict], model: str) -> str:
    try:
        response = ollama.chat(model=model, messages=history, stream=True)
        chunks = []
        for chunk in response:
            token = chunk["message"].get("content", "")
            if token:
                print(token, end="", flush=True)
                chunks.append(token)
        print()
        return "".join(chunks)
    except ollama.ResponseError as e:
        print(f"\n[Error] Ollama: {e.error}")
        return ""
    except Exception as e:
        msg = str(e).lower()
        if "connect" in msg or "refused" in msg:
            print("\n[Error] Cannot reach Ollama — is it running? (run: ollama serve)")
        else:
            print(f"\n[Error] {e}")
        return ""


def read_input(prompt: str) -> str:
    line = input(prompt)
    if line:
        return line
    print("(multiline mode — blank line to submit)")
    lines = []
    while True:
        try:
            part = input("... ")
        except (EOFError, KeyboardInterrupt):
            break
        if part == "" and lines:
            break
        lines.append(part)
    return "\n".join(lines)


def handle_command(
    cmd: str, args: str, model: str, history: list[dict], system: dict
) -> tuple[str, list[dict]]:
    if cmd == "/help":
        print(HELP)

    elif cmd == "/reset":
        history = [system]
        print("[History cleared]")

    elif cmd == "/models":
        try:
            result = ollama.list()
            for m in result.models:
                print(f"  {m.model}")
        except Exception as e:
            print(f"[Error] {e}")

    elif cmd == "/model":
        if not args:
            print(f"Current model: {model}")
        else:
            model = args.strip()
            print(f"[Switched to {model}]")

    elif cmd == "/save":
        path = Path(args.strip() or "history.json")
        msgs = [m for m in history if m["role"] != "system"]
        path.write_text(json.dumps(msgs, indent=2))
        print(f"[Saved {len(msgs)} messages to {path}]")

    elif cmd == "/load":
        path = Path(args.strip() or "history.json")
        if not path.exists():
            print(f"[File not found: {path}]")
        else:
            msgs = json.loads(path.read_text())
            history = [system] + msgs
            print(f"[Loaded {len(msgs)} messages from {path}]")

    else:
        print(f"[Unknown command: {cmd} — type /help for available commands]")

    return model, history


def main() -> None:
    parser = argparse.ArgumentParser(description="Local code assistant via Ollama")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--system", default=DEFAULT_SYSTEM, help="System prompt")
    parser.add_argument("--load", metavar="FILE", help="Load conversation history from JSON")
    cli = parser.parse_args()

    model = cli.model
    system: dict = {"role": "system", "content": cli.system}
    history: list[dict] = [system]

    if cli.load:
        path = Path(cli.load)
        if path.exists():
            msgs = json.loads(path.read_text())
            history = [system] + msgs
            print(f"[Loaded {len(msgs)} messages from {path}]")
        else:
            print(f"[Warning] File not found: {path}")

    print(f"Code assistant ({model}) — /help for commands, quit to exit.\n")

    while True:
        try:
            user_input = read_input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            sys.exit(0)

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            sys.exit(0)

        if user_input.startswith("/"):
            parts = user_input.split(None, 1)
            model, history = handle_command(
                parts[0], parts[1] if len(parts) > 1 else "", model, history, system
            )
            continue

        history.append({"role": "user", "content": user_input})
        history = trim(history, system)

        print("Assistant: ", end="", flush=True)
        reply = stream_reply(history, model)
        if reply:
            history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
