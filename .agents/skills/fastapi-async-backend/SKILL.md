---
name: fastapi-async-backend
description: Architecture rules and best practices for Chessian.AI FastAPI backend. Covers async SQLAlchemy 2.0 with asyncpg, service-layer isolation, Pydantic v2 schemas, Stockfish subprocess control, and error handling.
license: MIT
---

# FastAPI Async Backend Architecture for Chessian.AI

Guidelines and patterns for backend development in `backend/app/**`.

## 1. Layered Architecture (Enforced)

Never violate architectural boundaries:

```
[ HTTP Client ]
      │
      ▼
routers/          <── HTTP contracts, status codes, query params, dependency injection
      │
      ▼
services/         <── Business logic, engine coordination, LLM explanations, SM-2 logic
      │
      ▼
crud/             <── Database queries, inserts, updates via async SQLAlchemy
      │
      ▼
models/ (DB)      <── SQLAlchemy declarative models
```

### Rules:
1. **Routers never execute SQL or import chess engines directly.** They call a service function or crud function.
2. **Services never touch FastAPI request objects directly.** Accept typed domain arguments and return domain models or schemas.
3. **Database access is isolated in `app/services/crud/` (or `app/crud/`).**

---

## 2. Async SQLAlchemy 2.0 & asyncpg Best Practices

- Always use SQLAlchemy 2.0 `select()` syntax:
  ```python
  from sqlalchemy import select
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.models.game import Game

  async def get_game_by_id(db: AsyncSession, game_id: int) -> Game | None:
      result = await db.execute(select(Game).where(Game.id == game_id))
      return result.scalar_one_or_none()
  ```
- Use `selectinload` or `joinedload` for relationships when needed to prevent `MissingGreenlet` errors in async contexts.
- Transactions: Let the session dependency manage commits/rollbacks or wrap critical operations in `async with db.begin():`.

---

## 3. Subprocess & Stockfish Engine Management

- **Process Isolation**: Stockfish is spawned via `python-chess` UCI.
- **CPU Starvation Prevention**: All engine evaluations MUST be governed by an `asyncio.Semaphore(1)` to ensure only one heavy search runs at a time.
- **Non-blocking Execution**: Run synchronous engine compute inside `asyncio.to_thread` or async UCI protocol to prevent blocking the FastAPI event loop.

---

## 4. Verification Check Before PR

Always verify backend changes locally:
```bash
# 1. Import verification
python -c "from app.main import app"

# 2. Run unit tests
pytest
```
