"""
Scrape tweets from a Twitter/X account using twscrape.
Output: JSON file compatible with extract_profile.py --type podcast.

Requires a free Twitter/X account for authentication.
Add it once with --add-account, then scrape freely.

Usage:
    # First time: add a Twitter account via browser cookies (password login blocked by Cloudflare)
    python -m angry_agents.src.scraping.twitter_scraping --add-account

    # Scrape a profile
    python -m angry_agents.src.scraping.twitter_scraping \\
        --handle elonmusk --name elon_musk

    # Limit tweet count
    python -m angry_agents.src.scraping.twitter_scraping \\
        --handle elonmusk --name elon_musk --max 300

    # Exclude retweets
    python -m angry_agents.src.scraping.twitter_scraping \\
        --handle elonmusk --name elon_musk --no-rts

Flags:
    --handle        Twitter/X handle (without @)
    --name          Output filename stem (e.g. 'elon_musk' → elon_musk.json)
    --max           Max tweets to fetch (default: 500)
    --no-rts        Exclude retweets (default: include)
    --batch-size    Tweets per episode batch for extract_profile (default: 100)
    --out           Output directory (default: data/twitter)
    --accounts-db   Path to twscrape accounts DB (default: data/twitter/accounts.db)
    --add-account   Interactive: add a Twitter account to the auth pool

Output JSON shape (list of batches, compatible with extract_profile.py --type podcast):
    [
      {
        "title": "@handle tweets 1-100 (2024-01-01 to 2024-03-15)",
        "transcript": "tweet text\\ntweet text\\n...",
        "tweet_count": 100,
        "tweets": [
          {"tweet_id": "...", "text": "...", "date": "...",
           "likes": 0, "retweets": 0, "replies": 0, "url": "..."}
        ]
      }
    ]
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

_URL_RE = re.compile(r'https?://\S+')

OUTPUT_DIR = Path("data/twitter")
TWEETS_PER_BATCH = 100
MAX_TWEETS_DEFAULT = 500


# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------

async def _add_account_interactive(accounts_db: Path) -> None:
    """
    Add a Twitter/X account via browser cookies (recommended — bypasses Cloudflare).

    How to get cookies:
      1. Log into x.com in your browser
      2. Open DevTools → Application → Cookies → https://x.com
      3. Install "Cookie-Editor" extension and click Export → JSON
         OR manually copy the cookie header string from a request in the Network tab
      4. Paste the JSON array or Netscape/header string when prompted
    """
    from twscrape import API
    api = API(str(accounts_db))

    print("Add a Twitter/X account via browser cookies.")
    print("Cookies bypass Cloudflare — password login is blocked by Twitter.\n")
    print("How to get your cookies:")
    print("  1. Log into x.com in your browser")
    print("  2. Install 'Cookie-Editor' extension")
    print("  3. Click Export → JSON, copy the result")
    print("  OR: DevTools → Network → any x.com request → copy 'cookie:' header value\n")

    username = input("Your Twitter username (without @): ").strip()
    print("Paste cookies JSON (or header string), then press Enter twice:")

    lines = []
    while True:
        line = input()
        if line == "" and lines:
            break
        lines.append(line)
    cookies = "\n".join(lines).strip()

    if not cookies:
        print("No cookies provided — aborted.")
        return

    await api.pool.add_account_cookies(username, cookies)
    stats = await api.pool.stats()
    print(f"\nDone. Pool stats: {stats}")


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

async def _scrape(
    handle: str,
    max_tweets: int,
    include_rts: bool,
    accounts_db: Path,
) -> tuple[list[dict], str]:
    """
    Fetch tweets for a handle.
    Returns (tweets, display_name).
    Each tweet: {tweet_id, text, date, likes, retweets, replies, url}.
    """
    from twscrape import API

    api = API(str(accounts_db))

    stats = await api.pool.stats()
    if stats.get("total", 0) == 0:
        print("No accounts in pool. Run with --add-account first.")
        sys.exit(1)

    print(f"Looking up @{handle}...")
    user = await api.user_by_login(handle)
    if user is None:
        print(f"User @{handle} not found.")
        sys.exit(1)

    display_name = user.displayname or handle
    print(f"Found: {display_name} (@{handle}) | fetching up to {max_tweets} tweets\n")

    tweets = []
    async for tweet in api.user_tweets(user.id, limit=max_tweets):
        if not include_rts and tweet.retweetedTweet is not None:
            continue
        tweets.append({
            "tweet_id": str(tweet.id),
            "text": tweet.rawContent,
            "date": tweet.date.strftime("%Y-%m-%d"),
            "likes": tweet.likeCount,
            "retweets": tweet.retweetCount,
            "replies": tweet.replyCount,
            "url": tweet.url,
        })
        print(f"\r  Fetched {len(tweets)} tweets...", end="", flush=True)
        if len(tweets) >= max_tweets:
            break

    print()
    return tweets, display_name


# ---------------------------------------------------------------------------
# Batch into extract_profile-compatible episodes
# ---------------------------------------------------------------------------

def _batch_tweets(tweets: list[dict], batch_size: int, handle: str) -> list[dict]:
    """
    Group tweets into fixed-size batches.

    Each batch becomes one "episode" compatible with load_podcast_transcripts:
    transcript = newline-separated tweet texts.
    """
    episodes = []
    for i in range(0, len(tweets), batch_size):
        batch = tweets[i : i + batch_size]
        dates = [t["date"] for t in batch]
        date_range = f"{min(dates)} to {max(dates)}" if dates else ""
        # Strip URLs from transcript — they pollute vocabulary extraction.
        # Raw text with URLs is preserved in the tweets array.
        transcript_lines = [
            _URL_RE.sub("", t["text"]).strip()
            for t in batch
        ]
        transcript_lines = [l for l in transcript_lines if l]  # drop URL-only tweets
        episodes.append({
            "title": f"@{handle} tweets {i + 1}–{i + len(batch)} ({date_range})",
            "transcript": "\n".join(transcript_lines),
            "tweet_count": len(batch),
            "tweets": batch,
        })
    return episodes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Twitter/X account tweets → JSON for extract_profile.py.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # first-time setup\n"
            "  %(prog)s --add-account\n\n"
            "  # scrape\n"
            "  %(prog)s --handle elonmusk --name elon_musk --max 500 --no-rts\n"
        ),
    )
    parser.add_argument("--handle", default=None, help="Twitter/X handle (without @)")
    parser.add_argument("--name", default=None, help="Output filename stem")
    parser.add_argument("--max", type=int, default=MAX_TWEETS_DEFAULT,
                        help=f"Max tweets to fetch (default: {MAX_TWEETS_DEFAULT})")
    parser.add_argument("--no-rts", action="store_true", help="Exclude retweets")
    parser.add_argument("--batch-size", type=int, default=TWEETS_PER_BATCH,
                        help=f"Tweets per episode batch (default: {TWEETS_PER_BATCH})")
    parser.add_argument("--out", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--accounts-db", default=None,
                        help="Path to twscrape accounts DB (default: <out>/accounts.db)")
    parser.add_argument("--add-account", action="store_true",
                        help="Interactive: add a Twitter account to the auth pool")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    accounts_db = Path(args.accounts_db) if args.accounts_db else out_dir / "accounts.db"

    if args.add_account:
        asyncio.run(_add_account_interactive(accounts_db))
        return

    if not args.handle:
        parser.error("--handle required (or use --add-account for first-time setup)")

    name = args.name or args.handle
    out_file = out_dir / f"{name}.json"

    tweets, _ = asyncio.run(
        _scrape(args.handle, args.max, not args.no_rts, accounts_db)
    )

    if not tweets:
        print("No tweets fetched.")
        sys.exit(1)

    episodes = _batch_tweets(tweets, args.batch_size, args.handle)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

    total_tok = sum(len(e["transcript"]) for e in episodes) // 4
    print(f"\nDone: {len(tweets)} tweets | {len(episodes)} batches | ~{total_tok:,} tokens → {out_file}")
    print(f"\nExtract profile:")
    print(f"  python -m angry_agents.src.agents.personas.extract_profile \\")
    print(f"      --input {out_file} \\")
    print(f"      --name {name} \\")
    print(f"      --type podcast")


if __name__ == "__main__":
    main()
