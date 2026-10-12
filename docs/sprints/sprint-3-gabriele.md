# Sprint 3 — Gabriele Fronzoni

*Week W21 (May 19–25). Reconstructed from commit history.*

## What I did
- Improved the PDF scraper (few artifacts, multi-file folders) and the YouTube
  scraper; added a Twitter scraping script.
- Reworked the persona-extraction prompt; the script now calls a GPT model and
  estimates per-call cost. Built and rebuilt many persona profiles (movies +
  YouTube), retiring old ones.
- Modified agent responses to also emit plain messages, not only JSON.
- Wired backend↔frontend calls to persist data via the DB API; fixed admin
  password hashing.

## What blocked me
- Persona quality required several extraction/profile rebuild cycles.
- API cost of the extraction calls drove the move to cost estimation per call.

## What's next
- Add a smarter integration model to the extraction pipeline; stand up the
  report structure and Week-3 progress report.
