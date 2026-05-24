"""
Build the ChromaDB index from all persona profiles in data/personas/.

Run once to populate the index, then again whenever profiles are added or updated.

Usage:
    python -m angry_agents.src.rag.build_index
"""

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from .indexer import index_profile

PERSONAS_DIR = Path(__file__).parents[3] / "data" / "personas"

# Profiles that share a persona_name with a newer version — excluded to avoid
# chunk ID collisions during upsert.
_EXCLUDED = {"jimmy_profile_old.json"}


def _load_profiles() -> list[dict]:
    profiles = []
    for path in sorted(PERSONAS_DIR.glob("*.json")):
        if path.name in _EXCLUDED:
            print(f"  skipping {path.name} (excluded)")
            continue
        profiles.append(json.loads(path.read_text(encoding="utf-8")))
    return profiles


def main() -> None:
    profiles = _load_profiles()
    print(f"Indexing {len(profiles)} profiles...\n")

    for profile in profiles:
        name = profile.get("persona_name", "unknown")
        print(f"  → {name}")
        index_profile(profile)

    print(f"\nDone. {len(profiles)} profiles indexed.")


if __name__ == "__main__":
    main()