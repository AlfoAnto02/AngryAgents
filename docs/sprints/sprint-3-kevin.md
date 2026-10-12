# Sprint 3 — Kevin Shimaj

*Week W21 (May 19–25). Reconstructed from commit history.*

## What I did
- First implementation of the chat simulation (initially on Ollama); it now uses
  the extracted personas, hashes `persona_id`/`persona_name` for anonymity, and
  computes message embeddings with a drift threshold to redirect the agent.
- First implementation of the evaluation scripts; documented how eval works
  (`EVAL.md`) and pruned the metrics we decided not to keep.
- Implemented the MCP layer and documented its setup.
- Documented how the YouTube scraping script works; finalized the eval
  presentation.

## What blocked me
- Several proposed eval metrics turned out useless and were removed after
  thinking them through.

## What's next
- Extend eval from single-chat to batches; build out MCP read/write tools.
