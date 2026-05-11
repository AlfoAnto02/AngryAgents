import requests
from bs4 import BeautifulSoup
import re
import json
import os
from collections import Counter

def scrape_imsdb_script(movie_title):
    search_url = f"https://imsdb.com/scripts/{movie_title}.html"
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        script_element = soup.find('td', class_='scrtext')
        if not script_element:
            script_element = soup.find('pre')
        if not script_element:
            script_element = soup.find('div', class_='script')
        if not script_element:
            all_tds = soup.find_all('td')
            for td in all_tds:
                if len(td.get_text(strip=True)) > 1000:
                    script_element = td
                    break

        if script_element:
            # preserve whitespace — indentation is needed for line classification
            return script_element.get_text() or None
        else:
            print(f"No script element found at {search_url}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching {search_url}: {e}")
        return None


_SCENE_RE = re.compile(r'^(INT\.|EXT\.)')
_CHAR_RE = re.compile(r'^([A-Z][A-Z\s\-\']+?)(?:\s*\([^)]*\))?$')
_SPEECH_TYPE_RE = re.compile(r'\((V\.O\.(?:\s+CONT\'D)?|O\.S\.|O\.C\.|CONT\'D)\)', re.IGNORECASE)
_TRAILING_ARTIFACTS_RE = re.compile(r'(\s*\*+\s*|\s+\d+\.\s*)$')
_NON_CHAR_WORDS = {
    'INT', 'EXT', 'CUT', 'FADE', 'DISSOLVE', 'SCENE',
    'THE', 'A', 'AND', 'OR', 'BUT', 'BACK', 'TO',
}

# Guard: if collecting dialogue and hit this many lines without a break,
# something is wrong (e.g. dual-column revision formatting merged lines).
_MAX_DIALOGUE_LINES = 20


def _strip_artifacts(content):
    """Strip trailing revision markers (* clusters) and page numbers."""
    return _TRAILING_ARTIFACTS_RE.sub('', content).strip()


def _detect_thresholds(script_text):
    """
    Auto-detect character-cue and dialogue indentation thresholds for this
    specific script.

    Samples lines that match the ALL-CAPS character-name pattern and takes
    the mode of their indentation as the character threshold.  Dialogue
    threshold is set at half that value, which holds across all imsdb formats.

    Falls back to (15, 10) if not enough data is found.
    """
    char_indents = []
    for raw_line in script_text.split('\n'):
        content = _strip_artifacts(raw_line.strip())
        if not content or len(content) > 50:
            continue
        if _CHAR_RE.match(content) and content.upper() not in _NON_CHAR_WORDS:
            indent = len(raw_line) - len(raw_line.lstrip())
            if indent > 0:
                char_indents.append(indent)

    if len(char_indents) < 10:
        return 15, 10

    char_thresh = Counter(char_indents).most_common(1)[0][0]
    dialogue_thresh = max(3, char_thresh // 2)
    return char_thresh, dialogue_thresh


def _classify_line(raw_line, char_thresh, dialogue_thresh):
    """
    Classify a raw (unstripped) script line using indentation.

    Returns (kind, content) where kind is one of:
        'scene', 'character', 'dialogue', 'parenthetical', 'action', 'empty'
    """
    if not raw_line.strip():
        return 'empty', ''
    indent = len(raw_line) - len(raw_line.lstrip())
    content = _strip_artifacts(raw_line.strip())

    if not content:
        return 'empty', ''
    if _SCENE_RE.match(content):
        return 'scene', content
    if indent >= char_thresh and _CHAR_RE.match(content):
        return 'character', content
    if indent >= dialogue_thresh:
        return ('parenthetical', content) if content.startswith('(') else ('dialogue', content)
    return 'action', content


def _extract_speech_type(char_cue_content):
    """
    Extract speech modifier from a character cue line.
    Returns 'vo', 'os', 'oc', or 'direct'.
    """
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


def extract_personas(script_text):
    if not script_text:
        return []

    char_thresh, dialogue_thresh = _detect_thresholds(script_text)
    personas = []
    for raw_line in script_text.split('\n'):
        kind, content = _classify_line(raw_line, char_thresh, dialogue_thresh)
        if kind != 'character':
            continue
        char_name = re.sub(r'\s*\([^)]*\).*$', '', content).strip()
        if char_name and len(char_name) > 1 and char_name.upper() not in _NON_CHAR_WORDS:
            personas.append(char_name)

    return Counter(personas).most_common()


def extract_character_lines(script_text, character_name):
    """
    Extract dialogue lines for a character.

    Uses per-script indentation thresholds (auto-detected) to skip stage
    directions and scene headings.  Stores speech_type ('direct', 'vo', 'os',
    'oc') so callers can filter narration from in-scene dialogue.

    Returns list of dicts: [{"scene": str, "speech_type": str, "dialogue": str}]
    """
    if not script_text:
        return []

    char_thresh, dialogue_thresh = _detect_thresholds(script_text)
    raw_lines = script_text.split('\n')
    result = []
    current_scene = ''
    i = 0

    while i < len(raw_lines):
        kind, content = _classify_line(raw_lines[i], char_thresh, dialogue_thresh)

        if kind == 'scene':
            current_scene = content
        elif kind == 'character':
            base_name = re.sub(r'\s*\([^)]*\).*$', '', content).strip()
            if base_name.upper() == character_name.upper():
                speech_type = _extract_speech_type(content)
                i += 1
                dialogue_parts = []
                while i < len(raw_lines):
                    kind2, content2 = _classify_line(raw_lines[i], char_thresh, dialogue_thresh)
                    if kind2 in ('scene', 'character'):
                        break
                    if kind2 == 'dialogue':
                        dialogue_parts.append(content2)
                        if len(dialogue_parts) >= _MAX_DIALOGUE_LINES:
                            break
                    # action and parenthetical lines are intentionally skipped
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
    movie_title = "Wolf-of-Wall-Street,-The"

    print(f"Fetching {movie_title} script...")
    script = scrape_imsdb_script(movie_title)

    if script:
        print(f"Script fetched successfully! ({len(script)} characters)")

        char_thresh, dialogue_thresh = _detect_thresholds(script)
        print(f"Detected thresholds — character: {char_thresh}, dialogue: {dialogue_thresh}\n")

        personas = extract_personas(script)

        if personas:
            print("Top 10 personas (characters by frequency):")
            print("-" * 40)
            for i, (name, count) in enumerate(personas[:10], 1):
                print(f"{i:2d}. {name:<25} ({count:3d} lines)")

            print("\n\nSaving top 5 characters to JSON files...")
            print("-" * 40)
            output_dir = os.path.join(os.path.dirname(__file__), "personas")
            for name, count in personas[:5]:
                lines = extract_character_lines(script, name)
                filename = save_character_to_json(name, movie_title, lines, output_dir)
                print(f"✓ {name}: {len(lines)} lines → {filename}")
        else:
            print("No personas found in the script.")
    else:
        print("Failed to fetch the script.")
