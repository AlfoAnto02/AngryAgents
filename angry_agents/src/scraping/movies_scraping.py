import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import json
import os
from collections import Counter


_SCENE_RE = re.compile(r'^(INT\.|EXT\.)', re.IGNORECASE)
_CHAR_RE = re.compile(r'^([A-Z][A-Z\s\-\']+?)(?:\s*\([^)]*\))?$')
_SPEECH_TYPE_RE = re.compile(r'\((V\.O\.(?:\s+CONT\'D)?|O\.S\.|O\.C\.|CONT\'D)\)', re.IGNORECASE)
_NON_CHAR_WORDS = {
    'INT', 'EXT', 'CUT', 'FADE', 'DISSOLVE', 'SCENE',
    'THE', 'A', 'AND', 'OR', 'BUT', 'BACK', 'TO',
}

_MAX_DIALOGUE_LINES = 20


def scrape_imsdb_script(movie_title):
    """
    Fetch an imsdb screenplay.

    Returns the BeautifulSoup element whose direct children are <b> character
    cues and text nodes (i.e. the innermost <pre> with screenplay content).
    Returns None on failure.
    """
    url = f"https://imsdb.com/scripts/{movie_title}.html"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        root = (
            soup.find('td', class_='scrtext') or
            soup.find('div', class_='script')
        )
        # Some imsdb pages nest <pre> inside <td> — or even double-nest it.
        # Pick the <pre> with the most direct <b> children (= screenplay body).
        pres = root.find_all('pre') if root else soup.find_all('pre')
        if not pres:
            return root
        return max(pres, key=lambda p: len(p.find_all('b', recursive=False)))
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def _extract_speech_type(char_cue_content):
    """Returns 'vo', 'os', 'oc', or 'direct'."""
    m = _SPEECH_TYPE_RE.search(char_cue_content)
    if not m:
        return 'direct'
    tag = re.sub(r'[^A-Z]', '', m.group(1).upper())
    if 'VO' in tag:
        return 'vo'
    if 'OS' in tag:
        return 'os'
    if 'OC' in tag:
        return 'oc'
    return 'direct'


def _iter_nodes(script_element):
    """
    Walk script element children and yield (kind, content) tuples.

    Character cues come exclusively from <b> tags — zero indentation guessing.
    Text nodes are split line by line: scene headings, parentheticals, dialogue,
    and empty lines.
    """
    for child in script_element.children:
        if isinstance(child, Tag) and child.name == 'b':
            text = child.get_text(strip=True)
            if not text:
                continue
            if _SCENE_RE.match(text):
                yield ('scene', text)
            elif _CHAR_RE.match(text) and text.upper() not in _NON_CHAR_WORDS:
                yield ('character', text)
        else:
            raw = str(child) if isinstance(child, NavigableString) else child.get_text()
            for line in raw.split('\n'):
                stripped = line.strip()
                if not stripped:
                    yield ('empty', '')
                elif _SCENE_RE.match(stripped):
                    yield ('scene', stripped)
                elif stripped.startswith('(') and stripped.endswith(')'):
                    yield ('parenthetical', stripped)
                else:
                    yield ('line', stripped)


def extract_personas(script_element):
    """
    Extract all character names from an imsdb script element.

    Returns list of (name, count) sorted by frequency.
    """
    if script_element is None:
        return []

    counts = Counter()
    for kind, content in _iter_nodes(script_element):
        if kind != 'character':
            continue
        name = re.sub(r'\s*\([^)]*\).*$', '', content).strip()
        if name and len(name) > 1 and name.upper() not in _NON_CHAR_WORDS:
            counts[name] += 1

    return counts.most_common()


def extract_character_lines(script_element, character_name):
    """
    Extract dialogue lines for a character from an imsdb script element.

    Returns list of dicts: [{"scene": str, "speech_type": str, "dialogue": str}]

    Empty lines after dialogue terminate the current speech block, preventing
    action descriptions from leaking into dialogue.
    """
    if script_element is None:
        return []

    result = []
    current_scene = ''
    collecting = False
    speech_type = 'direct'
    dialogue_parts = []

    def _flush():
        nonlocal collecting, dialogue_parts
        if collecting and dialogue_parts:
            result.append({
                'scene': current_scene,
                'speech_type': speech_type,
                'dialogue': ' '.join(dialogue_parts),
            })
        dialogue_parts = []
        collecting = False

    for kind, content in _iter_nodes(script_element):
        if kind == 'scene':
            _flush()
            current_scene = content

        elif kind == 'character':
            _flush()
            base_name = re.sub(r'\s*\([^)]*\).*$', '', content).strip()
            if base_name.upper() == character_name.upper():
                collecting = True
                speech_type = _extract_speech_type(content)

        elif kind == 'line' and collecting:
            dialogue_parts.append(content)
            if len(dialogue_parts) >= _MAX_DIALOGUE_LINES:
                _flush()

        elif kind == 'empty' and collecting and dialogue_parts:
            # Blank line = end of this speech block; action lines follow
            _flush()

    _flush()
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
    movie_title = "La-La-Land"  # Change this to your desired movie title (without .html)

    print(f"Fetching {movie_title} script...")
    script_el = scrape_imsdb_script(movie_title)

    # print(script_el.prettify()[:1000])  # Print the first 1000 characters of the script element for debugging

    if script_el:
        print("Script fetched successfully!")

        personas = extract_personas(script_el)

        if personas:
            print("\nTop 10 personas (characters by frequency):")
            print("-" * 40)
            for i, (name, count) in enumerate(personas[:10], 1):
                print(f"{i:2d}. {name:<25} ({count:3d} lines)")

            print("\nSaving top 5 characters to JSON files...")
            print("-" * 40)
            output_dir = os.path.join(os.path.dirname(__file__), "personas")
            for name, count in personas[:5]:
                lines = extract_character_lines(script_el, name)
                filename = save_character_to_json(name, movie_title, lines, output_dir)
                print(f"✓ {name}: {len(lines)} lines → {filename}")
        else:
            print("No personas found in the script.")
    else:
        print("Failed to fetch the script.")
