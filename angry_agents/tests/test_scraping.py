"""
Scraping pipeline tests.

Unit tests:    pure functions, no I/O, always run.
Integration:   require the Star Wars PDF — skipped if file missing.
Quality:       contamination checks on extracted dialogue.
Structure:     validate every persona JSON in the personas/ dir.
"""

import json
import os
import pytest

from angry_agents.src.scraping.movies_scraping import (
    _classify_line,
    _strip_artifacts,
    _detect_thresholds,
    _extract_speech_type,
)
from angry_agents.src.scraping.pdf_scraping import (
    _classify_pdf_line,
    _group_words_into_lines,
    _detect_thresholds_pdf,
    extract_personas_pdf,
    extract_character_lines_pdf,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(__file__)
_SCRAPING_DIR = os.path.join(_HERE, "..", "src", "scraping")
PERSONAS_DIR = os.path.join(_SCRAPING_DIR, "personas")
STAR_WARS_PDF = os.path.join(_SCRAPING_DIR, "starwars_fourth3_76.pdf")

pdf_available = pytest.mark.skipif(
    not os.path.exists(STAR_WARS_PDF),
    reason="Star Wars PDF not present",
)

# ---------------------------------------------------------------------------
# Unit — _classify_line (movies_scraping)
# ---------------------------------------------------------------------------

class TestClassifyLine:
    def test_character_cue(self):
        assert _classify_line("                    JACK\r", 15, 10) == ("character", "JACK")

    def test_character_with_vo(self):
        kind, content = _classify_line("                    JACK (V.O.)\r", 15, 10)
        assert kind == "character"
        assert "JACK" in content

    def test_dialogue(self):
        kind, _ = _classify_line("          What do you say to three shillings?", 15, 10)
        assert kind == "dialogue"

    def test_scene_ext(self):
        kind, _ = _classify_line("EXT. PORT ROYAL - DAY", 15, 10)
        assert kind == "scene"

    def test_scene_int(self):
        kind, _ = _classify_line("INT. BLACKSMITH'S FORGE - NIGHT", 15, 10)
        assert kind == "scene"

    def test_action(self):
        kind, _ = _classify_line("He draws his sword slowly.", 15, 10)
        assert kind == "action"

    def test_parenthetical(self):
        kind, _ = _classify_line("          (quietly)", 15, 10)
        assert kind == "parenthetical"

    def test_empty(self):
        assert _classify_line("", 15, 10) == ("empty", "")

    def test_whitespace_only(self):
        kind, _ = _classify_line("   \r\n", 15, 10)
        assert kind == "empty"

    def test_below_char_thresh_not_character(self):
        # indent=10, char_thresh=15 → should NOT be character even if ALL-CAPS
        kind, _ = _classify_line("          HERO", 15, 10)
        assert kind == "dialogue"


# ---------------------------------------------------------------------------
# Unit — _strip_artifacts
# ---------------------------------------------------------------------------

class TestStripArtifacts:
    def test_strips_trailing_star(self):
        assert _strip_artifacts("JORDAN                  *") == "JORDAN"

    def test_strips_multiple_stars(self):
        assert _strip_artifacts("DONNIE        ***") == "DONNIE"

    def test_strips_page_number(self):
        assert _strip_artifacts("Watch and learn! 2.") == "Watch and learn!"

    def test_strips_page_number_multidigit(self):
        assert _strip_artifacts("I love drugs. 42.") == "I love drugs."

    def test_clean_line_unchanged(self):
        line = "What do you think you're doing?"
        assert _strip_artifacts(line) == line


# ---------------------------------------------------------------------------
# Unit — _extract_speech_type
# ---------------------------------------------------------------------------

class TestExtractSpeechType:
    def test_direct(self):
        assert _extract_speech_type("JACK") == "direct"

    def test_vo(self):
        assert _extract_speech_type("JORDAN (V.O.)") == "vo"

    def test_vo_contd(self):
        assert _extract_speech_type("JORDAN (V.O. CONT'D)") == "vo"

    def test_os(self):
        assert _extract_speech_type("LEIA (O.S.)") == "os"

    def test_oc(self):
        assert _extract_speech_type("HAN (O.C.)") == "oc"

    def test_contd_only_is_direct(self):
        assert _extract_speech_type("JACK (CONT'D)") == "direct"


# ---------------------------------------------------------------------------
# Unit — _detect_thresholds (movies_scraping)
# ---------------------------------------------------------------------------

def _make_script(char_indent, dialogue_indent, n=15):
    """Minimal synthetic script with known indentation levels."""
    char_line = " " * char_indent + "HERO"
    dlg_line = " " * dialogue_indent + "Hello there."
    return "\n".join([char_line, dlg_line] * n)


def test_detect_thresholds_char_indent():
    script = _make_script(char_indent=20, dialogue_indent=10)
    char_thresh, _ = _detect_thresholds(script)
    assert char_thresh == 20


def test_detect_thresholds_dialogue_below_char():
    script = _make_script(char_indent=20, dialogue_indent=10)
    char_thresh, dialogue_thresh = _detect_thresholds(script)
    assert dialogue_thresh < char_thresh


def test_detect_thresholds_fallback_on_sparse_data():
    char_thresh, dialogue_thresh = _detect_thresholds("almost empty script")
    assert char_thresh == 15
    assert dialogue_thresh == 10


# ---------------------------------------------------------------------------
# Unit — _classify_pdf_line
# ---------------------------------------------------------------------------

class TestClassifyPdfLine:
    def test_character(self):
        line = {"text": "LUKE", "x0": 185.9}
        assert _classify_pdf_line(line, 185, 101) == ("character", "LUKE")

    def test_character_at_exact_threshold(self):
        line = {"text": "HAN", "x0": 185.0}
        assert _classify_pdf_line(line, 185, 101)[0] == "character"

    def test_dialogue(self):
        line = {"text": "I've got a bad feeling about this.", "x0": 125.9}
        assert _classify_pdf_line(line, 185, 101) == ("dialogue", "I've got a bad feeling about this.")

    def test_scene_ext(self):
        line = {"text": "EXT. TATOOINE - DESERT - DAY", "x0": 65.9}
        assert _classify_pdf_line(line, 185, 101) == ("scene", "EXT. TATOOINE - DESERT - DAY")

    def test_scene_int(self):
        line = {"text": "INT. DEATH STAR - CORRIDOR", "x0": 65.9}
        assert _classify_pdf_line(line, 185, 101)[0] == "scene"

    def test_action(self):
        line = {"text": "Luke runs toward the ship.", "x0": 65.9}
        assert _classify_pdf_line(line, 185, 101) == ("action", "Luke runs toward the ship.")

    def test_parenthetical(self):
        line = {"text": "(whispering)", "x0": 150.0}
        assert _classify_pdf_line(line, 185, 101) == ("parenthetical", "(whispering)")

    def test_empty(self):
        line = {"text": "", "x0": 0.0}
        assert _classify_pdf_line(line, 185, 101) == ("empty", "")

    def test_just_below_char_thresh_is_not_character(self):
        line = {"text": "HERO", "x0": 184.9}
        assert _classify_pdf_line(line, 185, 101)[0] != "character"


# ---------------------------------------------------------------------------
# Unit — _group_words_into_lines
# ---------------------------------------------------------------------------

def test_group_words_same_y():
    words = [
        {"text": "Hello", "x0": 100, "top": 50.0},
        {"text": "world", "x0": 130, "top": 50.5},
    ]
    lines = _group_words_into_lines(words)
    assert len(lines) == 1
    assert lines[0]["text"] == "Hello world"
    assert lines[0]["x0"] == 100


def test_group_words_different_y():
    words = [
        {"text": "LUKE", "x0": 185, "top": 100.0},
        {"text": "Hello.", "x0": 125, "top": 115.0},
    ]
    lines = _group_words_into_lines(words)
    assert len(lines) == 2


def test_group_words_empty():
    assert _group_words_into_lines([]) == []


def test_group_words_preserves_left_to_right_order():
    words = [
        {"text": "world", "x0": 130, "top": 50.0},
        {"text": "Hello", "x0": 100, "top": 50.0},
    ]
    lines = _group_words_into_lines(words)
    assert lines[0]["text"] == "Hello world"


# ---------------------------------------------------------------------------
# Integration — Star Wars PDF personas
# ---------------------------------------------------------------------------

@pdf_available
def test_star_wars_top_character_is_luke():
    personas = extract_personas_pdf(STAR_WARS_PDF)
    assert personas, "No personas extracted"
    assert personas[0][0] == "LUKE"


@pdf_available
def test_star_wars_known_characters_present():
    personas = extract_personas_pdf(STAR_WARS_PDF)
    names = {n for n, _ in personas}
    for expected in ("LUKE", "HAN", "THREEPIO", "LEIA", "BEN"):
        assert expected in names, f"{expected} missing from extracted personas"


@pdf_available
def test_star_wars_thresholds_reasonable():
    from angry_agents.src.scraping.pdf_scraping import extract_lines_from_pdf
    lines = extract_lines_from_pdf(STAR_WARS_PDF)
    char_x0, dialogue_x0 = _detect_thresholds_pdf(lines)
    assert 170 <= char_x0 <= 200, f"Unexpected char threshold: {char_x0}"
    assert dialogue_x0 < char_x0


# ---------------------------------------------------------------------------
# Quality — HAN dialogue contamination checks
# ---------------------------------------------------------------------------

@pdf_available
def test_han_no_scene_headings_in_dialogue():
    lines = extract_character_lines_pdf(STAR_WARS_PDF, "HAN")
    for entry in lines:
        assert not entry["dialogue"].startswith("INT.")
        assert not entry["dialogue"].startswith("EXT.")


@pdf_available
def test_han_dialogue_not_all_caps():
    """All-caps dialogue = contamination (absorbed a character cue or stage dir)."""
    lines = extract_character_lines_pdf(STAR_WARS_PDF, "HAN")
    bad = [
        entry["dialogue"]
        for entry in lines
        if len(entry["dialogue"]) > 5 and entry["dialogue"] == entry["dialogue"].upper()
    ]
    assert bad == [], f"All-caps entries found: {bad[:3]}"


@pdf_available
def test_han_has_scene_context():
    lines = extract_character_lines_pdf(STAR_WARS_PDF, "HAN")
    populated = [e for e in lines if e["scene"]]
    assert len(populated) > 0, "No scene context attached to HAN lines"


@pdf_available
def test_han_speech_types_are_valid():
    lines = extract_character_lines_pdf(STAR_WARS_PDF, "HAN")
    valid = {"direct", "vo", "os", "oc"}
    for entry in lines:
        assert entry["speech_type"] in valid, f"Unknown speech_type: {entry['speech_type']}"


# ---------------------------------------------------------------------------
# Structure — every persona JSON in personas/
# ---------------------------------------------------------------------------

def _persona_json_paths():
    if not os.path.exists(PERSONAS_DIR):
        return []
    return [
        os.path.join(PERSONAS_DIR, f)
        for f in os.listdir(PERSONAS_DIR)
        if f.endswith(".json")
    ]


@pytest.mark.parametrize("path", _persona_json_paths())
def test_persona_json_required_fields(path):
    with open(path) as f:
        data = json.load(f)
    if "transcript" in data and "lines" not in data:
        pytest.skip("Old flat-transcript format — needs re-scrape")
    for field in ("character", "film", "lines_count", "lines"):
        assert field in data, f"Missing field '{field}' in {os.path.basename(path)}"


@pytest.mark.parametrize("path", _persona_json_paths())
def test_persona_json_lines_count_matches(path):
    with open(path) as f:
        data = json.load(f)
    if "transcript" in data and "lines" not in data:
        pytest.skip("Old flat-transcript format — needs re-scrape")
    assert data["lines_count"] == len(data["lines"]), (
        f"lines_count={data['lines_count']} but len(lines)={len(data['lines'])} "
        f"in {os.path.basename(path)}"
    )


@pytest.mark.parametrize("path", _persona_json_paths())
def test_persona_json_no_empty_dialogue(path):
    with open(path) as f:
        data = json.load(f)
    # old format: flat transcript string — skip
    if not isinstance(data.get("lines"), list):
        pytest.skip("Old flat-transcript format")
    for i, entry in enumerate(data["lines"]):
        assert isinstance(entry.get("dialogue"), str), (
            f"Entry {i} missing dialogue string in {os.path.basename(path)}"
        )
        assert len(entry["dialogue"]) > 0, (
            f"Empty dialogue at entry {i} in {os.path.basename(path)}"
        )
