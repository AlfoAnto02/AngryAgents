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


def clean_dialogue(dialogue: str) -> str:
    """
    Removes artifacts from dialogue (e.g., revision markers).
    """
    # Remove patterns like "Revision 11.", "Revision                        12.", etc.
    dialogue = re.sub(r'\s*Revision\s+\d+\.?\s*$', '', dialogue)
    # Remove multiple spaces
    dialogue = re.sub(r'\s+', ' ', dialogue)
    return dialogue.strip()


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
            dialogue_text = ' '.join(dialogue_parts)
            dialogue_text = clean_dialogue(dialogue_text)
            result.append({
                'scene': current_scene,
                'speech_type': speech_type,
                'dialogue': dialogue_text,
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


def save_character_to_json(character_name, films, lines, output_dir="personas"):
    """
    Save character data to JSON.
    
    Args:
        character_name: Character name
        films: Single film name (str) or list of film names
        lines: List of dialogue dicts
        output_dir: Output directory path
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Normalize films to list
    films_list = films if isinstance(films, list) else [films]

    data = {
        "character": character_name,
        "films": films_list,
        "lines_count": len(lines),
        "lines": lines,
    }

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', character_name)
    filename = os.path.join(output_dir, f"{safe_name}.json")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filename


if __name__ == "__main__":
    # Define movie titles (e.g., saga)
    movie_titles = [
        "Indiana-Jones-and-the-Raiders-of-the-Lost-Ark",
        # "Indiana-Jones-and-the-Temple-of-Doom",
        # "Indiana-Jones-and-the-Last-Crusade",
    ]

    # Optional: specify characters to extract (if None, will show interactive selection)
    selected_characters = None  # Set to list like ["INDY", "MARION"] to skip selection

    print(f"Fetching {len(movie_titles)} movie script(s)...")
    print("-" * 60)

    # Fetch all scripts and aggregate characters
    all_scripts = {}
    all_characters = Counter()

    for movie_title in movie_titles:
        print(f"\nFetching: {movie_title}...")
        script_el = scrape_imsdb_script(movie_title)

        if script_el:
            all_scripts[movie_title] = script_el
            personas = extract_personas(script_el)
            for name, count in personas:
                all_characters[name] += count
            print(f"  ✓ Found {len(personas)} characters")
        else:
            print(f"  ✗ Failed to fetch script")

    if not all_scripts:
        print("Failed to fetch any scripts.")
        exit(1)

    # Display all characters found
    print("\n" + "=" * 60)
    print(f"Total unique characters found: {len(all_characters)}")
    print("=" * 60)
    for i, (name, count) in enumerate(all_characters.most_common(), 1):
        print(f"{i:3d}. {name:<30} ({count:3d} lines)")

    # Character selection
    if selected_characters is None:
        print("\n" + "=" * 60)
        print("SELECT CHARACTERS TO EXTRACT")
        print("=" * 60)
        print("Enter character names separated by commas, or:")
        print("  - 'top N' for top N characters (e.g., 'top 5')")
        print("  - 'all' for all characters")
        print("  - Leave blank to save top 5 (default)")
        user_input = input("\nYour selection: ").strip()

        if not user_input or user_input.lower() == "default":
            selected_characters = [name for name, _ in all_characters.most_common(5)]
        elif user_input.lower() == "all":
            selected_characters = list(all_characters.keys())
        elif user_input.lower().startswith("top"):
            try:
                n = int(user_input.split()[1])
                selected_characters = [name for name, _ in all_characters.most_common(n)]
            except (IndexError, ValueError):
                print("Invalid format. Using top 5.")
                selected_characters = [name for name, _ in all_characters.most_common(5)]
        else:
            # Parse comma-separated names
            selected_characters = [
                c.strip() for c in user_input.split(',') if c.strip()
            ]

    print(f"\nExtracting {len(selected_characters)} character(s)...")
    print("-" * 60)

    output_dir = os.path.join(os.path.dirname(__file__), "personas")
    for character_name in selected_characters:
        all_lines = []

        # Aggregate lines from all movies containing this character
        films_with_char = []
        for movie_title, script_el in all_scripts.items():
            lines = extract_character_lines(script_el, character_name)
            if lines:
                all_lines.extend(lines)
                films_with_char.append(movie_title)

        if all_lines:
            filename = save_character_to_json(
                character_name, films_with_char, all_lines, output_dir
            )
            print(f"✓ {character_name:<30} {len(all_lines):4d} lines → {filename}")
        else:
            print(f"✗ {character_name:<30} (no lines found in selected films)")

    print("\nDone!")

