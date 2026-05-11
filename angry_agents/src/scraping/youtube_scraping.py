"""
Scrape YouTube channel videos: metadata + transcripts via yt-dlp and youtube-transcript-api.

Usage:
    python -m angry_agents.src.scraping.youtube_scraping
    python -m angry_agents.src.scraping.youtube_scraping --max 50
"""

import argparse
import json
import time
from pathlib import Path
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

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


def get_transcript(video_id: str) -> str | None:
    api = YouTubeTranscriptApi()
    try:
        transcript = api.fetch(video_id, languages=TRANSCRIPT_LANGS)
        return " ".join(snippet.text for snippet in transcript)
    except (NoTranscriptFound, TranscriptsDisabled):
        return None


def scrape(
    channel_url: str,
    output_dir: Path,
    max_videos: int | None = None,
    max_tokens: int = MAX_TOKENS_DEFAULT,
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

        transcript = get_transcript(video["video_id"])
        record = {**video, "transcript": transcript}
        results.append(record)

        if transcript:
            accumulated_chars += len(transcript)
            approx_tokens = accumulated_chars // CHARS_PER_TOKEN
            status = f"{len(transcript.split()):>6} words | total ~{approx_tokens:,} tok"
        else:
            status = "no transcript"

        print(f"[{i:>4}/{len(videos)}] {video['title'][:50]:<50} {status}")
        time.sleep(REQUEST_DELAY)

    out_file = output_dir / "cicciogamer89.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["transcript"])
    total_tok = accumulated_chars // CHARS_PER_TOKEN
    print(f"\nDone: {ok}/{len(results)} with transcript | ~{total_tok:,} tokens → {out_file}")
    return out_file


def scrape_by_ids(video_ids: list[str], output_dir: Path, max_tokens: int = MAX_TOKENS_DEFAULT) -> Path:
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

        transcript = get_transcript(vid_id)
        results.append({**video, "transcript": transcript})

        if transcript:
            accumulated_chars += len(transcript)
            approx_tokens = accumulated_chars // CHARS_PER_TOKEN
            status = f"{len(transcript.split()):>6} words | total ~{approx_tokens:,} tok"
        else:
            status = "no transcript"

        print(f"[{i:>4}/{len(video_ids)}] {video['title'][:50]:<50} {status}")
        time.sleep(REQUEST_DELAY)

    out_file = output_dir / "cicciogamer89.json"
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
    args = parser.parse_args()

    if args.video_ids:
        ids = [v.strip() for v in args.video_ids.split(",")]
        scrape_by_ids(ids, Path(args.out), args.max_tokens)
    else:
        scrape(args.channel, Path(args.out), args.max, args.max_tokens)


if __name__ == "__main__":
    main()
