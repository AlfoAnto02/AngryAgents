"""
Scrape YouTube channel videos: metadata + transcripts via yt-dlp and youtube-transcript-api.
Output: JSON file in data/youtube/ with video metadata and transcript text per video.

Usage:
    # Scrape entire channel (default: @JOk3R1, all videos, ≤50k tokens)
    python -m angry_agents.src.scraping.youtube_scraping

    # Limit number of videos from channel
    python -m angry_agents.src.scraping.youtube_scraping --max 30

    # Different channel
    python -m angry_agents.src.scraping.youtube_scraping --channel https://www.youtube.com/@SomeChannel

    # Specific video IDs (comma-separated, skips channel listing)
    python -m angry_agents.src.scraping.youtube_scraping --video-ids dQw4w9WgXcQ,abc123xyz

    # Cap transcript size (default 50000 tokens, ~200k chars)
    python -m angry_agents.src.scraping.youtube_scraping --max-tokens 20000

    # Custom output directory
    python -m angry_agents.src.scraping.youtube_scraping --out data/my_channel

    # Keep only one speaker's lines (1=most words, 2=second-most, etc.)
    python -m angry_agents.src.scraping.youtube_scraping --speaker 1

Flags:
    --channel       Channel URL (default: https://www.youtube.com/@JOk3R1)
    --max           Max videos to fetch from channel listing
    --max-tokens    Stop accumulating transcripts after ~N tokens (default: 50000)
    --out           Output directory (default: data/youtube)
    --video-ids     Comma-separated video IDs; output saved as cicciogamer89.json
    --speaker       Keep only speaker N ranked by word count (1=dominant). Requires
                    manual captions with '- ' turn markers. Ignored for auto-captions.

Output JSON shape per entry:
    {
      video_id, title, upload_date, duration, url,
      transcript: str | null,       # flat text, filtered to --speaker if set
      speaker_count: int | null     # number of detected speakers (null = no turn markers)
    }
"""

import argparse
import json
import re
import time
from pathlib import Path
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

# Matches the leading "- " that YouTube manual captions use to mark speaker turns.
_TURN_RE = re.compile(r'^-\s+')

CHANNEL_URL = "https://www.youtube.com/@JOk3R1"
OUTPUT_DIR = Path("data/youtube")
TRANSCRIPT_LANGS = ["it", "en"]
REQUEST_DELAY = 0.5  # seconds between transcript requests
CHARS_PER_TOKEN = 4
MAX_TOKENS_DEFAULT = 50_000


def get_channel_videos(channel_url: str, max_videos: int | None = None) -> list[dict]:
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_items": f"1-{max_videos}" if max_videos else None,
        "extractor_args": {"youtube": {"lang": ["it"]}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = info.get("entries") or []
    videos = []
    for e in entries:
        if not e or not e.get("id"):
            continue
        videos.append({
            "video_id": e["id"],
            "title": e.get("title") or "",
            "upload_date": e.get("upload_date") or "",
            "duration": e.get("duration"),
            "url": f"https://www.youtube.com/watch?v={e['id']}",
        })
    return videos


def get_videos_by_ids(video_ids: list[str]) -> list[dict]:
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "extractor_args": {"youtube": {"lang": ["it"]}},
    }
    videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for vid_id in video_ids:
            url = f"https://www.youtube.com/watch?v={vid_id}"
            info = ydl.extract_info(url, download=False)
            if not info:
                continue
            videos.append({
                "video_id": info["id"],
                "title": info.get("title") or "",
                "upload_date": info.get("upload_date") or "",
                "duration": info.get("duration"),
                "url": url,
            })
    return videos


def _segment_by_speaker(snippets: list) -> list[dict] | None:
    """
    Split snippets into speaker segments using '- ' turn markers.

    Returns list of {"speaker": "SPEAKER_A"|"SPEAKER_B", "text": str}
    or None if no turn markers found (auto-generated captions).

    Each '- ' prefix starts a new speaker turn. Labels alternate A/B to
    handle the common interview/podcast format where two speakers trade turns.
    Consecutive snippets without a prefix belong to the current speaker.
    """
    segments: list[dict] = []
    current_label: str | None = None
    current_parts: list[str] = []
    turn_index = 0  # increments on each '- ' marker; label = A/B by parity

    for snippet in snippets:
        text = snippet.text.strip()
        if not text:
            continue
        if _TURN_RE.match(text):
            if current_label is not None and current_parts:
                segments.append({"speaker": current_label, "text": " ".join(current_parts)})
            current_label = "SPEAKER_A" if turn_index % 2 == 0 else "SPEAKER_B"
            turn_index += 1
            current_parts = [_TURN_RE.sub("", text).strip()]
        else:
            if current_label is None:
                # snippets before any turn marker → no speaker structure
                return None
            current_parts.append(text)

    if current_label is not None and current_parts:
        segments.append({"speaker": current_label, "text": " ".join(current_parts)})

    return segments if segments else None


def _filter_speaker(segments: list[dict], rank: int) -> str:
    """
    Return transcript text for the speaker ranked by total word count.
    rank=1 → most words (usually the host/main speaker), rank=2 → second-most, etc.
    """
    from collections import Counter
    word_counts: Counter = Counter()
    for seg in segments:
        word_counts[seg["speaker"]] += len(seg["text"].split())

    ranked = [spk for spk, _ in word_counts.most_common()]
    target = ranked[min(rank - 1, len(ranked) - 1)]
    parts = [seg["text"] for seg in segments if seg["speaker"] == target]
    return " ".join(parts)


def _fetch_snippets(video_id: str) -> list:
    """
    Fetch transcript snippets, preferring manual captions over auto-generated.

    Manual captions often contain '- ' speaker-turn markers; auto-generated never do.
    Tries each preferred language for a manual transcript first, then falls back
    to whatever fetch() returns (auto-generated).
    """
    api = YouTubeTranscriptApi()
    try:
        t_list = api.list(video_id)
    except (NoTranscriptFound, TranscriptsDisabled):
        return []

    # prefer manual transcripts in language order
    manual = [t for t in t_list if not t.is_generated]
    for lang in TRANSCRIPT_LANGS:
        for t in manual:
            if t.language_code.startswith(lang):
                return list(t.fetch())

    # fall back to any manual transcript
    if manual:
        return list(manual[0].fetch())

    # fall back to auto-generated
    try:
        return list(api.fetch(video_id, languages=TRANSCRIPT_LANGS))
    except (NoTranscriptFound, TranscriptsDisabled):
        return []


def get_transcript(video_id: str, speaker_rank: int | None = None) -> tuple[str | None, int | None]:
    """
    Fetch transcript for a video.

    Returns (transcript_text, speaker_count).
    - transcript_text: flat string, optionally filtered to one speaker
    - speaker_count: number of detected speakers if turn markers present, else None

    speaker_rank: 1 = keep dominant speaker only, 2 = second-most, etc.
                  None = keep all speakers (interleaved as SPEAKER_A: ... SPEAKER_B: ...)
    """
    snippets = _fetch_snippets(video_id)
    if not snippets:
        return None, None

    segments = _segment_by_speaker(snippets)

    if segments is None:
        return " ".join(s.text for s in snippets), None

    speaker_count = len({seg["speaker"] for seg in segments})

    if speaker_rank is not None:
        return _filter_speaker(segments, speaker_rank), speaker_count

    lines = [f"{seg['speaker']}: {seg['text']}" for seg in segments]
    return "\n".join(lines), speaker_count


def scrape(
    channel_url: str,
    output_dir: Path,
    max_videos: int | None = None,
    max_tokens: int = MAX_TOKENS_DEFAULT,
    speaker_rank: int | None = None,
    name: str = "j0k3r",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Enumerating videos: {channel_url}")
    videos = get_channel_videos(channel_url, max_videos)
    print(f"Found {len(videos)} videos | target ≤{max_tokens:,} tokens\n")

    max_chars = max_tokens * CHARS_PER_TOKEN
    accumulated_chars = 0
    results = []

    for i, video in enumerate(videos, 1):
        if accumulated_chars >= max_chars:
            print(f"\nToken limit reached ({max_tokens:,}). Stopping.")
            break

        transcript, speaker_count = get_transcript(video["video_id"], speaker_rank)
        record = {**video, "transcript": transcript, "speaker_count": speaker_count}
        results.append(record)

        if transcript:
            accumulated_chars += len(transcript)
            approx_tokens = accumulated_chars // CHARS_PER_TOKEN
            spk_info = f" | {speaker_count} spk" if speaker_count else ""
            status = f"{len(transcript.split()):>6} words | total ~{approx_tokens:,} tok{spk_info}"
        else:
            status = "no transcript"

        print(f"[{i:>4}/{len(videos)}] {video['title'][:50]:<50} {status}")
        time.sleep(REQUEST_DELAY)

    out_file = output_dir / f"{name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["transcript"])
    total_tok = accumulated_chars // CHARS_PER_TOKEN
    print(f"\nDone: {ok}/{len(results)} with transcript | ~{total_tok:,} tokens → {out_file}")
    return out_file


def scrape_by_ids(
    video_ids: list[str],
    output_dir: Path,
    max_tokens: int = MAX_TOKENS_DEFAULT,
    speaker_rank: int | None = None,
    name: str = "output",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {len(video_ids)} videos by ID\n")

    max_chars = max_tokens * CHARS_PER_TOKEN
    accumulated_chars = 0
    results = []

    for i, vid_id in enumerate(video_ids, 1):
        if accumulated_chars >= max_chars:
            print(f"\nToken limit reached ({max_tokens:,}). Stopping.")
            break

        url = f"https://www.youtube.com/watch?v={vid_id}"
        ydl_opts = {"quiet": True, "extractor_args": {"youtube": {"lang": ["it"]}}}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        video = {
            "video_id": info["id"],
            "title": info.get("title") or "",
            "upload_date": info.get("upload_date") or "",
            "duration": info.get("duration"),
            "url": url,
        }

        transcript, speaker_count = get_transcript(vid_id, speaker_rank)
        results.append({**video, "transcript": transcript, "speaker_count": speaker_count})

        if transcript:
            accumulated_chars += len(transcript)
            approx_tokens = accumulated_chars // CHARS_PER_TOKEN
            spk_info = f" | {speaker_count} spk" if speaker_count else ""
            status = f"{len(transcript.split()):>6} words | total ~{approx_tokens:,} tok{spk_info}"
        else:
            status = "no transcript"

        print(f"[{i:>4}/{len(video_ids)}] {video['title'][:50]:<50} {status}")
        time.sleep(REQUEST_DELAY)

    out_file = output_dir / f"{name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["transcript"])
    total_tok = accumulated_chars // CHARS_PER_TOKEN
    print(f"\nDone: {ok}/{len(results)} with transcript | ~{total_tok:,} tokens → {out_file}")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="Max videos to scrape from channel")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS_DEFAULT, help="Stop after ~N tokens")
    parser.add_argument("--channel", default=CHANNEL_URL, help="Channel URL")
    parser.add_argument("--out", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--video-ids", default=None, help="Comma-separated video IDs (skips channel scrape)")
    parser.add_argument(
        "--speaker", type=int, default=None, metavar="N",
        help="Keep only speaker N ranked by word count (1=dominant). "
             "Only works for videos with manual captions that use '- ' turn markers.",
    )
    parser.add_argument("--name", default=None, help="Output filename stem (e.g. 'lex_fridman' → lex_fridman.json)")
    args = parser.parse_args()

    if args.video_ids:
        ids = [v.strip() for v in args.video_ids.split(",")]
        name = args.name or "output"
        scrape_by_ids(ids, Path(args.out), args.max_tokens, args.speaker, name)
    else:
        name = args.name or "j0k3r"
        scrape(args.channel, Path(args.out), args.max, args.max_tokens, args.speaker, name)


if __name__ == "__main__":
    main()
