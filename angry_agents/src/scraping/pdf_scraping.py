"""
PDF screenplay parser.

Uses X-coordinate position of words to classify lines as scene headings,
character cues, dialogue, or action. Auto-calibrates thresholds per PDF
so it works across Final Draft, Celtx, and most professional exports.

For scanned PDFs (no text layer), falls back to OCR via
pdf2image + pytesseract (install separately if needed).

Output format matches movies_scraping.py:
    {"character": str, "films": [str], "lines_count": int,
     "lines": [{"scene": str, "speech_type": str, "dialogue": str}]}

Usage:
    # list characters interactively
    python -m angry_agents.src.scraping.pdf_scraping --pdf script.pdf

    # extract specific characters across multiple PDFs
    python -m angry_agents.src.scraping.pdf_scraping \\
        --pdf s1.pdf s2.pdf --characters WALTER JESSE

    # merge name variants into one canonical character
    python -m angry_agents.src.scraping.pdf_scraping \\
        --pdf script.pdf \\
        --aliases "WALTER=Walter,Walt,Walter White" "JESSE=Jesse,Pinkman"
"""

import pdfplumber
import re
import json
import os
import sys
import argparse
from collections import Counter, defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Regexes & constants
# ---------------------------------------------------------------------------

_SCENE_RE = re.compile(r'^(INT\.|EXT\.)', re.IGNORECASE)
_CHAR_RE = re.compile(r'^([A-Z][A-Z\s\-\']+?)(?:\s*\([^)]*\))?$')
_SPEECH_TYPE_RE = re.compile(r'\((V\.O\.(?:\s+CONT\'D)?|O\.S\.|O\.C\.|CONT\'D)\)', re.IGNORECASE)

_REVISION_COLORS = r'(?:DOUBLE\s+)?(?:WHITE|BLUE|PINK|YELLOW|GREEN|GOLDENROD|BUFF|SALMON|CHERRY|TAN|GRAY)'
_REVISION_RE = re.compile(
    r'\s*(?:'
    r'\d{1,2}[-\.]\d{1,2}[-\.]\d{2,4}\s+' + _REVISION_COLORS + r'\s+REVISION\s+\d+[A-Z]?\.?'
    r'|'
    r'' + _REVISION_COLORS + r'\s+REVISION\s+[\d\-\.]+\s+\d+[A-Z]?\.?'
    r')\s*',
    re.IGNORECASE,
)

_INLINE_CHAR_CUE_RE = re.compile(
    r'\s+[A-Z][A-Z\s]{1,24}\s*\((?:CONT\'D|V\.O\.[^)]*|O\.S\.|O\.C\.)\)\s*',
)

_NON_CHAR_WORDS = {
    'INT', 'EXT', 'CUT', 'FADE', 'DISSOLVE', 'SCENE',
    'THE', 'A', 'AND', 'OR', 'BUT', 'BACK', 'TO',
    'END', 'OMITTED', 'CONTINUED', 'CONT',
}

_MAX_DIALOGUE_LINES = 20
_LINE_Y_TOLERANCE = 2
_MIN_CHARS_PER_PAGE = 150  # below this → assume scanned


# ---------------------------------------------------------------------------
# Text layer detection
# ---------------------------------------------------------------------------

def has_text_layer(pdf_path: str | Path, sample_pages: int = 5) -> bool:
    """Return True if the PDF has a usable embedded text layer."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages_to_check = min(sample_pages, len(pdf.pages))
        total_chars = sum(
            len(pdf.pages[i].extract_text() or '') for i in range(pages_to_check)
        )
    return (total_chars / max(pages_to_check, 1)) >= _MIN_CHARS_PER_PAGE


# ---------------------------------------------------------------------------
# Native extraction (pdfplumber — text layer present)
# ---------------------------------------------------------------------------

def _group_words_into_lines(words: list[dict]) -> list[dict]:
    """Group pdfplumber word dicts by vertical position into text lines."""
    if not words:
        return []
    buckets: dict[int, list] = defaultdict(list)
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


def _extract_lines_native(pdf_path: str | Path) -> list[dict]:
    all_lines: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            for line in _group_words_into_lines(words):
                line['page'] = page.page_number
                all_lines.append(line)
    return all_lines


# ---------------------------------------------------------------------------
# OCR extraction (scanned PDFs — no text layer)
# ---------------------------------------------------------------------------

def _extract_lines_ocr(pdf_path: str | Path, dpi: int = 300) -> list[dict]:
    """
    Extract lines from a scanned PDF via OCR.

    Requires: pip install pdf2image pytesseract
              brew install poppler tesseract  (or apt equivalent)
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        raise ImportError(
            "OCR requires extra dependencies:\n"
            "  pip install pdf2image pytesseract\n"
            "  brew install poppler tesseract"
        )

    images = convert_from_path(str(pdf_path), dpi=dpi)
    all_lines: list[dict] = []

    for page_num, image in enumerate(images, start=1):
        data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT, config='--psm 6'
        )
        line_buckets: dict[tuple, list] = defaultdict(list)
        for i, word_text in enumerate(data['text']):
            if not word_text.strip():
                continue
            if int(data['conf'][i]) < 30:  # skip low-confidence noise
                continue
            key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
            line_buckets[key].append({'text': word_text, 'x0': float(data['left'][i])})

        for key in sorted(line_buckets):
            words = sorted(line_buckets[key], key=lambda w: w['x0'])
            all_lines.append({
                'text': ' '.join(w['text'] for w in words),
                'x0': words[0]['x0'],
                'page': page_num,
            })

    return all_lines


# ---------------------------------------------------------------------------
# Auto-dispatch
# ---------------------------------------------------------------------------

def extract_lines_from_pdf(pdf_path: str | Path, force_ocr: bool = False) -> list[dict]:
    """
    Extract (text, x0, page) lines from a PDF.

    Auto-detects text layer; falls back to OCR for scanned PDFs.
    """
    pdf_path = Path(pdf_path)
    if not force_ocr and has_text_layer(pdf_path):
        return _extract_lines_native(pdf_path)
    print(f"  No text layer in {pdf_path.name} — using OCR (this may take a while)...")
    return _extract_lines_ocr(pdf_path)


# ---------------------------------------------------------------------------
# Threshold calibration & line classification
# ---------------------------------------------------------------------------

def _detect_thresholds(lines: list[dict]) -> tuple[float, float]:
    """
    Auto-detect character-cue and dialogue X thresholds for this PDF.

    Samples ALL-CAPS candidate lines to find character cue x0 mode.
    Falls back to standard Final Draft values (220, 108) if not enough data.
    """
    char_x0s: list[int] = []
    for line in lines:
        content = line['text'].strip()
        if not content or len(content) > 50:
            continue
        if _CHAR_RE.match(content) and content.upper() not in _NON_CHAR_WORDS:
            char_x0s.append(int(line['x0']))

    if len(char_x0s) < 10:
        return 220.0, 108.0

    char_x0 = float(Counter(char_x0s).most_common(1)[0][0])
    dialogue_x0 = max(50.0, char_x0 * 0.55)
    return char_x0, dialogue_x0


def _classify_line(line: dict, char_x0: float, dialogue_x0: float) -> tuple[str, str]:
    """
    Classify a line dict by X position and content.

    Returns (kind, content) — kind: scene|character|dialogue|parenthetical|action|empty
    """
    content = line['text'].strip()
    if not content:
        return 'empty', ''
    x0 = line['x0']
    if _SCENE_RE.match(content):
        return 'scene', content
    if x0 >= char_x0 and _CHAR_RE.match(content) and content.upper() not in _NON_CHAR_WORDS:
        return 'character', content
    if x0 >= dialogue_x0:
        return ('parenthetical', content) if content.startswith('(') else ('dialogue', content)
    return 'action', content


def _extract_speech_type(char_cue: str) -> str:
    m = _SPEECH_TYPE_RE.search(char_cue)
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


def _base_name(cue: str) -> str:
    """Strip parenthetical from character cue: 'WALTER (V.O.)' → 'WALTER'."""
    return re.sub(r'\s*\([^)]*\).*$', '', cue).strip()


def _clean_dialogue(text: str) -> str:
    text = _REVISION_RE.sub(' ', text)
    text = _INLINE_CHAR_CUE_RE.sub(' ', text)
    text = re.sub(r'(?<!\w)\*(?!\w)', '', text)
    text = re.sub(r'\s+\d{1,3}\s*$', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Character discovery
# ---------------------------------------------------------------------------

def extract_personas(pdf_path: str | Path, force_ocr: bool = False) -> list[tuple[str, int]]:
    """Return (name, line_count) pairs sorted by frequency."""
    lines = extract_lines_from_pdf(pdf_path, force_ocr=force_ocr)
    char_x0, dialogue_x0 = _detect_thresholds(lines)
    counts: Counter = Counter()
    for line in lines:
        kind, content = _classify_line(line, char_x0, dialogue_x0)
        if kind != 'character':
            continue
        name = _base_name(content)
        if name and len(name) > 1 and name.upper() not in _NON_CHAR_WORDS:
            counts[name] += 1
    return counts.most_common()


# ---------------------------------------------------------------------------
# Dialogue extraction
# ---------------------------------------------------------------------------

def extract_character_lines(
    pdf_path: str | Path,
    character_name: str,
    aliases: list[str] | None = None,
    force_ocr: bool = False,
) -> list[dict]:
    """
    Extract dialogue lines for a character from a single PDF.

    aliases: additional name variants that map to this character
             e.g. ['Walter', 'Walt'] all resolve to WALTER

    Returns [{"scene": str, "speech_type": str, "dialogue": str}]
    """
    target_names = {character_name.upper()}
    if aliases:
        target_names.update(a.upper() for a in aliases)

    lines = extract_lines_from_pdf(pdf_path, force_ocr=force_ocr)
    char_x0, dialogue_x0 = _detect_thresholds(lines)

    result: list[dict] = []
    current_scene = ''
    i = 0

    while i < len(lines):
        kind, content = _classify_line(lines[i], char_x0, dialogue_x0)

        if kind == 'scene':
            current_scene = content

        elif kind == 'character':
            if _base_name(content).upper() in target_names:
                speech_type = _extract_speech_type(content)
                i += 1
                dialogue_parts: list[str] = []

                while i < len(lines):
                    kind2, content2 = _classify_line(lines[i], char_x0, dialogue_x0)
                    if kind2 in ('scene', 'character'):
                        break
                    if kind2 == 'dialogue':
                        cleaned = _clean_dialogue(content2)
                        if cleaned:
                            dialogue_parts.append(cleaned)
                        if len(dialogue_parts) >= _MAX_DIALOGUE_LINES:
                            break
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


# ---------------------------------------------------------------------------
# Alias parsing
# ---------------------------------------------------------------------------

def parse_aliases(alias_strings: list[str]) -> dict[str, list[str]]:
    """
    Parse alias strings into canonical → variants mapping.

    Input:  ["WALTER=Walter,Walt,Walter White", "JESSE=Jesse,Pinkman"]
    Output: {"WALTER": ["Walter", "Walt", "Walter White"], "JESSE": [...]}

    Raises ValueError for tokens that are missing '=' so callers can warn the user.
    """
    result: dict[str, list[str]] = {}
    for s in alias_strings:
        s = s.strip()
        if not s:
            continue
        if '=' not in s:
            raise ValueError(
                f"Invalid alias '{s}' — must be CANONICAL=Name1,Name2\n"
                f"  Example: JIMMY=SAUL  (merge SAUL lines into JIMMY)"
            )
        canonical, rest = s.split('=', 1)
        variants = [v.strip() for v in rest.split(',') if v.strip()]
        result[canonical.strip().upper()] = variants
    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_character_to_json(
    character_name: str,
    films: str | list[str],
    lines: list[dict],
    output_dir: str | Path = 'personas',
) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = {
        'character': character_name,
        'films': films if isinstance(films, list) else [films],
        'lines_count': len(lines),
        'lines': lines,
    }

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', character_name)
    out_file = output_dir / f'{safe_name}.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(out_file)


def merge_character_jsons(
    paths: list[str | Path],
    canonical_name: str,
    output_dir: str | Path,
) -> str:
    """
    Merge two or more existing character JSON files into one.

    Lines are concatenated in the order files are given.
    Films lists are merged and deduplicated preserving order.
    """
    merged_lines: list[dict] = []
    merged_films: list[str] = []
    seen_films: set[str] = set()

    for p in paths:
        p = Path(p)
        if not p.exists():
            raise FileNotFoundError(f'Not found: {p}')
        with open(p, encoding='utf-8') as f:
            data = json.load(f)
        merged_lines.extend(data.get('lines', []))
        for film in data.get('films', [data.get('film', p.stem)]):
            if film not in seen_films:
                seen_films.add(film)
                merged_films.append(film)

    return save_character_to_json(canonical_name, merged_films, merged_lines, output_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _collect_pdfs(pdf_args: list[str] | None, dir_args: list[str] | None) -> list[Path]:
    """Resolve --pdf files and --dir folders into a deduplicated list of PDF paths."""
    seen: set[Path] = set()
    result: list[Path] = []

    for p in pdf_args or []:
        path = Path(p).resolve()
        if not path.exists():
            print(f'  ✗ Not found: {path}')
            continue
        if path not in seen:
            seen.add(path)
            result.append(path)

    for d in dir_args or []:
        folder = Path(d).resolve()
        if not folder.is_dir():
            print(f'  ✗ Not a directory: {folder}')
            continue
        pdfs = sorted(folder.glob('*.pdf')) + sorted(folder.glob('*.PDF'))
        for path in pdfs:
            if path not in seen:
                seen.add(path)
                result.append(path)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract character dialogue from screenplay PDFs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  # extract from folder\n'
            '  %(prog)s --dir data/scripts/\n\n'
            '  # collapse two script names into one character during extraction\n'
            '  %(prog)s --pdf script.pdf --characters WALTER --aliases "WALTER=Walter,Walt"\n\n'
            '  # merge two already-extracted JSON files\n'
            '  %(prog)s --merge WALTER.json WALT.json --as WALTER\n'
        ),
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--pdf', nargs='+', metavar='FILE',
                        help='One or more screenplay PDF paths.')
    source.add_argument('--dir', nargs='+', metavar='FOLDER',
                        help='One or more folders — all *.pdf files inside are used.')
    source.add_argument('--merge', nargs='+', metavar='FILE',
                        help='Merge two or more existing character JSON files into one.')
    parser.add_argument('--as', dest='canonical', metavar='NAME',
                        help='Canonical character name for --merge output.')
    parser.add_argument('--characters', nargs='*', metavar='NAME',
                        help='Character name(s) to extract (ALL CAPS). Omit for interactive.')
    parser.add_argument('--aliases', nargs='*', metavar='ALIAS',
                        help=(
                            'Collapse name variants into one character during extraction. '
                            'Format: CANONICAL=Variant1,Variant2  '
                            'Works for any name seen in the script, e.g. '
                            '"WALTER=Walter,Walt,Walter White"'
                        ))
    parser.add_argument('--out-dir', default=None,
                        help='Output directory (default: <script_dir>/movies_transcripts)')
    parser.add_argument('--force-ocr', action='store_true',
                        help='Force OCR even when PDF has a text layer.')
    args = parser.parse_args()

    # ── Merge mode ────────────────────────────────────────────────────────
    if args.merge:
        if not args.canonical:
            parser.error('--merge requires --as CANONICAL_NAME')
        output_dir = (
            Path(args.out_dir)
            if args.out_dir
            else Path(__file__).parent / 'movies_transcripts'
        )
        out_file = merge_character_jsons(args.merge, args.canonical.upper(), output_dir)
        total = sum(
            len(json.load(open(p, encoding='utf-8')).get('lines', []))
            for p in args.merge
        )
        print(f'Merged {len(args.merge)} files ({total} lines) → {out_file}')
        return

    try:
        alias_map = parse_aliases(args.aliases or [])
    except ValueError as e:
        parser.error(str(e))
    selected_characters: list[str] | None = args.characters or None

    # ── Resolve PDF list ───────────────────────────────────────────────────
    pdf_inputs = _collect_pdfs(args.pdf, args.dir)
    if not pdf_inputs:
        print('No PDF files found.')
        sys.exit(1)

    # ── Scan all PDFs ──────────────────────────────────────────────────────
    all_personas: Counter = Counter()
    valid_pdfs: list[Path] = []

    print(f'Scanning {len(pdf_inputs)} PDF(s)...')
    print('-' * 60)

    for pdf_path in pdf_inputs:
        native = has_text_layer(pdf_path)
        mode = 'native' if (native and not args.force_ocr) else 'OCR'
        print(f'  {pdf_path.name}  [{mode}]')
        personas = extract_personas(pdf_path, force_ocr=args.force_ocr or not native)
        for name, count in personas:
            all_personas[name] += count
        valid_pdfs.append(pdf_path)
        char_x0, dialogue_x0 = _detect_thresholds(
            extract_lines_from_pdf(pdf_path, force_ocr=args.force_ocr or not native)
        )
        print(f'    ✓ {len(personas)} characters  |  thresholds: char x0≥{char_x0:.0f}, dialogue x0≥{dialogue_x0:.0f}')

    if not valid_pdfs:
        print('No valid PDFs found.')
        sys.exit(1)

    # ── Display character list ─────────────────────────────────────────────
    print(f'\n{"=" * 60}')
    print(f'Characters found: {len(all_personas)} unique')
    print('=' * 60)
    for i, (name, count) in enumerate(all_personas.most_common(), 1):
        print(f'  {i:3d}. {name:<30} ({count:3d} lines)')

    # ── Interactive character selection ────────────────────────────────────
    if selected_characters is None:
        print(f'\n{"=" * 60}')
        print("SELECT CHARACTERS  (names, 'top N', or 'all' — blank = top 5)")
        print('=' * 60)
        user_input = input('Selection: ').strip()

        if not user_input:
            selected_characters = [n for n, _ in all_personas.most_common(5)]
        elif user_input.lower() == 'all':
            selected_characters = list(all_personas.keys())
        elif user_input.lower().startswith('top'):
            try:
                k = int(user_input.split()[1])
                selected_characters = [n for n, _ in all_personas.most_common(k)]
            except (IndexError, ValueError):
                selected_characters = [n for n, _ in all_personas.most_common(5)]
        else:
            selected_characters = [c.strip() for c in user_input.split(',') if c.strip()]

    # ── Interactive alias merging (if not supplied via --aliases) ──────────
    if not alias_map:
        print(f'\n{"=" * 60}')
        print('COLLAPSE CHARACTERS  (optional — press Enter to skip)')
        print('  Merge name variants OR two different script names into one output.')
        print('  Format: CANONICAL=Name1,Name2,...')
        print('  Examples:')
        print('    WALTER=Walter,Walt,Walter White   ← case/suffix variants')
        print('    WALTER=WALT                       ← two separate script names')
        print('=' * 60)
        raw = input('Groups (space-separated, e.g. JIMMY=SAUL WALTER=Walt): ').strip()
        if raw:
            for token in re.split(r'\s+(?=[A-Z]+=)', raw):
                token = token.strip()
                if not token:
                    continue
                try:
                    alias_map.update(parse_aliases([token]))
                except ValueError as e:
                    print(f'  Warning: {e}')
                    print(f'  Skipped — re-run with correct format or use --aliases flag.')

    # ── Extract ────────────────────────────────────────────────────────────
    output_dir = (
        Path(args.out_dir)
        if args.out_dir
        else Path(__file__).parent / 'movies_transcripts'
    )

    print(f'\nExtracting {len(selected_characters)} character(s)...')
    print('-' * 60)

    for char in selected_characters:
        canon = char.upper()
        aliases = alias_map.get(canon, [])
        all_lines: list[dict] = []
        films_with_char: list[str] = []

        for pdf_path in valid_pdfs:
            native = has_text_layer(pdf_path)
            lines = extract_character_lines(
                pdf_path, canon,
                aliases=aliases,
                force_ocr=args.force_ocr or not native,
            )
            if lines:
                all_lines.extend(lines)
                films_with_char.append(pdf_path.stem)

        if all_lines:
            out_file = save_character_to_json(canon, films_with_char, all_lines, output_dir)
            print(f'  ✓ {canon:<30} {len(all_lines):4d} lines → {out_file}')
        else:
            print(f'  ✗ {canon:<30} (no lines found)')

    print('\nDone.')


if __name__ == '__main__':
    main()
