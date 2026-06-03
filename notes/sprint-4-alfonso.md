# Sprint 4 — Alfonso Antognozzi

*Week W22 (May 26–Jun 1). Reconstructed from commit history.*

## What I did
- Added the Hungarian algorithm for persona identification.
- Added token-usage reporting; modified RAG indexing (retrieve by field ×
  weight); tuned the judge prompt.
- Reduced judging time with an API-call timeout to avoid bottlenecking.
- Implemented the admin dashboard UI and wired judge evaluations end-to-end
  (judging phase wired to the UI); fixed UI routes and persona characters.

## What blocked me
- Judging latency bottleneck — addressed with per-call timeouts.

## What's next
- Group-fidelity score, DB v4, dynamic candidate pool, judge-template/metric
  tuning for persona ID, individual-fidelity token tracking.
