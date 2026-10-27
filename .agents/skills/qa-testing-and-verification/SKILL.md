---
name: qa-testing-and-verification
description: Quality assurance standards, Pytest conventions, known-position chess tests, and Definition of Done verification logging for Chessian.AI.
license: MIT
---

# QA Testing & Verification Standards for Chessian.AI

Guidelines for writing and executing tests across `backend/tests/**` and verifying pull requests.

## 1. Test Suite Commands

Run tests from the `backend/` directory:
```bash
# Run all unit tests
pytest

# Run tests with output
pytest -v

# Run specific test file
pytest tests/test_curriculum.py
```

---

## 2. Chess Logic Testing Rules (Known Positions)

Never use random or empty board states when testing chess evaluation, parsing, or motifs. Always provide known FEN positions:

```python
import chess
from app.services.analyzer import classify_move

# Example: Black makes a blunder allowing a queen fork
FEN_FORK = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"

def test_fork_blunder_classification():
    board = chess.Board(FEN_FORK)
    # verify engine classifies move appropriately
```

---

## 3. Definition of Done Checklist & Log Attachment

Every PR submitted by an agent must include the raw terminal output verifying the following:

1. **Backend Import**:
   ```bash
   python -c "from app.main import app"
   ```
2. **Backend Tests**:
   ```bash
   pytest
   ```
3. **Frontend Typecheck**:
   ```bash
   npx tsc --noEmit
   ```
4. **Frontend Linter**:
   ```bash
   npm run lint
   ```

Never claim a test passed without running it and inspecting the command exit code.
