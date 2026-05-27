"""
Fix generic do_not_say entries in persona profile JSONs.

Identifies duplicate do_not_say lines shared across 2+ profiles and
regenerates persona-specific replacements using the configured LLM backend.

Each profile is processed in a single LLM call (batch of its bad entries),
so the total number of API calls equals the number of affected profiles.

Usage:
    # Dry-run: print what would change, write nothing
    python -m angry_agents.src.rag.fix_do_not_say --dry-run

    # Live: rewrite profile JSONs in place
    python -m angry_agents.src.rag.fix_do_not_say

    # Process only specific personas
    python -m angry_agents.src.rag.fix_do_not_say --only "Walter White" "Joker"

Run build_index again afterwards to reindex the updated chunks.
"""

import argparse
import collections
import json
import pathlib
import sys
import time

# --- path bootstrap so the module works when run directly ---------------------
_ROOT = pathlib.Path(__file__).parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from angry_agents.src.agents.agent_config import llm_call, DEFAULT_MODEL  # noqa: E402

PERSONAS_DIR = _ROOT / "data" / "personas"
EXCLUDED = {"jimmy_profile_old.json"}

# ── Prompt ─────────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are a persona analyst generating negative speech fingerprints.

A do_not_say entry contains two fields:
  "line"       — an exact phrase this persona would NEVER utter
  "contradicts" — the specific character trait, story arc, or identity aspect that makes
                  saying this line impossible for this persona

Rules for a GOOD entry:
  1. UNIQUE to this persona — something that could not appear in another character's list
  2. CHARACTER-SPECIFIC — references their unique narrative arc, catchphrase denial, or core identity
  3. NOT GENERIC — must NOT be a generic competitive/modest/social statement that any person
     with drive or teamwork could say (e.g. "Winning isn't everything" is bad — too generic)
  4. CREDIBLE — if someone read this line, they should immediately recognise the character

Return ONLY a JSON array of replacement objects, one per requested replacement, in order.
No markdown, no extra keys, no explanation outside the JSON.

Shape:
[
  {"line": "...", "contradicts": "..."},
  ...
]
"""

_USER_TEMPLATE = """\
Persona: {name}
Source: {source}

--- FULL PROFILE ---
{profile_json}

--- ENTRIES TO REPLACE (return exactly {n} replacements, in order) ---
{entries_to_replace}

--- ENTRIES TO KEEP (do NOT generate anything semantically similar to these) ---
{entries_to_keep}

Generate {n} replacement do_not_say entries that are uniquely specific to {name}.
Each must reference a concrete, recognisable trait from the profile above.
Return a JSON array of exactly {n} objects with keys "line" and "contradicts".
"""


# ── Core logic ─────────────────────────────────────────────────────────────────

def _load_profiles() -> dict[str, tuple[pathlib.Path, dict]]:
    """Return {persona_name: (path, profile_dict)} for all non-excluded profiles."""
    result: dict[str, tuple[pathlib.Path, dict]] = {}
    for path in sorted(PERSONAS_DIR.glob("*.json")):
        if path.name in EXCLUDED:
            continue
        p = json.loads(path.read_text(encoding="utf-8"))
        result[p["persona_name"]] = (path, p)
    return result


def _build_freq_table(profiles: dict) -> collections.Counter:
    """Count how many profiles each do_not_say line appears in."""
    freq: collections.Counter = collections.Counter()
    for _, p in profiles.values():
        for d in p.get("do_not_say") or []:
            line = d.get("line", str(d)) if isinstance(d, dict) else str(d)
            freq[line.strip()] += 1
    return freq


def _find_bad_indices(profile: dict, freq: collections.Counter) -> list[int]:
    """Return indices of do_not_say entries that are shared with other profiles."""
    bad = []
    for i, d in enumerate(profile.get("do_not_say") or []):
        line = d.get("line", str(d)) if isinstance(d, dict) else str(d)
        if freq[line.strip()] > 1:
            bad.append(i)
    return bad


def _call_llm_for_replacements(
    name: str,
    profile: dict,
    bad_indices: list[int],
) -> list[dict]:
    """
    Call the LLM to regenerate bad do_not_say entries.
    Returns a list of {line, contradicts} dicts in the same order as bad_indices.
    """
    dns_list = profile.get("do_not_say") or []

    def _entry_line(d) -> str:
        return d.get("line", str(d)) if isinstance(d, dict) else str(d)

    def _entry_contradicts(d) -> str:
        return d.get("contradicts", "") if isinstance(d, dict) else ""

    entries_to_replace = [
        f"  [{i}] line={_entry_line(dns_list[i])!r} | contradicts={_entry_contradicts(dns_list[i])!r}"
        for i in bad_indices
    ]
    entries_to_keep = [
        f"  line={_entry_line(d)!r}"
        for i, d in enumerate(dns_list)
        if i not in bad_indices
    ]

    source = profile.get("source_title") or profile.get("source_type", "unknown")
    # Trim profile JSON to avoid token bloat — drop annotated_quotes (verbose)
    trimmed = {k: v for k, v in profile.items() if k != "annotated_quotes"}
    profile_json = json.dumps(trimmed, indent=2, ensure_ascii=False)

    user = _USER_TEMPLATE.format(
        name=name,
        source=source,
        profile_json=profile_json,
        n=len(bad_indices),
        entries_to_replace="\n".join(entries_to_replace),
        entries_to_keep="\n".join(entries_to_keep) if entries_to_keep else "  (none)",
    )

    raw = llm_call(_SYSTEM, user, DEFAULT_MODEL, json_mode=True, temperature=0.7)

    # The LLM should return a JSON array; some backends wrap it in a key.
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        # Some backends return {"replacements": [...]} or {"0": {...}, ...}
        for key in ("replacements", "entries", "results"):
            if key in parsed:
                parsed = parsed[key]
                break
        else:
            # Maybe it's a dict keyed by index
            parsed = list(parsed.values())

    if not isinstance(parsed, list):
        raise ValueError(f"LLM returned unexpected shape for {name}: {type(parsed)}")

    # Tolerate the LLM returning one extra entry — take the first N.
    # Raise only if it returned fewer than expected (missing data).
    if len(parsed) < len(bad_indices):
        raise ValueError(
            f"LLM returned {len(parsed)} entries for {name}, expected {len(bad_indices)}"
        )
    if len(parsed) > len(bad_indices):
        parsed = parsed[: len(bad_indices)]

    # Validate each entry has the required keys
    cleaned = []
    for entry in parsed:
        if not isinstance(entry, dict):
            raise ValueError(f"Entry is not a dict: {entry}")
        if "line" not in entry:
            raise ValueError(f"Entry missing 'line' key: {entry}")
        cleaned.append({
            "line": str(entry["line"]),
            "contradicts": str(entry.get("contradicts", "")),
        })

    return cleaned


def _apply_replacements(
    profile: dict,
    bad_indices: list[int],
    replacements: list[dict],
) -> dict:
    """Return a new profile dict with bad entries replaced."""
    import copy
    updated = copy.deepcopy(profile)
    dns_list = updated.get("do_not_say") or []
    for idx, replacement in zip(bad_indices, replacements):
        dns_list[idx] = replacement
    updated["do_not_say"] = dns_list
    return updated


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate generic do_not_say entries with persona-specific ones."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed changes without writing any files.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="Process only the named personas (exact persona_name match).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between LLM calls (default 0.5). Increase for rate-limited APIs.",
    )
    args = parser.parse_args()

    profiles = _load_profiles()
    freq = _build_freq_table(profiles)

    # Build work list
    work: list[tuple[str, pathlib.Path, dict, list[int]]] = []
    for name, (path, profile) in profiles.items():
        if args.only and name not in args.only:
            continue
        bad = _find_bad_indices(profile, freq)
        if bad:
            work.append((name, path, profile, bad))

    if not work:
        print("No duplicate entries found — nothing to do.")
        return

    total_entries = sum(len(bad) for _, _, _, bad in work)
    print(f"{'DRY RUN - ' if args.dry_run else ''}Processing {len(work)} profiles, {total_entries} entries to replace.")
    print()

    successes = 0
    errors = 0
    replaced_count = 0

    for i, (name, path, profile, bad_indices) in enumerate(work, 1):
        dns_list = profile.get("do_not_say") or []
        print(f"[{i}/{len(work)}] {name}  (entries {bad_indices})")

        # Show what we're replacing
        for idx in bad_indices:
            d = dns_list[idx]
            old_line = d.get("line", str(d)) if isinstance(d, dict) else str(d)
            print(f"  REMOVE [{idx}]: \"{old_line}\"")

        if args.dry_run:
            print()
            continue

        # Call LLM
        try:
            replacements = _call_llm_for_replacements(name, profile, bad_indices)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            print()
            errors += 1
            continue

        # Show and apply
        for idx, replacement in zip(bad_indices, replacements):
            print(f"  ADD    [{idx}]: \"{replacement['line']}\" [violates: {replacement['contradicts']}]")

        updated_profile = _apply_replacements(profile, bad_indices, replacements)
        path.write_text(
            json.dumps(updated_profile, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  Saved -> {path.name}")
        print()
        successes += 1
        replaced_count += len(bad_indices)

        if args.delay and i < len(work):
            time.sleep(args.delay)

    if args.dry_run:
        print(f"Dry run complete. {total_entries} entries would be replaced across {len(work)} profiles.")
    else:
        print(f"Done. {replaced_count} entries replaced across {successes} profiles. ({errors} errors)")
        if successes:
            print("Run  python -m angry_agents.src.rag.build_index  to reindex.")


if __name__ == "__main__":
    main()
