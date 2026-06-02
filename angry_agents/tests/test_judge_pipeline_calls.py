"""
Verifies the two-call judge pipeline:
  Call 1 — persona identification (no fidelity in prompt or output)
  Call 2 — individual fidelity given true mapping (separate, explicit)
"""

import json
from unittest.mock import MagicMock, call, patch

import pytest

from angry_agents.src.rag.judge_with_tools import (
    _parse_assignment,
    run_group_fidelity_with_tools,
    run_individual_fidelity_with_tools,
    run_persona_identification_with_tools,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DIGEST_A = "aaaaaa1111111111111111111111111111111111111111111111111111111111"
_DIGEST_B = "bbbbbb2222222222222222222222222222222222222222222222222222222222"

_CHAT = {
    "messages": [
        {"author": _DIGEST_A, "message": "Life is like a box of chocolates."},
        {"author": _DIGEST_A, "message": "Mama always said stupid is as stupid does."},
        {"author": _DIGEST_B, "message": "Wubba lubba dub dub!"},
        {"author": _DIGEST_B, "message": "Get schwifty."},
    ]
}

_CANDIDATES = [
    {"persona_name": "Forrest Gump", "core_style": "slow, sincere, literal"},
    {"persona_name": "Rick Sanchez", "core_style": "cynical, rapid-fire, scientific"},
    {"persona_name": "Batman", "core_style": "brooding, clipped"},
]

_ALL_PROFILES = {
    "Forrest Gump": {"persona_name": "Forrest Gump", "core_style": "slow, sincere, literal"},
    "Rick Sanchez": {"persona_name": "Rick Sanchez", "core_style": "cynical, rapid-fire, scientific"},
}

_AUTHOR_MAP = {_DIGEST_A: "Forrest Gump", _DIGEST_B: "Rick Sanchez"}


# ---------------------------------------------------------------------------
# Call 1 — persona identification
# ---------------------------------------------------------------------------

class TestPersonaIdentificationCall:
    def test_identification_template_has_no_fidelity_key(self):
        from angry_agents.src.agents.judges.templates import render_prompt

        for role in ("style", "ideology", "general", "behavioral"):
            system, user = render_prompt(
                f"persona_id_{role}_batch.j2",
                n_candidates=3,
                candidates_block="...",
                messages_block="...",
                author_list="a, b",
                persona_names="P1, P2, P3",
            )
            assert '"fidelity"' not in system, f"{role}: fidelity key in system prompt"
            assert '"fidelity"' not in user, f"{role}: fidelity key in user prompt"
            assert "fidelity rubric" not in system.lower(), f"{role}: fidelity rubric still present"
            # Group fidelity is now a dedicated call/template — it must not leak into persona ID.
            assert "group_fidelity_score" not in system, f"{role}: group_fidelity_score leaked into persona ID system prompt"
            assert "group_fidelity_score" not in user, f"{role}: group_fidelity_score leaked into persona ID user prompt"

    def test_parse_assignment_returns_no_fidelity_signal(self):
        raw = json.dumps({
            "assignment": {_DIGEST_A: "Forrest Gump", _DIGEST_B: "Rick Sanchez"},
            "group_fidelity_score": 4,
        })
        result = _parse_assignment(raw, [_DIGEST_A, _DIGEST_B], _CANDIDATES)
        for author, scores in result.items():
            assert len(scores) == 1
            # score is the neutral constant 3 — not meaningful fidelity
            assert scores[0].score == 3

    def test_build_record_fidelity_is_null(self):
        """persona_identification entries must have fidelity=None."""
        from angry_agents.src.rag.evaluation_test_20_judges import _build_record
        from angry_agents.src.agents.judges.base_judge import (
            AuthorMatch, PersonaIdentificationResult, PersonaScore,
        )

        result = PersonaIdentificationResult(matches=[
            AuthorMatch(author=_DIGEST_A, scores=[PersonaScore("Forrest Gump", 3)]),
            AuthorMatch(author=_DIGEST_B, scores=[PersonaScore("Rick Sanchez", 3)]),
        ])
        judge = {"name": "style_1", "role": "style", "focus": "style", "rag_fields": None, "top_k": 10}
        record = _build_record(1, judge, 99, result, ["Forrest Gump", "Rick Sanchez", "Batman"])

        for entry in record["persona_identification"]:
            assert entry["fidelity"] is None, (
                f"fidelity must be None in identification record, got {entry['fidelity']} for {entry['persona_name']}"
            )


# ---------------------------------------------------------------------------
# Call 2 — individual fidelity
# ---------------------------------------------------------------------------

class TestIndividualFidelityCall:
    def test_fidelity_template_has_individual_fidelity_key(self):
        from angry_agents.src.agents.judges.templates import render_prompt

        for role in ("style", "ideology", "general", "behavioral"):
            system, user = render_prompt(
                f"individual_fidelity_{role}.j2",
                n_pairs=2,
                pairs_block="--- Pair 1 ---\nAuthor: aaa\nMessages:\n- hello\n\nPersona: Forrest Gump\nSlow and sincere.",
            )
            assert '"individual_fidelity"' in system
            assert "true" in system.lower() or "revealed" in system.lower(), (
                f"{role}: template should state that true identity is revealed"
            )

    def test_fidelity_call_uses_true_mapping(self):
        """run_individual_fidelity_with_tools sends each true (author, persona) pair."""
        fake_response = json.dumps({"individual_fidelity": {"Forrest Gump": 4, "Rick Sanchez": 5}})

        with patch(
            "angry_agents.src.rag.judge_with_tools._openai_simple_call",
            return_value=fake_response,
        ) as mock_call:
            result = run_individual_fidelity_with_tools(
                role="style",
                messages_by_digest={_DIGEST_A: ["Life is like a box of chocolates."], _DIGEST_B: ["Wubba lubba dub dub!"]},
                true_mapping=_AUTHOR_MAP,
                all_profiles=_ALL_PROFILES,
                judge_name="style_1",
            )

        assert mock_call.call_count == 1
        _, user_prompt = mock_call.call_args[0][0], mock_call.call_args[0][1]
        # Both true pairs must appear in the prompt
        assert "Forrest Gump" in user_prompt
        assert "Rick Sanchez" in user_prompt
        assert _DIGEST_A in user_prompt
        assert _DIGEST_B in user_prompt
        # Scores returned for all true personas
        assert result == {"Forrest Gump": 4, "Rick Sanchez": 5}

    def test_fidelity_scores_clamped_to_1_5(self):
        fake_response = json.dumps({"individual_fidelity": {"Forrest Gump": 9, "Rick Sanchez": -1}})
        with patch("angry_agents.src.rag.judge_with_tools._openai_simple_call", return_value=fake_response):
            result = run_individual_fidelity_with_tools(
                role="general",
                messages_by_digest={_DIGEST_A: ["hi"], _DIGEST_B: ["yo"]},
                true_mapping=_AUTHOR_MAP,
                all_profiles=_ALL_PROFILES,
            )
        assert result["Forrest Gump"] == 5
        assert result["Rick Sanchez"] == 1

    def test_missing_score_defaults_to_1(self):
        fake_response = json.dumps({"individual_fidelity": {"Forrest Gump": 4}})  # Rick Sanchez missing
        with patch("angry_agents.src.rag.judge_with_tools._openai_simple_call", return_value=fake_response):
            result = run_individual_fidelity_with_tools(
                role="behavioral",
                messages_by_digest={_DIGEST_A: ["hi"], _DIGEST_B: ["yo"]},
                true_mapping=_AUTHOR_MAP,
                all_profiles=_ALL_PROFILES,
            )
        assert result["Forrest Gump"] == 4
        assert result["Rick Sanchez"] == 1  # default

    def test_invalid_json_returns_all_defaults(self):
        with patch("angry_agents.src.rag.judge_with_tools._openai_simple_call", return_value="not json"):
            result = run_individual_fidelity_with_tools(
                role="ideology",
                messages_by_digest={_DIGEST_A: ["hi"], _DIGEST_B: ["yo"]},
                true_mapping=_AUTHOR_MAP,
                all_profiles=_ALL_PROFILES,
            )
        assert all(v == 1 for v in result.values())
        assert set(result.keys()) == {"Forrest Gump", "Rick Sanchez"}


# ---------------------------------------------------------------------------
# Call 3 — group fidelity (dedicated call, independent of persona ID / fidelity)
# ---------------------------------------------------------------------------

class TestGroupFidelityCall:
    def test_group_fidelity_templates_render_with_score_key(self):
        from angry_agents.src.agents.judges.templates import render_prompt

        for role in ("style", "ideology", "general", "behavioral"):
            system, user = render_prompt(
                f"group_fidelity_{role}.j2",
                topic="Climate policy",
                conversation_block="[aaa]: We must act now.\n[bbb]: Says who?",
            )
            assert '"group_fidelity_score"' in system, f"{role}: group_fidelity_score key missing"
            # A group fidelity template must NOT ask for per-persona individual fidelity.
            assert '"individual_fidelity"' not in system, f"{role}: individual_fidelity leaked into group fidelity"
            # Topic and the chronological conversation must both reach the prompt.
            assert "Climate policy" in user, f"{role}: topic missing from prompt"
            assert "[aaa]:" in user and "[bbb]:" in user, f"{role}: conversation missing from prompt"

    def test_group_fidelity_topic_omitted_when_none(self):
        from angry_agents.src.agents.judges.templates import render_prompt

        _, user = render_prompt(
            "group_fidelity_general.j2",
            topic=None,
            conversation_block="[aaa]: hi\n[bbb]: yo",
        )
        assert "Topic:" not in user  # {% if topic %} guard drops the line when None

    def test_group_fidelity_parses_and_defaults_out_of_range(self):
        # In-range int kept; out-of-range / non-int → neutral default 3 (with warning).
        for raw_score, expected in [(4, 4), (1, 1), (5, 5), (9, 3), (0, 3), ("bad", 3)]:
            fake = json.dumps({"group_fidelity_score": raw_score})
            with patch(
                "angry_agents.src.rag.judge_with_tools._openai_simple_call",
                return_value=fake,
            ):
                score = run_group_fidelity_with_tools(
                    role="general", chat=_CHAT, judge_name="general_1",
                )
            assert score == expected, f"raw={raw_score!r} → {score}, expected {expected}"

    def test_group_fidelity_invalid_json_defaults_to_3(self):
        with patch(
            "angry_agents.src.rag.judge_with_tools._openai_simple_call",
            return_value="not json",
        ):
            score = run_group_fidelity_with_tools(role="style", chat=_CHAT, judge_name="style_1")
        assert score == 3

    def test_group_fidelity_sends_chronological_transcript(self):
        """The judge must see messages in chronological order, not grouped by author."""
        captured: dict = {}

        def _capture(system, user, model, **kwargs):
            captured["user"] = user
            captured["call_type"] = kwargs.get("call_type")
            return json.dumps({"group_fidelity_score": 5})

        with patch(
            "angry_agents.src.rag.judge_with_tools._openai_simple_call",
            side_effect=_capture,
        ):
            score = run_group_fidelity_with_tools(
                role="behavioral", chat=_CHAT, judge_name="behavioral_1",
            )

        assert score == 5
        # Token usage must be attributed to the dedicated group_fidelity call type.
        assert captured["call_type"] == "group_fidelity"
        user = captured["user"]
        # _CHAT order is A, A, B, B — chronological order must be preserved in the prompt.
        i_a1 = user.index("Life is like a box of chocolates")
        i_a2 = user.index("Mama always said")
        i_b1 = user.index("Wubba lubba dub dub")
        assert i_a1 < i_a2 < i_b1, "conversation_block is not chronological"


# ---------------------------------------------------------------------------
# End-to-end record structure
# ---------------------------------------------------------------------------

class TestRecordStructure:
    def test_record_has_individual_fidelity_and_null_fidelity_in_pi(self):
        """Full record: individual_fidelity populated, persona_identification fidelity always null."""
        from angry_agents.src.rag.evaluation_test_20_judges import _build_record
        from angry_agents.src.agents.judges.base_judge import (
            AuthorMatch, PersonaIdentificationResult, PersonaScore,
        )

        pi_result = PersonaIdentificationResult(matches=[
            AuthorMatch(author=_DIGEST_A, scores=[PersonaScore("Forrest Gump", 3)]),
            AuthorMatch(author=_DIGEST_B, scores=[PersonaScore("Rick Sanchez", 3)]),
        ])
        judge = {"name": "general_2", "role": "general", "focus": "all", "rag_fields": None, "top_k": 10}
        if_scores = {"Forrest Gump": 4, "Rick Sanchez": 5}

        record = _build_record(
            2, judge, 42, pi_result,
            ["Forrest Gump", "Rick Sanchez", "Batman"],
            gf_score=4,
            individual_fidelity=if_scores,
        )

        # individual_fidelity is the dedicated output
        assert record["individual_fidelity"] == {"Forrest Gump": 4, "Rick Sanchez": 5}

        # persona_identification fidelity must be None — not used for scoring
        for entry in record["persona_identification"]:
            assert entry["fidelity"] is None

        # Correct predictions stored
        pi_map = {e["persona_name"]: e["predicted"] for e in record["persona_identification"]}
        assert pi_map["Forrest Gump"] == _DIGEST_A
        assert pi_map["Rick Sanchez"] == _DIGEST_B
        assert pi_map["Batman"] is None  # distractor
