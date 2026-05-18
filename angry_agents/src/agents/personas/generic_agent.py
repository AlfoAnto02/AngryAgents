"""
Generic agent with full chat memory.
Every turn appends to the history and sends the whole conversation to Ollama,
so the model always has context of what was said before.
"""

import argparse
import sys
import time
from typing import Any

import requests

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"

SYSTEM_PROMPT = "You are a helpful assistant. Be concise."


def check_ollama(model: str) -> None:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        sys.exit("Error: Ollama not running. Start it with: ollama serve")

    available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
    if model not in available and model.split(":")[0] not in available:
        sys.exit(
            f"Error: model '{model}' not found in Ollama.\n"
            f"Available: {available}\n"
            f"Pull it with: ollama pull {model}"
        )


def chat(history: list[dict[str, Any]], model: str) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
        "options": {"temperature": 0.7},
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Stateful chat agent via Ollama.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    check_ollama(args.model)

    print(f"Model: {args.model}  |  Memory: full history  |  Type 'exit' to quit.")
    print()

    history: list[dict[str, Any]] = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        start = time.time()
        reply = chat(history, args.model)
        elapsed = time.time() - start

        history.append({"role": "assistant", "content": reply})

        print(f"\nAssistant ({elapsed:.2f}s):")
        print(reply)
        print()


if __name__ == "__main__":
    main()
