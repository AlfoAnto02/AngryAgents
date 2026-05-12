"""
PDF screenplay parser using pdfplumber.

Uses X-coordinate position of words (not indentation of plain text) to
classify lines as scene headings, character cues, dialogue, or action.
Auto-detects thresholds per PDF so it works across different sources.

Output format is identical to movies_scraping.py:
    [{"scene": str, "speech_type": str, "dialogue": str}]
"""

import pdfplumber
import re
import json
import os
import sys
from collections import Counter, defaultdict


_SCENE_RE = re.compile(r'^(INT\.|EXT\.)', re.IGNORECASE)
_CHAR_RE = re.compile(r'^([A-Z][A-Z\s\-\']+?)(?:\s*\([^)]*\))?$')
_SPEECH_TYPE_RE = re.compile(r'\((V\.O\.(?:\s+CONT\'D)?|O\.S\.|O\.C\.|CONT\'D)\)', re.IGNORECASE)
_NON_CHAR_WORDS = {
    'INT', 'EXT', 'CUT', 'FADE', 'DISSOLVE', 'SCENE',
    'THE', 'A', 'AND', 'OR', 'BUT', 'BACK', 'TO',
}

# Threshold: if we accumulate this many dialogue lines without a break,
# something went wrong (e.g. merged columns), so stop.
_MAX_DIALOGUE_LINES = 20

# Words whose top coordinate falls within this many points = same line.
_LINE_Y_TOLERANCE = 2


def _group_words_into_lines(words):
    """Group pdfplumber word dicts by vertical position into text lines."""
    if not words:
        return []

    buckets = defaultdict(list)
    for word in words:
        key = round(word['top'] / _LINE_Y_TOLERANCE) * _LINE_Y_TOLERANCE
        buckets[key].append(word)

    lines = []
    for y_key in sorted(buckets):
        line_words = sorted(buckets[y_key], key=lambda w: w['x0'])
        lines.append({
            'text': ' '.join(w['text'] for w in line_words),
            'x0': line_words[0]['x0'],
        })
    return lines


def extract_lines_from_pdf(pdf_path):
    """
    Extract all text lines from a screenplay PDF with their X position.

    Returns list of dicts: [{'text': str, 'x0': float, 'page': int}]
    """
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            for line in _group_words_into_lines(words):
                line['page'] = page.page_number
                all_lines.append(line)
    return all_lines


def _detect_thresholds_pdf(lines):
    """
    Auto-detect character-cue and dialogue X thresholds for this PDF.

    Samples ALL-CAPS candidate lines and uses the mode of their x0 as the
    character cue threshold.  Dialogue threshold is ~55% of that, which
    holds across Final Draft, Celtx, and most professional PDF exports.

    Falls back to standard Final Draft values (220, 108) if not enough data.
    """
    char_x0s = []
    for line in lines:
        content = line['text'].strip()
        if not content or len(content) > 50:
            continue
        if _CHAR_RE.match(content) and content.upper() not in _NON_CHAR_WORDS:
            char_x0s.append(int(line['x0']))  # floor avoids x0=185.9 → thresh=186 miss

    if len(char_x0s) < 10:
        return 220, 108

    char_x0 = Counter(char_x0s).most_common(1)[0][0]
    dialogue_x0 = max(50, int(char_x0 * 0.55))
    return char_x0, dialogue_x0


def _classify_pdf_line(line, char_x0_thresh, dialogue_x0_thresh):
    """
    Classify a PDF line dict by X position and content.

    Returns (kind, content) where kind is one of:
        'scene', 'character', 'dialogue', 'parenthetical', 'action', 'empty'
    """
    content = line['text'].strip()
    if not content:
        return 'empty', ''

    x0 = line['x0']

    if _SCENE_RE.match(content):
        return 'scene', content
    if x0 >= char_x0_thresh and _CHAR_RE.match(content):
        return 'character', content
    if x0 >= dialogue_x0_thresh:
        return ('parenthetical', content) if content.startswith('(') else ('dialogue', content)
    return 'action', content


def _extract_speech_type(char_cue_content):
    """Returns 'vo', 'os', 'oc', or 'direct'."""
    m = _SPEECH_TYPE_RE.search(char_cue_content)
    if not m:
        return 'direct'
    tag = m.group(1).upper().replace(' ', '').replace("'", '')
    if 'VO' in tag:
        return 'vo'
    if 'OS' in tag:
        return 'os'
    if 'OC' in tag:
        return 'oc'
    return 'direct'


def extract_personas_pdf(pdf_path):
    """
    Extract all character names from a screenplay PDF.

    Returns list of (name, count) sorted by frequency.
    """
    lines = extract_lines_from_pdf(pdf_path)
    char_x0, dialogue_x0 = _detect_thresholds_pdf(lines)

    personas = []
    for line in lines:
        kind, content = _classify_pdf_line(line, char_x0, dialogue_x0)
        if kind != 'character':
            continue
        char_name = re.sub(r'\s*\([^)]*\).*$', '', content).strip()
        if char_name and len(char_name) > 1 and char_name.upper() not in _NON_CHAR_WORDS:
            personas.append(char_name)

    return Counter(personas).most_common()


def extract_character_lines_pdf(pdf_path, character_name):
    """
    Extract dialogue lines for a character from a screenplay PDF.

    Returns list of dicts: [{"scene": str, "speech_type": str, "dialogue": str}]
    """
    lines = extract_lines_from_pdf(pdf_path)
    char_x0, dialogue_x0 = _detect_thresholds_pdf(lines)

    result = []
    current_scene = ''
    i = 0

    while i < len(lines):
        kind, content = _classify_pdf_line(lines[i], char_x0, dialogue_x0)

        if kind == 'scene':
            current_scene = content
        elif kind == 'character':
            base_name = re.sub(r'\s*\([^)]*\).*$', '', content).strip()
            if base_name.upper() == character_name.upper():
                speech_type = _extract_speech_type(content)
                i += 1
                dialogue_parts = []
                while i < len(lines):
                    kind2, content2 = _classify_pdf_line(lines[i], char_x0, dialogue_x0)
                    if kind2 in ('scene', 'character'):
                        break
                    if kind2 == 'dialogue':
                        dialogue_parts.append(content2)
                        if len(dialogue_parts) >= _MAX_DIALOGUE_LINES:
                            break
                    # action and parenthetical lines intentionally skipped
                    i += 1
                if dialogue_parts:
                    result.append({
                        'scene': current_scene,
                        'speech_type': speech_type,
                        'dialogue': ' '.join(dialogue_parts),
                    })
                i -= 1

        i += 1

    return result


def save_character_to_json(character_name, film_name, lines, output_dir="personas"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    data = {
        "character": character_name,
        "film": film_name,
        "lines_count": len(lines),
        "lines": lines,
    }

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', character_name)
    filename = os.path.join(output_dir, f"{safe_name}.json")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filename


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_scraping.py <script.pdf> [CHARACTER_NAME]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    film_name = os.path.splitext(os.path.basename(pdf_path))[0]

    print(f"Extracting from: {pdf_path}")

    lines_data = extract_lines_from_pdf(pdf_path)
    char_x0, dialogue_x0 = _detect_thresholds_pdf(lines_data)
    print(f"Detected thresholds — character x0 ≥ {char_x0}, dialogue x0 ≥ {dialogue_x0}")

    personas = extract_personas_pdf(pdf_path)
    if not personas:
        print("No personas found.")
        sys.exit(1)

    print("\nTop 10 personas:")
    print("-" * 40)
    for idx, (name, count) in enumerate(personas[:10], 1):
        print(f"{idx:2d}. {name:<25} ({count:3d} lines)")

    target = sys.argv[2].upper() if len(sys.argv) > 2 else personas[0][0]
    print(f"\nExtracting lines for: {target}")

    char_lines = extract_character_lines_pdf(pdf_path, target)
    output_dir = os.path.join(os.path.dirname(__file__), "personas")
    filename = save_character_to_json(target, film_name, char_lines, output_dir)
    print(f"Saved {len(char_lines)} lines → {filename}")
