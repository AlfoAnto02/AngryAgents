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
from bs4 import BeautifulSoup

from angry_agents.src.scraping.movies_scraping import (
    _extract_speech_type,
    _iter_nodes,
    extract_personas,
    extract_character_lines,
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
STAR_WARS_PDF = os.path.join(_SCRAPING_DIR, "scripts", "starwars_fourth3_76.pdf")

pdf_available = pytest.mark.skipif(
    not os.path.exists(STAR_WARS_PDF),
    reason="Star Wars PDF not present",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_script_el(html_body):
    """Wrap HTML in a <pre> and return the BeautifulSoup element."""
    return BeautifulSoup(f"<pre>{html_body}</pre>", "html.parser").find("pre")


# ---------------------------------------------------------------------------
# Unit — _iter_nodes (movies_scraping)
# ---------------------------------------------------------------------------

class TestIterNodes:
    def test_b_tag_yields_character(self):
        el = _make_script_el("<b>JACK</b>")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "character" in kinds

    def test_b_tag_content(self):
        el = _make_script_el("<b>JACK (V.O.)</b>")
        chars = [c for k, c in _iter_nodes(el) if k == "character"]
        assert chars == ["JACK (V.O.)"]

    def test_non_char_b_tag_ignored(self):
        el = _make_script_el("<b>THE</b>")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "character" not in kinds

    def test_scene_ext_detected(self):
        el = _make_script_el("\nEXT. PORT ROYAL - DAY\n")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "scene" in kinds

    def test_scene_int_detected(self):
        el = _make_script_el("\nINT. BLACKSMITH'S FORGE - NIGHT\n")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "scene" in kinds

    def test_parenthetical_detected(self):
        el = _make_script_el("\n(quietly)\n")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "parenthetical" in kinds

    def test_empty_line_detected(self):
        el = _make_script_el("\n\n")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "empty" in kinds

    def test_dialogue_yields_line(self):
        el = _make_script_el("\nWhat do you say to three shillings?\n")
        kinds = [k for k, _ in _iter_nodes(el)]
        assert "line" in kinds


# ---------------------------------------------------------------------------
# Unit — extract_character_lines (movies_scraping)
# ---------------------------------------------------------------------------

class TestExtractCharacterLines:
    def _el(self, html):
        return _make_script_el(html)

    def test_basic_dialogue(self):
        el = self._el(
            "\nEXT. DOCKS - DAY\n\n"
            "<b>JACK</b>\n"
            "What do you say to three shillings?\n\n"
        )
        lines = extract_character_lines(el, "JACK")
        assert len(lines) == 1
        assert lines[0]["dialogue"] == "What do you say to three shillings?"

    def test_scene_attached(self):
        el = self._el(
            "\nEXT. DOCKS - DAY\n\n"
            "<b>JACK</b>\n"
            "That's a fine boat.\n\n"
        )
        lines = extract_character_lines(el, "JACK")
        assert lines[0]["scene"] == "EXT. DOCKS - DAY"

    def test_speech_type_vo(self):
        el = self._el("<b>JACK (V.O.)</b>\nNarration here.\n\n")
        lines = extract_character_lines(el, "JACK")
        assert lines[0]["speech_type"] == "vo"

    def test_other_character_not_collected(self):
        el = self._el(
            "<b>WILL</b>\nI'm Will Turner.\n\n"
            "<b>JACK</b>\nSo you are.\n\n"
        )
        lines = extract_character_lines(el, "JACK")
        assert len(lines) == 1
        assert "Will Turner" not in lines[0]["dialogue"]

    def test_action_after_blank_not_included(self):
        el = self._el(
            "<b>JACK</b>\n"
            "Savvy?\n\n"
            "Jack draws his sword.\n\n"
            "<b>WILL</b>\nYes.\n\n"
        )
        lines = extract_character_lines(el, "JACK")
        assert len(lines) == 1
        assert "sword" not in lines[0]["dialogue"]

    def test_multiple_speeches(self):
        el = self._el(
            "<b>JACK</b>\nFirst line.\n\n"
            "<b>WILL</b>\nInterrupt.\n\n"
            "<b>JACK</b>\nSecond line.\n\n"
        )
        lines = extract_character_lines(el, "JACK")
        assert len(lines) == 2

    def test_empty_script(self):
        assert extract_character_lines(None, "JACK") == []


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
