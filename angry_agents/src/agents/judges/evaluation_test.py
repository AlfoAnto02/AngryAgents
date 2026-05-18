"""
Run from the repo root:
    python -m angry_agents.src.agents.judges.evaluation_test
"""

import json
from pathlib import Path

from .general_judge import GeneralJudge
from .ideology_judge import IdeologyJudge
from .style_judge import StyleJudge

CHAT_FILE = Path(__file__).parent / "test_fake_chat.json"


def _print_result(judge_name: str, result) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {judge_name.upper()}")
    print(f"{'=' * 50}")
    for agent_score in result.scores:
        print(f"  {agent_score.author}  →  {agent_score.score}/5")
    print(f"\n  Predicted: {result.predicted}")


def main() -> None:
    chat = json.loads(CHAT_FILE.read_text(encoding="utf-8"))

    judges = [
        ("Style Judge",    StyleJudge()),
        ("Ideology Judge", IdeologyJudge()),
        ("General Judge",  GeneralJudge()),
    ]

    print(f"\nRunning persona_identification on {len(chat['messages'])} messages "
          f"from {len({m['author'] for m in chat['messages']})} agents...\n")

    for name, judge in judges:
        result = judge.persona_identification(chat)
        _print_result(name, result)

    print(f"\n{'=' * 50}\n")


if __name__ == "__main__":
    main()
