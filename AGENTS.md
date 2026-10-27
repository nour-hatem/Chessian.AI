# AGENTS.md

Instructions for AI coding agents and human contributors working on Chessian.AI.
Read this file fully before changing anything. See ARCHITECTURE.md for the system design.

## Project summary

Chessian.AI analyzes a chess player's games, finds recurring weaknesses, and explains
critical moments in coaching language. Pipeline: import games, evaluate with Stockfish,
aggregate into patterns, explain with an LLM, train with puzzles.

## Stack

- Backend: FastAPI, async SQLAlchemy, PostgreSQL (asyncpg), Alembic
- Engine: Stockfish over UCI via python-chess
- LLM: Groq (llama-3.1-8b-instant), free tier
- Frontend: Next.js, TypeScript, chessground, chess.js, CSS modules
- Vector store: Qdrant (provisioned, not used yet)

## Repository layout

- backend/app/routers/    HTTP endpoints only, no business logic
- backend/app/services/   business logic (analysis, import, engine, explainer, sm2, crud)
- backend/app/models/     SQLAlchemy models
- backend/app/schemas/    Pydantic request and response models
- backend/alembic/        migrations
- backend/scripts/        one-off and seeding scripts
- backend/tests/          pytest tests
- frontend/src/app/       Next.js routes
- frontend/src/components/ shared UI components
- docs/                   research and design documents

## Commands

Backend (from backend/):
- Run: uvicorn app.main:app --port 8000
- Test: pytest
- Migrate: alembic upgrade head
- Import check: python -c "from app.main import app"

Frontend (from frontend/):
- Run: npm run dev
- Typecheck: npx tsc --noEmit
- Lint: npm run lint

PostgreSQL must be running before the backend starts. Stockfish path is set with
STOCKFISH_PATH (Debian and Ubuntu install it at /usr/games/stockfish).

## Definition of done

A task is done only when all of these pass and the output is attached to the PR:
- python -c "from app.main import app" succeeds
- pytest passes
- npx tsc --noEmit reports zero errors
- Any schema change has an Alembic migration
- New logic has tests (chess logic needs known-position tests)

Never report success on a check you did not run.

## Workflow rules

- One task per branch, one PR per task. Never commit to main.
- Branch names: feat/<topic>, fix/<topic>, docs/<topic>, chore/<topic>
- Commit messages: type(scope): summary, for example fix(analyzer): use win probability
- Keep diffs small and in scope. Do not refactor unrelated code.
- If the task spec is ambiguous or a file outside your scope needs changing, stop and ask.

## Conventions

- Routers call services. Services call crud. Do not put SQL or chess logic in routers.
- Type hints on all Python functions. Strict TypeScript, no `any`.
- CSS modules only. No inline styles, no new CSS frameworks.
- No new dependencies without approval in the issue.
- Comments in English, explaining why, not what.
- Secrets live in .env only. Never commit keys.

## Chess correctness rules

- Evaluations are centipawns from White's perspective. Convert to the mover's
  perspective before computing loss.
- Do not compare analyses made at different depths. Store depth with every analysis.
- Skip variant games (Chess960 and others). Stockfish setup here does not support them.
- LLM explanations must only state facts derivable from the supplied FEN, moves and
  engine lines. Never let the model invent piece placement.
- Never fake data. If a feature depends on data that does not exist yet
  (for example tactical_motifs, currently always null), say so instead of simulating it.

## Agent roles

- backend: backend/app/** and backend/alembic/**
- frontend: frontend/src/**
- qa: backend/tests/** and CI configuration
- docs: *.md and docs/**
- devops: Dockerfiles, docker-compose.yml, .github/**

Stay inside your role's paths. Role definitions live in .agents/ (one file per role).

## Do not

- Edit migrations that were already merged. Add a new one.
- Disable or weaken a test to make it pass.
- Commit generated files, .env, pgdata/, node_modules/ or model weights.
- Claim a task works without running the commands above.
