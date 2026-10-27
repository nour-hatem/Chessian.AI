---
name: postgresql-database-design
description: Schema design, indexing, and Alembic migration workflows for PostgreSQL in Chessian.AI. Use when creating or altering database models, writing migrations, or optimizing SQL queries.
license: MIT
---

# PostgreSQL & Alembic Database Guidelines for Chessian.AI

Rules and best practices for relational database models and schema evolution under `backend/app/models/` and `backend/alembic/`.

## 1. Schema Conventions

- **Naming**: Use `snake_case` for table names, column names, constraints, and indexes. Table names should be pluralized (e.g. `games`, `game_analyses`, `puzzles`).
- **Primary Keys**: Use standard integers or UUIDs.
- **Foreign Keys**: Always create explicit foreign keys with indexed columns (e.g. `game_id` with `index=True`).
- **Timestamps**: Store all timestamps in UTC with timezone (`DateTime(timezone=True)`).
- **JSONB**: Use PostgreSQL JSONB for flexible payload storage (such as clock lists or raw PGN headers), but keep queryable entities (such as ECO codes, ratings, winner) in indexed scalar columns.

---

## 2. Alembic Migration Rules

1. **Never edit an existing merged migration file.** Create a new revision:
   ```bash
   alembic revision --autogenerate -m "feat: add tactical_motifs to move_analyses"
   ```
2. **Review auto-generated code**:
   - Inspect the generated migration file in `backend/alembic/versions/`.
   - Ensure both `upgrade()` and `downgrade()` are completely implemented and reversible.
   - Verify that default values and nullable flags are correctly set.
3. **Execute migrations**:
   ```bash
   alembic upgrade head
   ```

---

## 3. Query Optimization Checklist

- Verify queries filter on indexed columns.
- Avoid N+1 queries by using `selectinload()` on relationships in async SQLAlchemy.
- When querying large game libraries, always use pagination (`limit` and `offset` or cursor-based pagination).
