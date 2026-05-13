"""
Generic output quality judge.

Reads a file, scores its content 1-5, and appends the result to a CSV.

Usage:
    python -m angry_agents.src.agents.judges.generic_judge path/to/file.txt
    python -m angry_agents.src.agents.judges.generic_judge path/to/file.txt --model mistral
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "mistral"
OUTPUT_DIR = Path(__file__).parent.parent / "judge_output"

SYSTEM_PROMPT = """\
You are a rigorous output quality evaluator. Be concise and objective.\
"""

JUDGE_PROMPT = """\
Evaluate the quality of the following content.

--- CONTENT ---
{content}

Score it on a 1–5 integer scale:
  1 = very poor  2 = poor  3 = acceptable  4 = good  5 = excellent

Reply with exactly two lines:
Line 1: the integer score (nothing else)
Line 2: one sentence explaining why
"""


def check_ollama(model: str) -> None:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        sys.exit("Error: Ollama not running. Start it with: ollama serve")

    available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
    if model not in available and model.split(":")[0] not in available:
        sys.exit(
            f"Error: model '{model}' not found.\nAvailable: {available}\nPull with: ollama pull {model}"
        )


def judge(content: str, model: str) -> tuple[int, str]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": JUDGE_PROMPT.format(content=content)},
        ],
        "options": {"temperature": 0.1, "num_predict": 128},
    }

    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()

    lines = resp.json()["message"]["content"].strip().splitlines()
    if len(lines) < 2:
        raise ValueError(f"Unexpected model output: {lines}")

    score = int(lines[0].strip())
    if score not in range(1, 6):
        raise ValueError(f"Score out of range: {score}")

    reason = lines[1].strip()
    return score, reason


def save_csv(file_path: Path, score: int, reason: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "evaluations.csv"
    write_header = not csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "file", "score", "reason"])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            str(file_path),
            score,
            reason,
        ])

    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a file's content 1-5 via Ollama.")
    parser.add_argument("file", type=Path, help="Path to the file to evaluate")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    if not args.file.exists():
        sys.exit(f"Error: file not found: {args.file}")

    check_ollama(args.model)

    content = args.file.read_text(encoding="utf-8")
    score, reason = judge(content, args.model)

    csv_path = save_csv(args.file, score, reason)

    print(f"Score: {score}/5")
    print(f"Reason: {reason}")
    print(f"Saved → {csv_path}")


if __name__ == "__main__":
    main()
