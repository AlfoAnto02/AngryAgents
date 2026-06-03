# Sprint 4 — Kevin Shimaj

*Week W22 (May 26–Jun 1). Reconstructed from commit history.*

## What I did
- Improved the evaluation framework to score batches of chats, not just one;
  documented batch eval; redefined/pruned several metrics and wired the new
  metrics into the UI (incl. MAD between judge types for the admin).
- Modified persona-identification metric scripts.
- MCP layer: read/write tools, UI routes, and an unauthenticated route for
  MCP/LLM agents to create DM/group chats with explicit participant IDs and
  optional `created_by`. Replaced `create_chat` with `create_full_chat`
  (DM/group auto-detect); added `created_by` to `create_message` so the LLM can
  post as the user; added preview/`confirm_stop_chat` to halt the agent loop.
- Added a `status` field to chats so `PATCH /chats/{id}` can stop a running chat.
- Prevented MCP context overflow when listing agents (~575 kB → ~5 kB; full
  profiles still available by id/slug).
- Tuned DM/group persona templates.

## What blocked me
- MCP context overflow when listing all agents — fixed by trimming the list
  payload and keeping full profiles behind id/slug lookups.

## What's next
- Wire the UI to batch evaluation; remove the unused deliberation metrics.
