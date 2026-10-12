# Sprint 3 — Alfonso Antognozzi

*Week W21 (May 19–25). Reconstructed from commit history.*

## What I did
- Stood up FastAPI for the API layer + Swagger; added gitignore and the
  requirements file so the app launches.
- Added the test suite covering all repo/service methods (~170 tests).
- Implemented DB v3 + the authorization layer; baseline JWT authentication
  (config, models, repository method); changed the chat-message hashing method.
- First RAG implementation; updated RAG chunks for new persona profiles.
- First official UI for the application.
- Implemented 20 judges with parallel calls (removed looping to cut cost);
  refactored the evaluation method to emit JSON reports coherent with the RAG
  system; judge score became a list of floats.
- Maintained the progress report.

## What blocked me
- Judge cost: the looping approach was expensive, so I parallelized the 20-judge
  calls and dropped the loop.

## What's next
- Persona-identification metrics (Hungarian assignment), token-usage reporting,
  RAG indexing improvements, judge-prompt tuning.
