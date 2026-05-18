import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import json
import os
from collections import Counter
from pathlib import Path


_SCENE_RE = re.compile(r'^(INT\.|EXT\.)', re.IGNORECASE)
_CHAR_RE = re.compile(r'^([A-Z][A-Z\s\-\']+?)(?:\s*\([^)]*\))?$')
_SPEECH_TYPE_RE = re.compile(r'\((V\.O\.(?:\s+CONT\'D)?|O\.S\.|O\.C\.|CONT\'D)\)', re.IGNORECASE)
_NON_CHAR_WORDS = {
    'INT', 'EXT', 'CUT', 'FADE', 'DISSOLVE', 'SCENE',
    'THE', 'A', 'AND', 'OR', 'BUT', 'BACK', 'TO',
    'END', 'OMITTED', 'CONTINUED', 'CONT',
}

_MAX_DIALOGUE_LINES = 20

# Lines where more than this fraction of characters are noise are OCR garbage.
_GARBLED_THRESHOLD = 0.25
_PRINTABLE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789 .,!?'\"-:;()[]"
)


def _is_garbled(text: str) -> bool:
    if not text or len(text) < 4:
        return False
    noise = sum(1 for c in text if c not in _PRINTABLE_CHARS)
    return noise / len(text) > _GARBLED_THRESHOLD


# Truncate when sentence-ending punctuation is followed by a lowercase action verb
# (third-person present, past, or progressive). Catches stage directions that bleed
# into the same text block as dialogue.
# e.g. "...please ... rips off his mask" → truncate at "rips"
_ACTION_BLEED_RE = re.compile(r'(?<=[.!?])\s+(?=[a-z][a-z]+(?:s|ed|ing)\b)')


def clean_dialogue(dialogue: str) -> str:
    dialogue = re.sub(r'\s*Revision\s+\d+\.?\s*$', '', dialogue)
    dialogue = re.sub(r'(?<!\w)\*(?!\w)', '', dialogue)        # lone revision asterisks
    dialogue = re.sub(r'^\s*\d+[A-Z]?\s+\d+[A-Z]?\s*$', '', dialogue)  # scene/page numbers
    dialogue = re.sub(r'\s+\d{1,3}\s*$', '', dialogue)        # trailing page numbers
    dialogue = dialogue.replace('•', '.')                      # OCR bullet-as-period
    # Truncate trailing action bleed (stage direction after dialogue end)
    m = _ACTION_BLEED_RE.search(dialogue)
    if m:
        dialogue = dialogue[:m.start()].rstrip(' ,')
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


def _iter_html_nodes(script_element):
    """
    Walk imsdb HTML script element children and yield (kind, content) tuples.

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


# Max words in a character cue name (after stripping parentheticals).
# Guards against ALL-CAPS action lines like "BATMAN RUNS TO THE CAR" being
# misidentified as character cues.
_MAX_CHAR_NAME_WORDS = 4


def _classify_text_line(text: str):
    """
    Classify one screenplay line by content alone — no x-position needed.
    Yields one (kind, content) tuple.
    """
    if not text:
        return ('empty', '')
    if _SCENE_RE.match(text):
        return ('scene', text)
    if text.startswith('(') and text.endswith(')'):
        return ('parenthetical', text)
    if _CHAR_RE.match(text):
        base = re.sub(r'\s*\([^)]*\).*$', '', text).strip()
        words = base.upper().split()
        if len(words) <= _MAX_CHAR_NAME_WORDS and not any(w in _NON_CHAR_WORDS for w in words):
            return ('character', text)
    return ('line', text)


def _iter_pdf_nodes(pdf_path: Path):
    """
    Parse a screenplay PDF and yield (kind, content) tuples.
    Lines are collected per-page sorted top-to-bottom, then classified
    purely by text content — no x-position geometry required.
    """
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextBox, LTTextLine

    for page_layout in extract_pages(str(pdf_path)):
        page_lines = []
        for element in page_layout:
            if not isinstance(element, LTTextBox):
                continue
            for line in element:
                if not isinstance(line, LTTextLine):
                    continue
                text = line.get_text().strip()
                if text:
                    page_lines.append((line.y0, text))

        for _y, text in sorted(page_lines, key=lambda t: -t[0]):
            yield _classify_text_line(text)
        yield ('empty', '')  # page break terminates any open speech block


def _iter_nodes(source):
    """Dispatch to HTML or PDF node iterator based on source type."""
    if isinstance(source, Path):
        yield from _iter_pdf_nodes(source)
    else:
        yield from _iter_html_nodes(source)


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
            dialogue_text = clean_dialogue(' '.join(dialogue_parts))
            if dialogue_text:
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
            if _is_garbled(content):
                continue
            dialogue_parts.append(content)
            if len(dialogue_parts) >= _MAX_DIALOGUE_LINES:
                _flush()

        elif kind == 'empty' and collecting and dialogue_parts:
            # Blank line = end of this speech block; action lines follow
            _flush()

    _flush()
    return result


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "mistral"

_EXTRACTION_SYSTEM = (
    "You are a screenplay analyst. Call add_dialogue_line for every line "
    "spoken by the target character. Never call it for action descriptions."
)

_EXTRACTION_PROMPT = """\
Read the screenplay excerpt below and call `add_dialogue_line` once per speech block spoken by "{character}".

Rules:
- Call the tool ONLY for actual spoken dialogue — never for action/stage directions, even if they mention {character}.
- Use the nearest INT./EXT. scene heading above the line.
- speech_type: "direct" (default), "vo" (V.O.), "os" (O.S.), "oc" (O.C.)
- Merge consecutive lines from the same speech block into one call.
- If {character} has no dialogue in this excerpt, make no tool calls.

--- SCREENPLAY EXCERPT ---
{text}
"""

# Ollama tool definition for structured per-line extraction
_DIALOGUE_TOOL = {
    "type": "function",
    "function": {
        "name": "add_dialogue_line",
        "description": "Record one speech block spoken by the target character.",
        "parameters": {
            "type": "object",
            "properties": {
                "scene": {
                    "type": "string",
                    "description": "Nearest INT./EXT. scene heading above this line",
                },
                "speech_type": {
                    "type": "string",
                    "enum": ["direct", "vo", "os", "oc"],
                    "description": "direct=on-screen, vo=voice over, os=off screen, oc=off camera",
                },
                "dialogue": {
                    "type": "string",
                    "description": "Exact text spoken by the character",
                },
            },
            "required": ["scene", "speech_type", "dialogue"],
        },
    },
}


def _collect_tool_calls(message: dict) -> list[dict]:
    """Extract add_dialogue_line arguments from an Ollama tool-use response message."""
    lines = []
    for call in message.get("tool_calls", []):
        fn = call.get("function", {})
        if fn.get("name") != "add_dialogue_line":
            continue
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue
        if isinstance(args, dict) and "dialogue" in args:
            lines.append({
                "scene": args.get("scene", ""),
                "speech_type": args.get("speech_type", "direct"),
                "dialogue": args.get("dialogue", ""),
            })
    return lines


def _pdf_pages_text(pdf_path: Path) -> list[str]:
    """Return list of raw text strings, one per PDF page."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextBox, LTTextLine

    pages = []
    for page_layout in extract_pages(str(pdf_path)):
        lines = []
        for element in page_layout:
            if not isinstance(element, LTTextBox):
                continue
            for line in element:
                if not isinstance(line, LTTextLine):
                    continue
                text = line.get_text().rstrip('\n')
                if text.strip():
                    lines.append(text)
        if lines:
            pages.append('\n'.join(lines))
    return pages


def extract_character_lines_llm(
    pdf_path: Path,
    character_name: str,
    model: str = DEFAULT_MODEL,
    pages_per_chunk: int = 8,
    ollama_url: str = OLLAMA_BASE_URL,
) -> list[dict]:
    """
    Use a local Ollama model to extract character dialogue from a screenplay PDF.
    Chunks the PDF into groups of pages and queries the model per chunk.
    """
    pages = _pdf_pages_text(pdf_path)
    if not pages:
        return []

    chunks = [pages[i:i + pages_per_chunk] for i in range(0, len(pages), pages_per_chunk)]
    all_lines: list[dict] = []

    print(f"  LLM extraction: {len(pages)} pages → {len(chunks)} chunks")

    for i, chunk_pages in enumerate(chunks, 1):
        chunk_text = '\n\n--- PAGE BREAK ---\n\n'.join(chunk_pages)
        user_content = _EXTRACTION_PROMPT.format(
            character=character_name,
            text=chunk_text,
        )
        payload = {
            "model": model,
            "stream": False,
            "tools": [_DIALOGUE_TOOL],
            "messages": [
                {"role": "system", "content": _EXTRACTION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            "options": {"temperature": 0.1, "num_ctx": 32768},
        }
        resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=600)
        resp.raise_for_status()
        chunk_lines = _collect_tool_calls(resp.json()["message"])
        all_lines.extend(chunk_lines)
        print(f"  Chunk {i}/{len(chunks)}: +{len(chunk_lines)} lines ({len(all_lines)} total)")

    return all_lines


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
    import argparse

    parser = argparse.ArgumentParser(description="Extract character lines from imsdb or PDF screenplay.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--imsdb", nargs="+", metavar="TITLE",
                       help="imsdb movie title(s), e.g. Star-Wars")
    group.add_argument("--pdf", nargs="+", metavar="FILE",
                       help="Path(s) to screenplay PDF file(s)")
    parser.add_argument("--characters", nargs="*", metavar="NAME",
                        help="Character name(s) to extract (ALL CAPS). Omit for interactive selection.")
    parser.add_argument("--out-dir", default=None,
                        help="Output directory (default: <script_dir>/movies_transcripts)")
    parser.add_argument("--use-llm", action="store_true",
                        help="Use local Ollama LLM for dialogue extraction (PDF only, handles noisy scans)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model for --use-llm (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    selected_characters = args.characters or None

    all_scripts = {}
    all_characters = Counter()

    if args.imsdb:
        movie_titles = args.imsdb
        print(f"Fetching {len(movie_titles)} movie script(s) from imsdb...")
        print("-" * 60)

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

    else:
        print(f"Loading {len(args.pdf)} PDF script(s)...")
        print("-" * 60)

        for pdf_path_str in args.pdf:
            pdf_path = Path(pdf_path_str).resolve()
            if not pdf_path.exists():
                print(f"  ✗ File not found: {pdf_path}")
                continue
            print(f"\nLoading: {pdf_path.name}...")
            # Use resolved path as key — avoids stem collision across directories
            all_scripts[str(pdf_path)] = pdf_path
            personas = extract_personas(pdf_path)
            for name, count in personas:
                all_characters[name] += count
            print(f"  ✓ Found {len(personas)} characters")

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

    use_llm = getattr(args, 'use_llm', False)
    if use_llm and args.imsdb:
        print("Warning: --use-llm ignored for imsdb sources (HTML is clean, LLM not needed).")
        use_llm = False

    print(f"\nExtracting {len(selected_characters)} character(s)"
          f"{' via LLM (' + args.model + ')' if use_llm else ''}...")
    print("-" * 60)

    def _film_label(key, source):
        """Human-readable film name for JSON output."""
        return Path(source).stem if isinstance(source, Path) else key

    output_dir = args.out_dir or os.path.join(os.path.dirname(__file__), "movies_transcripts")
    for character_name in selected_characters:
        all_lines = []

        # Aggregate lines from all sources containing this character
        films_with_char = []
        for key, source in all_scripts.items():
            if use_llm and isinstance(source, Path):
                print(f"  [{_film_label(key, source)}] querying {args.model}...")
                lines = extract_character_lines_llm(source, character_name, model=args.model)
            else:
                lines = extract_character_lines(source, character_name)
            if lines:
                all_lines.extend(lines)
                films_with_char.append(_film_label(key, source))

        if all_lines:
            filename = save_character_to_json(
                character_name, films_with_char, all_lines, output_dir
            )
            print(f"✓ {character_name:<30} {len(all_lines):4d} lines → {filename}")
        else:
            print(f"✗ {character_name:<30} (no lines found in selected films)")

    print("\nDone!")

