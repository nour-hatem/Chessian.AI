# ARCHITECTURE.md

## Overview

Chessian.AI is a web app with a FastAPI backend and a Next.js frontend. The backend
imports games, analyzes them with Stockfish, stores results in PostgreSQL, and generates
coaching explanations with an LLM. The frontend renders the library, analysis viewer,
opening profile, puzzle trainer and play mode.

    Next.js frontend  --HTTP-->  FastAPI backend  -->  PostgreSQL
                                      |
                                      +--> Stockfish (UCI subprocess)
                                      +--> Groq API (explanations)
                                      +--> Chess.com / Lichess public APIs (import)

## Backend layers

- routers: request validation and response shaping only
- services: business logic
  - importer: Chess.com, Lichess and PGN import, SHA256 dedup of move sequence
  - analyzer: per-move evaluation, classification, accuracy, phase split, critical moments
  - engine: single best-move lookups for play mode
  - explainer: LLM explanation for critical moments
  - sm2: spaced repetition scheduling (pure functions, no I/O)
  - crud: all database access
- models and schemas: persistence and API contracts

## Analysis pipeline

1. Import: fetch games, store PGN, user color, opening name, clock data.
2. Evaluate: scan every position at depth 14, re-search critical moments at depth 20.
   Stockfish access is serialized with a semaphore of 1.
3. Classify: centipawn loss per move mapped to best, good, inaccuracy, mistake, blunder.
4. Aggregate: accuracy per player and per phase, critical moment selection.
5. Explain: LLM call per critical moment, sequential to respect rate limits.
6. Persist and serve through GET /api/analysis/{game_id}.

## Data model

- User: identity and platform usernames
- Game: PGN, players, result, time control, opening, clock data
- GameAnalysis: per-game summary, status (pending, processing, complete, failed)
- MoveAnalysis: per-move evaluation, classification, critical flag
- MoveExplanation: LLM text per move analysis
- Puzzle and PuzzleAttempt: Lichess puzzles and SM-2 state per user

## Frontend structure

- Routes: / , /library, /analysis/[id], /openings, /puzzles, /play
- Shared components: Board (chessground wrapper), EvalBar, EvalChart, MoveList, Library/*
- API base URL from NEXT_PUBLIC_API_URL, default http://localhost:8000

## Known gaps

- Auth is a hardcoded dev user. No registration, sessions or JWT.
- Accuracy uses the Lichess constants on centipawn loss instead of win probability,
  so values are too low. Planned fix: win-probability based accuracy.
- Brilliant classification triggers on negative centipawn loss, which is search noise.
- Phase boundaries are move-count based, not theory-exit and material based.
- tactical_motifs is always null. Motif detection is not implemented.
- Analysis runs as in-process background tasks. A restart loses queued work.
- Dockerfiles exist but were never built or tested.
- No CI. Tests exist only for SM-2.

## Roadmap

1. Win-probability accuracy, corrected classification, typed critical moments
2. Endgame conversion and time-pressure profiles
3. Tactical motif detection with a FEN test suite, then blindspot map
4. Blindspot-driven puzzle selection and weekly plan
5. Real auth and a persistent analysis job queue
6. RAG coach, style profile, opponent preparation

## Design decisions

- Stockfish runs as a subprocess, one at a time, to avoid CPU starvation.
- Only free-tier external services are used.
- Puzzle selection is rating-band plus SM-2 until motif data exists.
