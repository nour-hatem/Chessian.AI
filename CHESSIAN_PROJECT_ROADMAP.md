# Chessian.AI: Project Audit and 12-Month Product Roadmap

**Living document · repository audit snapshot: 2026-10-30 · planning horizon: 2026-11 through 2027-10**

This document separates observed repository facts from recommendations. Evidence labels mean: **Verified working** = exercised locally or covered by a passing test; **Verified present** = implementation exists but the whole behavior was not exercised; **Claimed only** = described in project documentation or planning text, without implementation evidence; **Missing** = no implementation found in the reviewed paths. A passing local check does not imply a deployed service works.

## 1. Executive summary

Chessian.AI already has the outline of its intended product: game imports, per-move Stockfish analysis, explanations, opening aggregates, puzzles with SM-2, and play against Stockfish. It is a monolith with a useful service/router split, a MIT license, migrations, a CI workflow, and only two small backend test modules. The differentiated product is not another eval graph. It is a trustworthy loop from a player's own games, to measured recurring weaknesses, to targeted practice, and then to a re-test.

The first month must establish trustworthy measurements before growing the coach. Correct accuracy and classification, record and compare analysis settings, test known positions, make a fresh clone runnable, and turn CI into an honest gate. Then measure endgame conversion and clock behavior, add validated tactical motifs, use those features for training, and only then expand coaching. Authentication, durable jobs, user-owned records, privacy, and self-hosting are product foundations, not late polish.

This plan assumes one student developer using small, reviewable AI-assisted PRs. It does not assume weekly feature throughput from a staffed team. Monthly milestones are targets; if validation or school workload slips, defer experimental work and protect correctness, data ownership, and a reproducible release.

## 2. Audit scope and method

Read-only discovery covered the root and frontend instructions, `README.md`, `ARCHITECTURE.md`, `docs/feature-research.md`, role files under `.agents/`, backend routes/services/models/migrations/scripts/tests, frontend routes/components, environment template, Dockerfiles, Compose, CI, license, and repository directories. Source paths and line references below refer to the snapshot inspected on 2026-10-30. Existing user changes in `frontend/src/app/openings/page.tsx` and `openings.module.css` were left intact.

Local checks run: backend app import, `pytest` with `GROQ_API_KEY` blank, frontend typecheck, frontend lint, and `docker compose config -q`. The first unmodified pytest invocation entered the curriculum summary provider call because a local Groq key was configured; it stalled and was interrupted. The blank-key run completed all 15 tests. Compose validation parses configuration; it does not build images, start PostgreSQL, migrate a database, or prove a working stack. No migrations, installs, builds, database startup, or external game imports were run. The unintended test provider request is the only external call attempted during validation.

To close the end-to-end verification gap on a disposable local setup, first provide a configured `.env` with an empty `GROQ_API_KEY`, then run `docker compose up --build -d`, `docker compose ps`, and `curl -fsS http://localhost:8000/api/health`. Load the documented demo PGN through `/library`, start analysis, and verify status/result in `/analysis/{game_id}`; import platform games only with an explicit username and acceptance of the provider request. Run `docker compose exec backend alembic upgrade head` only against the disposable database. For puzzle DB/UI verification, seed data only after declaring the currently missing `zstandard` dependency in a separate approved task; then run `docker compose exec backend python -m scripts.seed_puzzles`. A live Stockfish play check requires `STOCKFISH_PATH` to resolve inside the container.

External sources were checked on 2026-10-30. They are linked in Section 28. Provider free tiers, product features, API limits, and model availability can change and must be rechecked before implementing any hosted integration.

## 3. Product and user thesis

**Verified product intent:** README and architecture documents describe game import, Stockfish review, cross-game patterns, plain-language explanations, and puzzle recommendations. The current app implements much of that workflow, but diagnosis and measured training impact are not yet established.

**Target user recommendation:** self-directed club and online players roughly 800–1800 rapid/blitz who have a usable game history and want to answer: “What recurring mistake costs me games, and what should I practice next?” This band is a product hypothesis, not an observed user segment. Ask early testers to validate it. Newer players need simple, high-confidence tactical and conversion feedback; stronger players need precise lines and enough evidence to challenge the diagnosis.

**Differentiation to validate:** private, inspectable, self-hostable cross-game diagnosis whose recommendations link back to concrete games and moves, followed by practice and later re-testing. Do not claim that current Chess.com or Lichess tools cannot do aggregate insights: Lichess offers Chess Insights and mistake learning, and Chess.com offers Game Review and Insights. Compete on data portability, reproducibility, transparent evidence, and the connection between a player's recurring errors and practice, not on a generic coach persona.

## 4. Repository evidence inventory

| Capability / claim | Evidence and confirmation | Status |
|---|---|---|
| FastAPI + async SQLAlchemy + PostgreSQL + Alembic | `backend/app/main.py:22-47`, `backend/app/database.py:13-27`, `backend/alembic/versions/0001_initial_schema.py` | Verified present; import check passed, DB operation not run |
| Stockfish UCI and serialized search | `backend/app/services/analyzer.py:12-15,125-127`; `backend/app/services/engine.py:8-10,80-97` shares the semaphore | Verified present; live engine analysis not run |
| Game import from Lichess, Chess.com, and PGN | `backend/app/routers/import_.py:67-265`, `backend/app/services/importer.py:15-149`; frontend `frontend/src/components/Library/ImportPanel.tsx:26-97` | Verified present; external provider calls not exercised |
| SHA256 import deduplication | `backend/app/services/importer.py:154-165`; importer routes check hash before create. Hash input includes both player usernames plus UCI moves, not only the move sequence. | Verified present; dedup path not exercised here; semantics differ from the prompt's claim |
| User-side identification including old imports | `backend/app/services/crud.py:70-110` remembers platform handles and falls back to most-common game username | Verified present; heuristic can misidentify imported mixed-owner archives and needs confirmation UX |
| Per-move analysis, classification and critical selection | `backend/app/services/analyzer.py:55-79,92-320`; persistence in `backend/app/services/crud.py:352-410` | Verified present; chess correctness tests missing |
| Clock annotation extraction | `backend/app/services/analyzer.py:119-123,173-185` reads `%clk` and derives elapsed time after a prior same-color clock sample | Verified present; first move and increment edge cases lack tests |
| Mate score behavior | `backend/app/services/analyzer.py:82-89` collapses any mate to ±1000 CP; models have CP fields but no mate-distance/score-type field | Verified present; loss of mate-distance and terminal-score semantics |
| Two-tier analysis at scan 14 / critical 20 | Normal API defaults to 20 in `backend/app/routers/analysis.py:115-120`; it calls `analyze_game(...depth=depth)` without a separate critical depth. Analyzer default is 20/20 (`backend/app/services/analyzer.py:92-97`). | Claimed only for normal API; actual default is depth 20, critical depth 20, so no second-pass depth increase |
| Analysis persistence and explanations | `backend/app/routers/analysis.py:22-112,164-217`; models include `MoveExplanation` (`backend/app/models/__init__.py:122-135`) | Verified present; provider generation not verified; explanations are optional when a key exists |
| Opening repertoire stats and drill-down | `/api/games/openings/repertoire` in `backend/app/routers/games.py:99-121`; aggregation `backend/app/services/crud.py:471-587`; frontend `frontend/src/app/openings/page.tsx` and library filter in `frontend/src/app/library/page.tsx:83-110` | Verified present; API/database workflow not executed |
| Puzzle corpus seed definition | `backend/scripts/seed_puzzles.py:42-55` targets 3,100 Lichess rows across seven bands; model and migration in `backend/app/models/__init__.py:138-189`, `backend/alembic/versions/0002_puzzle_tables.py` | Verified present; current database row count and seed execution not checked |
| Puzzle trainer and SM-2 update | `backend/app/routers/puzzles.py:84-141,151-242`; frontend `frontend/src/app/puzzles/page.tsx:84-140,154-255`; pure algorithm `backend/app/services/sm2.py`; tests in `backend/tests/test_sm2.py` | Verified present; algorithm Verified working (15-test suite includes SM-2 cases); end-to-end DB/UI not run |
| Play against Stockfish | `backend/app/routers/play.py:55-82`, `backend/app/services/engine.py:55-130`; frontend `frontend/src/app/play/page.tsx:92-150` | Verified present; live engine not run. Frontend falls back to random legal move on endpoint failure |
| Coach and weekly plan | `/api/plan` (`backend/app/routers/plan.py:17-32`), `backend/app/services/curriculum.py`; frontend `/plan`. `/coach` is a placeholder (`frontend/src/app/coach/page.tsx`). | Plan Verified present; coach is placeholder, not a conversational coach |
| Accuracy formula | `backend/app/services/analyzer.py:71-79` applies constants to average centipawn loss | Verified present and confirmed incorrect relative to Lichess's stated formula |
| Negative-loss “brilliant” | `classify_move()` at `backend/app/services/analyzer.py:55-68`; analyzer clamps CPL with `max(0, ...)` at `164-168` | Branch is present but effectively unreachable in this analyzer; actual classification remains CP-threshold-based |
| Phase definitions | `backend/app/services/analyzer.py:236-257` assigns first and last 20 plies by index | Verified present; not theory-exit/material based |
| Critical moment types | `backend/app/services/analyzer.py:259-263` selects five highest CPL over 50 | Verified present; swing/missed-win/collapse/escape types missing |
| Tactical motif data | Column exists (`backend/app/models/__init__.py:115`), CRUD stores `mv.get("tactical_motifs")` (`backend/app/services/crud.py:403`), but `MoveEval` has no such field and no detector was found | Missing detector; persisted field remains null in current analysis path |
| Authentication | Routers call `ensure_dev_user`; fixed ID and `dev_user` in `backend/app/services/auth.py:15-40` | Verified present as a single dev identity; registration/session/JWT absent |
| Analysis job durability | `backend/app/routers/analysis.py:7,22-37,148-160` uses FastAPI `BackgroundTasks` | Verified present; in-process only, no restart recovery or queue |
| Variant filtering | Import parser reads PGN but no standard-variant filter found; analyzer parses `game.board()` and sends it to Stockfish | Missing import rejection; Chess960/variant behavior unverified and unsafe to accept |
| CI | `.github/workflows/ci.yml` runs backend install/import/pytest and frontend install/typecheck/lint on PRs to `main` | Verified present; local equivalents passed as recorded in Section 2; remote Actions not run |
| Documentation claims vs runtime | `README.md` lists Claude or Groq and Qdrant embeddings; runtime `backend/app/services/explainer.py` calls Groq only, and no Qdrant reference/dependency/service was found. `frontend/src/app/plan/page.tsx` and `/api/plan` are present, while `/coach` is a placeholder. | README is stale/overbroad; plan is present, conversational coach is missing |
| Docker | root Compose and both Dockerfiles exist; `docker compose config -q` passed | Syntax Verified working; image builds and first boot unverified |
| License and open-source entry points | `LICENSE` is MIT; PR template exists. No `CONTRIBUTING.md`, issue templates, explicit privacy/deletion policy, or public demo seed PGN was found. `data/test_game.pgn` exists locally, but `*.pgn` is ignored; whether it is tracked was not verified. | MIT Verified present; readiness gaps remain |
| Qdrant | Local `qdrant/` and `storage/` directories exist, but no app code, dependency, or Compose service references Qdrant | App integration Missing; whether an outside-of-compose local service is active is unknown |

## 5. End-to-end workflow traces

| Flow | UI → API → service/data → response | Audit result |
|---|---|---|
| Import → analyze → explanation viewer | `ImportPanel` posts `/api/import/{lichess,chesscom}` or `/api/import/pgn`; router assigns dev user, fetches/parses, hashes and inserts via CRUD. Library starts `POST /api/analysis/{id}`; the router schedules an in-process task, analyzer evaluates, CRUD saves summary/moves, optional Groq explanations are saved. Analysis page fetches game metadata, analysis and PGN; response joins move rows with explanation text. | Full code path present; not exercised against PostgreSQL, provider APIs, or Stockfish. Polling can hang on stale processing records after restart. |
| Openings → repertoire stats → game drill-down | `/openings` fetches `/api/games/openings/repertoire`; route resolves usernames and calls `crud.get_opening_repertoire`, which groups completed analyzed games by ECO/name and calculates user W/L/D and accuracy. UI links a selected ECO to `/library?opening=...`; library sends `opening_eco` filter. | Full code path present. Accuracy remains unreliable until the metric migration. User identity fallback is inferred and should be surfaced as uncertain. |
| Solve puzzle → SM-2 | Puzzle page fetches `/api/puzzles/next`, applies setup move, validates user UCI against solution line, then posts one result to `/api/puzzles/{id}/attempt`; router maps correct to quality 3 and incorrect to 0, calls pure `update_sm2`, updates `PuzzleAttempt`, commits. | Full code path present; SM-2 pure tests pass. DB/UI path and retention behavior are unverified. `time_spent_ms` is accepted but discarded. |
| Play a move against engine | `play/page.tsx` posts current FEN and difficulty to `/api/play/move`; router validates via `get_engine_move`, which uses Stockfish under the analyzer semaphore and responds with SAN/UCI/eval. Client applies SAN. | Full code path present; runtime engine path not exercised. UI chooses a fallback random legal move on backend failure, which risks presenting non-engine play as an equivalent game. |

## 6. Existing feature pages and product truth

| UI surface | Current evidence | Roadmap treatment |
|---|---|---|
| Landing, library, game analysis | Routes exist under `frontend/src/app`; library imports and polls analysis; analysis renders eval graph, move list, accuracy and critical moments | Core workflow exists in code. Reposition as “analysis available” until metrics are corrected and engine is run end to end. |
| Openings | `frontend/src/app/openings/page.tsx`, API aggregation path in Section 5 | Existing feature, not future work. Fix trust and identity edge cases before adding theory exploration. |
| Puzzles | `/puzzles` consumes seeded Lichess data and SM-2 | Existing baseline. Blindspot-based selection is future work because game motif labels are missing. |
| Play | `/play` uses backend Stockfish route and client chess.js | Existing training mode. Not a substitute for diagnostics; clock display is not server-recorded training-game evidence. |
| Plan | `/plan` calls a curriculum based on currently flawed accuracy/phase metrics; task completion uses process memory (`services/curriculum.py:30-50`) | Exists but its recommendations are not trustworthy enough to market as adaptive. Correct foundations first. |
| Coach | `/coach` contains placeholder/coming-soon content | No conversational game-history coach exists. Defer until profile, queryable evidence, privacy, and grounding are in place. |

## 7. Product research and feature triage

`docs/feature-research.md` is an idea inventory, not a specification. It lists 58 concepts, but several are expensive, data-hungry, privacy-sensitive, or already covered by established platforms. Defer computer vision, webcam/eye tracking, biometrics, real-time psychological inference, GM style clones, social leaderboards, speculative opening novelty discovery, and large human-move models. Their likely data, model, compute, moderation, and maintenance costs do not fit a solo free-only project.

Prioritize evidence-rich, explainable work: evaluation correctness; imports and user identity; durable analysis; conversion and clock metrics; validated motif labels; blindspot-linked review puzzles; a re-test loop; clean self-hosting. A rating estimate or promised Elo gain is out of scope. Avoid fabricated claims such as “70% of losses” or “+60 Elo gain” unless a reproducible dataset supports them.

## 8. Technical debt register

| ID | Debt and evidence | User/product risk | Recommended response |
|---|---|---|---|
| TD-01 | Accuracy constants consume CP loss (`analyzer.py:71-79`); mate is flattened to ±1000 CP (`82-89`) | Misleading accuracy and every profile/plan built on it | Replace with mover-perspective win-probability loss; preserve raw mate/depth metadata and use bounded conversion only at metric boundary |
| TD-02 | CP-only labels; negative branch unreachable (`55-68`, `164-171`) | “Brilliant” semantics wrong; no missed-win or forced-move representation | Start with transparent CPL and WDL change bins; reserve subjective labels until criteria and tests exist |
| TD-03 | Phase segmentation by first/last 20 plies (`236-257`) | Phase feedback misattributes late opening/early endgame | Persist theory exit and deterministic material phase markers, with unknown/ambiguous state |
| TD-04 | Top-five CPL moments only (`259-263`) | Wins thrown away or saved positions can be overlooked | Typed swing and conversion moments derived from same-depth WDL trajectories |
| TD-05 | No motif detector despite nullable JSON column | Cannot target real blindspots | Add FEN fixtures and engine-validated rule candidates; store evidence and detector version |
| TD-06 | LLM sees FEN/move/best move but not PV; no output validator (`explainer.py:10-49,71-115`) | Generic or impossible tactical explanation can be persisted | Structured facts contract, validation, deterministic fallback, and sampled contradiction review |
| TD-07 | Hardcoded dev user (`auth.py:15-40`) | All self-hosted users share data; cross-user privacy impossible | Single-user local auth first, secure session and ownership checks; optional multi-user mode only after threat model |
| TD-08 | Background task lives in web process (`analysis.py:22-37,148-160`) | Restart loses work; multiple replicas duplicate work | Use PostgreSQL-backed job rows and a small worker loop, one DB, transactional claim/lease |
| TD-09 | Analysis depth policy lacks a stable version; normal route depth 20, scan/deep logic uneven | Scores cannot be compared or safely re-analyzed | Persist engine/version, requested and achieved depth/nodes, metric and classifier version; never aggregate unlike versions silently |
| TD-10 | Import path does not reject variants; data ownership inferred from username frequency (`import_.py`, `importer.py:125-151`, `crud.py:70-110`) | Invalid boards or wrong player stats | Validate PGN variant/header and ask for identity when uncertain; retain import provenance |
| TD-11 | Plans and toggles are partly speculative and process-local (`curriculum.py:30-50,227-359`) | Task state lost; recommendation language exceeds evidence | Replace made-up Elo gains, build metrics first, persist goals and plan snapshots only when justified |
| TD-12 | Sparse tests: two modules, 15 tests; no chess known-position or route integration tests found | Regression risk across core differentiator | Add unit FEN suites and service/API tests before expanding metrics |
| TD-13 | Compose has default dev credentials, `env_file: .env`, source bind mounts; frontend Dockerfile assumes standalone output (configured in `frontend/next.config.ts`); backend entrypoint applies migrations (`docker-compose.yml`, Dockerfiles) | New clone may fail or expose unsafe defaults; prod/dev modes unclear | Separate dev and self-host profiles, health checks, secrets template, startup docs, backup/delete path; smoke test clean boot |
| TD-14 | `.env.example` points to `/usr/bin/stockfish`, while Debian commonly uses `/usr/games/stockfish`; config default also `/usr/bin/stockfish` | Native install fails on common distro | Resolve by PATH lookup/config and document both; container symlink already handles Debian path |
| TD-15 | Stray `backend/run_migration.py`; duplicate root/backend virtualenvs; `data/test_game.pgn`, `pgdata/`, `qdrant/`, `storage/`, generated artifacts | Clone hygiene and developer confusion | Audit git tracking and setup docs; do not delete data or environments until ownership and reproducibility are known |

## 9. Open-source readiness audit

**Verified:** MIT license exists; PR template exists; agent role files define five ownership areas; CI workflow exists; `.gitignore` excludes env files, Python artifacts, and `pgdata/`.

**Missing or incomplete:** contributor onboarding, issue templates and labels, code-of-conduct choice, explicit source/data licensing inventory, privacy/data flow statement, user data deletion and export, safe demo data and seed process that runs without private game imports, tested first-run instructions, supported deployment profiles, CI coverage of Docker build/config and any schema migration smoke test. The generated 3,100-puzzle seed is derived from Lichess's CC0 dataset, but it requires network access and the script imports `zstandard` without declaring it in `pyproject.toml`; seed execution is not a guaranteed offline first run.

Treat user PGNs as private personal data. Local self-hosting should work with no LLM key and no outbound calls except an explicit import, optional provider, or opt-in tablebase request. Add an export and delete-my-data path before multi-user auth. Verify every bundled dataset, font, engine binary, and copied sample for license and redistribution terms; Stockfish is GPLv3, so container distribution needs an explicit license notice and compliance review.

## 10. Evaluation correctness and re-analysis policy

**Observed defect:** `compute_accuracy()` applies `103.1668 * exp(-0.04354 * x) - 3.1668` to average centipawn loss. Lichess defines that transform on the *loss in Win%*, after converting engine centipawns to Win% with a logistic curve. At ordinary ACPL values, the current code can saturate at zero. Its mate conversion to ±1000 CP is also lossy and has no stored score-kind field. See official [Lichess Accuracy](https://lichess.org/page/accuracy) and [`AccuracyPercent.scala`](https://github.com/lichess-org/lila/blob/master/modules/analyse/src/main/AccuracyPercent.scala).

**Recommended v2 pipeline:** retain the engine's raw score kind (`cp` or `mate`), score POV, achieved depth, engine identity/build, and limit. Convert each before/after score to a bounded win probability, orient both to the moving player's point of view, then compute `loss = max(0, win_before - win_after)` in percentage points. Use Lichess's published curve for per-move accuracy as a transparent initial metric. For whole-game accuracy, first use the arithmetic mean of move accuracies and label it `chessian-v2-mean`; only adopt the volatility-weighted/harmonic aggregate after a benchmark proves its value and after matching the intended side/phase semantics. Do not call the result “Lichess accuracy” unless the implementation and inputs match their method.

Mate policy: keep mate scores as mate scores through storage and comparisons; map to the documented capped centipawn equivalent only at the Win% boundary, test both sides of mate and mate-in-zero/terminal positions, and never claim exact probability from a forced-mate sentinel. Ignore terminal positions as move-quality deltas when there is no next decision. Avoid the ±1000 score's present ambiguity by storing `score_type` and `mate_distance` alongside an optional CP score. Scores compared for a move must come from the same engine build and analysis policy.

**Re-analysis cost:** every existing `GameAnalysis` and `MoveAnalysis` accuracy/classification/phase aggregate is stale under v2. Run a dry-run inventory and benchmark game lengths first. Add `metric_version`, `classifier_version`, `analysis_policy_version`, `engine_name/build`, `requested_depth`, and `achieved_depth` metadata through a new Alembic migration. Mark old rows as v1; do not mix v1 and v2 in profiles. Re-analyze through the durable queue in bounded batches, report counts/failures, retain old summaries until a v2 result commits, then make v2 the only default aggregate. Preserve PGNs and raw move data. A user can pause/cancel re-analysis; the visible UI labels stale metrics until refresh. Never compare different depths or engine builds as if equivalent.

**Classification path:** do not make “brilliant” a negative-loss condition. In the first correctness release expose best/near-best, inaccuracy, mistake, blunder and unclassified/forced labels from tested win-probability loss bands, with thresholds chosen from golden positions and a manually reviewed sample. Keep CPL visible as a separate engine diagnostic. No “great” or “brilliant” badge until an objective, documented policy passes known-position review. The research thresholds need a separate dataset and may vary by game phase and position difficulty.

## 11. Move labels: proposed definitions

These definitions are recommendations for an objective first release. Values marked “calibrate” must be tuned against a versioned set of positions and manually reviewed games. Labels should expose the underlying score change and confidence, not imply universal truth.

| Label | Proposed rule | Safety condition |
|---|---|---|
| Best | Played move matches the engine's top move at the recorded search policy | Store top-move rank, depth, engine build and alternatives; “best” is engine-relative |
| Good | Same-depth WDL change stays below the inaccuracy band | Store the measured delta; do not claim “good” means human-easy |
| Inaccuracy / mistake / blunder | Initial candidate thresholds on normalized winning-chance scale `[-1, 1]`: loss ≥0.10 / ≥0.20 / ≥0.30 respectively (5 / 10 / 15 percentage points on 0–100 Win%) | These are a transparent starting policy aligned with Lichess's current annotation bands; validate against the golden set and label/version Chessian's policy |
| Forced move | Position has one legal move, or only one move preserves the same WDL class within a configured tolerance after MultiPV search | Distinguish “only legal” from “only practical engine move”; retain criteria in the response |
| Book move | Move remains in a locally licensed, versioned opening tree; show the source and depth/ply coverage | Do not infer from engine strength or opening name headers alone; out-of-book does not equal bad |
| Missed win | Player had a stable winning WDL/Win% class before the move; played move loses the win class; an engine alternative retains it | Must survive deeper same-engine confirmation; count only if the prior edge is not just a shallow search spike |
| Great | Defer emission. Candidate: a move uniquely preserves a decisive WDL class while ordinary alternatives lose it, or creates a confirmed decisive swing. | Requires multi-PV comparison, deeper confirmation, and evidence that the label adds value beyond “best” or the underlying loss |
| Brilliant | No first-year badge. Candidate policy would require an objectively sound, non-obvious move that preserves/improves WDL despite a superficially attractive losing alternative or material sacrifice, with alternatives proven inferior by same-depth and deeper search | Never infer from search noise, sacrificed material alone, forced moves, or annotations on imported PGNs; a reviewer must validate a labeled dataset before launch |

Do not borrow Chess.com label meanings and imply equivalence. Its public definitions are product-specific, and its Game Review can change labels with analysis settings. Document Chessian's own policy and version it.

## 12. Phase boundaries and edge cases

Replace move-count windows with two independently derived boundaries. **Opening** ends at the first position leaving a versioned, licensed ECO/theory tree. Until that tree is selected and licensed, return `opening_boundary_unknown`; use the PGN opening header for display only, not for chess position correctness. **Endgame** begins when the material pattern crosses a deterministic rule set, such as both queens absent and the remaining material is below a reviewed threshold. Store boundary source and reason per ply; allow “transition/uncertain” positions instead of forcing a phase label.

Initial acceptance cases: a long theoretical line must stay opening past ply 20; a gambit with early material deficit must not be called an endgame; queenless middlegames with many rooks/minors must remain middlegame; queen trades with low material can enter endgame; short decisive games may have no middle or endgame; promotion, underpromotion, and promoted material must count correctly. A phase accuracy score is per player and per phase, and requires enough of that player's moves. Missing phase data is null, never 100%. Endgame type (rook/pawn/minor/queen/mixed) is a separate dimension, not a phase boundary.

## 13. Typed critical moments

Store each moment as a typed record with triggering ply, perspective, before/after WDL or Win%, same-depth engine evidence, alternative PV, confidence, `commission` or `omission`, and detector version. Build a position trajectory and deduplicate overlapping types so one event does not crowd the whole summary.

| Type | Definition | Commission vs omission |
|---|---|---|
| Swing | Large same-depth change in the mover's or game-level WDL/Win% | Played move caused the change = commission |
| Missed win | A player with a stable winning position failed to preserve the winning class | Omission when engine line proves a preserving move was available; commission if the move actively drops it |
| Collapse | A winning advantage deteriorates to draw/loss over a bounded sequence | Attribute the earliest confirmed decision point, not every later move |
| Escape | A lost/drawn side finds a resource that restores draw/win chances | Commission when played move creates the resource; otherwise omission by opponent |
| Turning point | Highest-confidence point where likely game result changes direction | Explain evidence and outcome label; no psychological inference |

Do not select only top CPL. Keep a capped default of a few moments per game but include one severe collapse or escape when present. Use a threshold and confidence floor; avoid announcing a missed win where the position is only slightly favorable or analysis is unstable. Display if the interpretation is “engine suggests,” not human certainty.

## 14. Tactical motif detector and acceptance suite

Use deterministic candidate generation from `python-chess` legal attacks, checks, pins, captures, material and king safety, followed by Stockfish validation at the same versioned depth policy. Motif labels describe the board event, not player intent. Persist motif, event squares/pieces, side to move, PV/eval evidence, detector version, confidence, and one of: `executed`, `missed_offense`, `missed_defense`, `walked_into`. A label is omitted when validation is inconclusive.

Start with fork, pin, skewer, discovered attack, back rank, hanging piece, trapped piece, deflection, overloading, and mating patterns. A rule detector finds candidates; engine search confirms whether a forcing line exists and that the move actually changes the result materially. “Walked into” requires a threat that existed before the move and a loss after it. `missed_defense` requires a defensive engine move preserving the WDL class. Be cautious around quiet positional overloads and trapped pieces; require a strong forcing proof or omit.

Acceptance: version-controlled FEN fixtures for every motif, color flip, legal move, promotion/castling where relevant, false-positive neighbor positions, and each of the four action tags. Each fixture states expected motif/action and why. Tests assert exact intended tags, engine-enabled tests use a pinned Stockfish version/depth, and pure candidate tests do not need Stockfish. Require zero false positives in the golden suite and manually review a stratified sample before enabling cross-game blindspot summaries. A FEN set is the regression contract, not a claim of complete tactical understanding.

## 15. Clock behavior and session patterns

Clock signals are correlations, not diagnoses of emotion. Existing analyzer reads PGN `%clk` values and `time_spent`, but it cannot compute the first move's spent time without an initial clock value. Store clock provenance and missingness; do not treat absent clocks as zero. Normalize by time control and increment.

Deterministic measures: blunder/mistake rates by remaining-time band; fraction of moves below a configurable remaining-time threshold; onset ply when remaining time first falls below a normalized budget; decision time versus engine-scored position difficulty; time spent on objectively hard versus routine moves; time-control-stratified outcomes. Cross-game session patterns may compare moves after an objectively costly error with matched positions and time controls. Use language such as “these events were associated in your imported games,” never “tilt caused.” Do not use video, biometrics, or real-time warnings.

Acceptance requires at least a stated sample count and confidence interval; show “not enough clock data” for small samples. Filter bullet/blitz/rapid/classical separately and account for increment, delay, missing `%clk`, interrupted games, and time scrambles. Include a test PGN with known clock annotations, a no-clock PGN, and clocks that increase due to increment.

## 16. Conversion, holding, and resilience metrics

Track four outcome transitions from stable engine WDL bands: conversion of winning positions to wins; defense of drawn positions to draws; saving objectively lost positions as draws/wins; endgame conversion/holding by material type. Split by user color, game result, time control, material/endgame type, and sample count. Count independent opportunities rather than every adjacent ply. Compare with a deeper same-engine confirmation for candidate turning points.

The prompt calls endgame conversion a particularly large leak below 1800. Treat that as a hypothesis, not a universal fact. Prioritize this metric early because it is useful and deterministic, then test whether it predicts actionable learning in the first small cohort. Suppress rates with fewer than a predeclared minimum number of opportunities and provide numerator/denominator and interval, not a percentage alone. Do not make Elo-gain promises.

## 17. Training loop, puzzle ratings and endgame drills

Keep the current rating-band + SM-2 puzzle queue as the safe baseline. Once validated motif events exist, rank candidate review puzzles by evidence strength, blindspot frequency, recency/decay and difficulty fit; always retain a mixed control queue so the trainer does not overfit one sparse label. Each recommendation links to the originating game/move and offers hide/delete controls.

Record attempts with first-try correctness, retries, solve time, hint/reveal, rating band, motif and source. Do not count a puzzle as a successful first try after a wrong attempt. Maintain separate *puzzle skill* from chess rating. A Glicko-style rating/deviation can be an experiment after enough attempts; avoid a false-precision number for new users, and use conservative updates with a cold-start interval. Never use puzzle rating to claim over-the-board strength.

Compare SM-2 with FSRS only through a replayable offline scheduler evaluation on collected grade histories and a prospective opt-in cohort. SM-2 maps the current binary outcome to only quality 0 or 3; it cannot estimate confidence. Add an honest recall grade (again/hard/good/easy) before any scheduler comparison. Evaluate next-review recall, review burden, calibration and drop-off; keep SM-2 as default until evidence and migration behavior justify a switch. FSRS has a public open implementation, but the algorithm alone does not create enough training data.

Endgame drills can use Lichess's public Syzygy tablebase API for eligible positions rather than shipping ~18GB of tablebase files. Make remote lookup explicit, cache minimally, obey published rate limits/terms, provide offline Stockfish fallback, and explain the seven-piece eligibility boundary. Do not depend on an unversioned third-party service for core correctness. Time Capsule can re-serve prior missed positions after 7/30/90 days, measure first-try recall, and preserve the original game reference. A weekly plan comes only after metrics have sample thresholds, user rating band is known or explicitly self-reported, and each task is grounded in an evidence link.

## 18. AI capability contract

Deterministic chess/domain code owns legal positions, engine comparisons, metric calculations, classification, phase/motif/clock signals, weakness aggregation, puzzle selection, and evidence links. LLMs may phrase already-computed facts. They must not discover tactics, infer pieces from prose, invent causality, choose metrics, or create a “coach plan” from unsupported assumptions.

| Capability | Input → output | Pipeline/model/data | Evaluation | Failure and free-tier cost |
|---|---|---|---|---|
| Move explanation (optional) | FEN, legal played move, best move/PV, before/after score with POV/depth, verified motif and phase → 2–3 grounded sentences | Deterministic fact packet → optional free provider selected by operator, or local template; source is user's PGN plus Stockfish | Golden FEN set; piece/square/move claims validated against FEN and legal line; sampled human rating; contradiction rate | Provider can be unavailable, rate-limited or generic; reject invalid claims and use templates. Zero project spend: no key by default, no paid fallback, enforce no-billing user guidance and call budget. Free quotas can change. |
| Cross-game “coach” summary (later) | Precomputed profile aggregates with denominators, confidence, links → concise summary and next action | SQL/aggregation first; LLM only paraphrases these rows; no vector search for numeric questions | Every number and cited game link must resolve to input; compare against deterministic baseline; unsupported-claim review | Empty/sparse profile gets deterministic “collect more data”; no invented trends. Same optional/free-only constraints. |
| Tactical motifs | FEN and candidate moves → validated motif/action tags | `python-chess` rules + Stockfish; no LLM | FEN fixture suite, false-positive review and engine-depth repeatability | Ambiguous event returns no tag. Local CPU cost only, bounded by per-game candidate budget. |
| Weakness prioritization | Versioned analysis rows, motif and conversion/clock aggregates → sorted evidence-backed weaknesses | SQL + deterministic scoring and minimum sample requirements | Hand-calculated fixtures, stability as games are added, confidence calibration | Sparse/mixed-version data yields “insufficient data”; no LLM needed. |
| Puzzle generation/selection | Stored CC0 puzzles and verified user events → selected source puzzle / old error | SQL scoring/rating bands, SM-2 or evaluated scheduler; no synthetic tactics | First-try retention by motif/rating/time; correctness by solution replay | Missing theme coverage uses mixed puzzles; generated puzzles deferred. |

Structured explanation contract: `position_fen`, `mover`, `played_uci/san`, `best_uci/san`, validated PV UCI, score POV and kind, depth/build, WDL/Win% change, classification/version, phase evidence, motif evidence, allowed square/piece names, forbidden claims, and source game/ply. Persist exact prompt/model/version and output only if policy permits; do not log PGNs or secrets. Validate square/piece claims from FEN and named moves against legal positions; validate quoted variation; reject unsupported numeric claims. Always have a deterministic template fallback and a clear “explanation unavailable” state.

## 19. RAG and conversational coach decision

**Decision: reject RAG for the first year.** Questions such as “How often did I blunder in rook endgames?” or “Show my losses as Black in the Caro-Kann” are structured SQL over the user's own records. Embedding search would make counts harder to audit and could surface the wrong game. First build an evidence-linked profile API and deterministic query templates.

Reconsider a small retrieval feature only if user feedback demonstrates questions that cannot be answered by structured queries, such as retrieving similar strategic explanations across games. Then use structured filters first (owner, time control, phase, motif, date), local permissively licensed embedding model and local vector index, and retrieve exact game/move IDs with citations. Qdrant is currently an unused local artifact, not an architectural requirement. Do not download embedding models or send PGNs to a hosted embedding API by default. Any LLM answer must cite game, date and ply and distinguish a retrieved example from an aggregate statistic.

## 20. Competitive research and positioning

Current product pages were reviewed, not benchmarked hands-on. Feature availability varies by account and region; the table describes publicly documented product direction, not a complete feature audit.

| Product | Public strengths / overlap | What Chessian should learn | What not to copy |
|---|---|---|---|
| Lichess | Free analysis, insights, puzzles, personal opening explorer, tablebases, studies and large game tools | Open data, open source, inspectable exports, training from mistakes, high baseline for “free” | Do not position the project as the only one with cross-game insights; do not depend on their APIs as an unbounded backend |
| Chess.com | Game Review, move labels, coach, retry, opening links, Insights and broad lessons | Guided review flow, retry at the error, explain decisions in player-facing terms | Paid-only assumptions, opaque proprietary scoring, unverified “brilliant” badges, growth features before trust |
| Aimchess | Aggregates player history into tactics, endgame, advantage conversion, resourcefulness, time and opening insights; personalized exercises | Confirms that user-centered aggregates and practice from mistakes are meaningful product territory | Claims unsupported by a reproducible formula, proprietary dependence, or inflated gain promises |
| DecodeChess | Explains engine suggestions, threats, plans and piece roles | Explanation quality needs to explain why a move works, not repeat the evaluation | A single-game prose layer without validated cross-game evidence is not the main differentiator |
| Chessable | Course-linked, interactive chess learning | Make practice actionable; preserve user's learning context | Building a course marketplace or copying copyrighted course content |
| ChessTempo | Rated tactics, opening trainer, endgame trainer, personal repertoire and training history | Rating bands, defensive puzzles, opening/endgame drills and measurable retention | Rebuilding a full chess training library when the product can point to the user's own evidence |
| ChessBase | Deep database, opening preparation/reports and serious-player research workflow | Serious users value provenance, filters and position/game references | Expensive database/licensing needs, massive scope, “pro suite” complexity |
| Open-source references | Lichess/Lila, Stockfish, python-chess, and Scid vs. PC provide inspectable tools or code | Reuse standards and test ideas; cite upstream and maintain licenses | Forking large systems or claiming source availability alone gives product differentiation |

Chessian should not compete on engine strength, raw puzzle count, social scale, generic chat, or opening database size. Its plausible edge is a local-first, evidence-linked report across portable user-owned games with a visible “not enough data” state and focused re-testing. That remains a hypothesis until pilot users prefer it over existing free tools.

## 21. Architecture decisions and trade-offs

These are proposed decisions, not implemented or approved ADRs. Record the final owner decision and superseding rationale in the decision log (Section 27).

| Topic | Recommendation | Trade-off and trigger to revisit |
|---|---|---|
| Overall shape | Keep the existing FastAPI + Next.js monolith and PostgreSQL. Preserve routers → services → CRUD boundaries. | One deployable unit and one database are easier for one maintainer. Split only after a measured CPU/availability need, not for anticipated scale. |
| Persistent analysis jobs | PostgreSQL `analysis_jobs` table plus a small worker process using transactional leases/`FOR UPDATE SKIP LOCKED`; store attempts, state, heartbeat, error code and version. | One extra process, no Redis/Celery dependency, survives web restarts and matches existing Postgres. Revisit if sustained queue throughput or multiple independent worker types justify a broker. |
| Authentication | Start with a self-hosted owner account, bootstrap credential flow, server-side opaque session cookie, password hashing, CSRF protections, rate limits and secure cookie defaults; no social login requirement. | Simpler local ownership than mandatory OAuth/JWT. Remote public hosting requires TLS, secret rotation, recovery and a stronger threat review before release. Avoid all-users-share-one-dev-user. |
| User-owned data | Keep and enforce `user_id` foreign keys; migrate all queries through authenticated owner ID; make move hash uniqueness `(user_id, moves_hash)`; preserve source/identity confirmation and cascade deletion. | Existing tables partly support ownership. Migration must not merge or delete anyone's games automatically. |
| Caching | First cache only immutable engine position results keyed by normalized full FEN, variant, Stockfish build, options, depth/nodes/time limit; use bounded local/Postgres cache with invalidation by engine version. | Saves repeat work but adds storage and privacy concerns. Measure cache hit rate before implementing; no shared cross-user PGN/result cache. |
| Observability | Structured standard-library logs and request/job IDs; metrics for import, queue wait, analysis time, failure reason, LLM attempts and DB latency; redact credentials, PGNs and raw prompts. A self-hosted admin status page is enough initially. | No paid Datadog or hosted monitoring requirement. Exportable logs and a local health endpoint; opt-in diagnostics only. |
| Security | Limit PGN bytes and game count; validate variants, FEN, moves and remote URL hosts; protect outbound imports from redirects/SSRF; rate-limit auth/analysis; use parameterized SQL, secret-safe logs, dependency/license checks, CSP/security headers and data export/delete. | Maintain a short threat model and test it in CI. No telemetry or third-party AI data transmission by default. |
| Deployment | Repair root Compose into a documented self-host profile: Postgres health check, backend readiness, frontend build/start, migration-on-single-start policy, named data volume and backup/delete instructions. Keep development bind mounts separate. | Compose is sufficient for one-machine self-hosting. Do not imply production HA or public internet safety. Docker image build remains a monthly gate. |
| Tests | Unit tests for formulas/phase/moments/motifs; FEN fixtures; analyzer tests with deterministic fake UCI where appropriate; pinned-engine integration tests for a small suite; API tests with disposable Postgres; frontend typecheck/lint/build; Compose smoke test in CI if free runner budget allows. | Keep ordinary CI quick; label engine-heavy integration separately. No weakened assertions to accommodate engine drift; pin binaries and version expected metrics. |
| Qdrant | Do not add it to Compose or runtime until an evidence retrieval feature is approved. | Removes idle service/data complexity. If needed later, include local embedding and backup instructions and measure resource use. |

## 22. Roadmap overview: four quarters

| Quarter | Months | Outcome | Gate before next quarter |
|---|---|---|---|
| Q1: Trust and cloneability | 1–3 | Correct metrics and labels, runnable clean clone, baseline conversion/clock data, durable queued analysis and owner identity | Golden correctness suite passes; metrics are versioned; first-run setup works on a clean machine |
| Q2: Diagnosis | 4–6 | Phase boundaries, typed critical moments, FEN-validated motif labels, explainable cross-game profile | Motif fixture acceptance and human audit pass; each profile claim links to game evidence |
| Q3: Practice loop | 7–9 | Blindspot-linked puzzles, retention tracking, time capsule, practical endgame conversion drills | Practice records provenance and first-try outcome; no recommendation before its metric dependency exists |
| Q4: Open-source release and learning | 10–12 | Local-first coach summary, self-host release, contributor onboarding, pilot results and measured next-year decisions | Security/privacy and license review; clean install and export/delete verified; zero-cost operating mode demonstrated |

Velocity assumption: one developer has roughly 6–10 focused hours per week for this project, with 1–2 small PRs per week when available. Reserve at least one week each quarter for discovery, integration, tests and documentation. University deadlines can shift a month; the milestone gate matters more than calendar completion. No month includes more than one high-uncertainty data/model feature.

## 23. Quarter 1 monthly milestones (Months 1–3)

### Month 1 — Foundation and trustworthy numbers (2026-11)

- **Objective:** make correctness and a clean clone the floor for every later metric.
- **Features / engineering:** restructure the contributor entry points by consolidating setup/check commands, separating tracked demo/test fixtures from generated local data, and making the docs/config ownership map explicit; do not move domain modules or delete unclassified artifacts. Add formula and classifier tests; replace accuracy with versioned mover-perspective Win% loss; remove ineffective brilliant branch; calibrate objective error bands on a small FEN/PGN golden set; record policy/depth metadata; variant rejection; stockfish path resolution; expand existing CI (it already exists) to make backend import, pytest, frontend typecheck/lint and Docker config/build checks explicit; repair Compose and first-run instructions; add demo PGN fixtures and open-source templates.
- **Architecture:** additive schema migration for analysis versions and raw score types; keep old v1 rows tagged/stale. Compose includes Postgres health/readiness, clear development and self-host defaults, and a working empty-volume boot.
- **Research:** compare a sampled local game set to same-engine deeper analysis and selected Lichess output where comparable; manually inspect accuracy behavior, mate positions, forced moves and variant PGNs. Confirm Stockfish redistribution notice and all bundled sample licenses.
- **Deliverables:** CI green; verified formulas and FEN tests; versioned analysis record; import rejects unsupported variants with a useful message; clean `docker compose up --build` path; `CONTRIBUTING.md`, issue/PR templates, data/privacy statement outline and demo PGN.
- **Dependencies:** none; current code and directory structure as audited.
- **Validation / Definition of Done:** backend import, all pytest, frontend typecheck/lint, Docker syntax/build and clean boot, Alembic upgrade on disposable DB, analyzer known-position tests, no secrets or user data in repo; attach logs. Re-analysis dry-run is not mass-run in this month.
- **Risks / fallback:** if accuracy aggregation becomes unstable, ship per-move WDL-loss and mark game aggregates beta; if Compose build exceeds time, keep source restructure small and complete the clean backend/Postgres boot before UI container polish.

### Month 2 — Player identity, variant safety and durable analysis (2026-12)

- **Objective:** make imports attributable and analysis recover after service restarts.
- **Features / engineering:** PGN identity confirmation for ambiguous archives; reject Chess960/unsupported variants and malformed/incomplete games with per-game results; resumable import bookkeeping; database-backed analysis job status/attempts; recovery and retry; expose queue/progress/errors in library; user export/delete endpoint design and single-owner bootstrap.
- **Architecture:** PostgreSQL queue with worker process, no Redis/Celery; owner ID dependency replaces direct `ensure_dev_user()` use after auth migration is proven. Keep a dev-only compatibility path for upgrade test, remove before public release.
- **Research:** estimate queue runtime and CPU at two user machines; test failure/restart at queued, running and persist boundaries; review account/data model migration safety.
- **Deliverables:** restart-safe analysis; explicit import-side identity; versioned, idempotent re-analysis job; migration dry-run/rollback notes.
- **Dependencies:** Month 1 versioned analysis and Compose database.
- **Validation / Definition of Done:** worker recovery integration tests, unique job claim under concurrent workers, owner isolation tests, PGN fixture matrix, verified no state loss when backend restarts.
- **Risks / fallback:** if robust auth threatens queue work, do local owner bootstrap and queue as two small issues; postpone public multi-user mode while never sharing a dev identity.

### Month 3 — Conversion, resilience and clock baselines (2027-01)

- **Objective:** add useful cross-game measures whose evidence is already available.
- **Features / engineering:** define stable WDL bands and opportunity aggregation; conversion/holding/saving rates with denominators and confidence; clock normalization for `%clk`/increment and “unknown” cases; open-source privacy and deletion/export requirements; instrument analysis latency and time-to-first-insight.
- **Architecture:** profile query/service module with pure metric calculations; aggregate only same-version analyses; no new model required unless measurement proves need.
- **Research:** compare candidate thresholds on known games and a small consented self-review; examine if endgame conversion signal is actionable across the proposed rating range instead of assuming it is the dominant leak.
- **Deliverables:** profile v1 cards for conversion, holding, saving and time pressure; source game/move links; metrics dictionary.
- **Dependencies:** Months 1–2 reliable metrics, ownership, durable jobs.
- **Validation / Definition of Done:** pure fixtures for transition counts and confidence suppression; clock PGN tests with increment/missing data; dashboard totals reconcile to inspected source games.
- **Risks / fallback:** if sample sizes are too small, display counts and “collect more games”; omit rates and do not add a noisy plan task.

## 24. Quarter 2 monthly milestones (Months 4–6)

### Month 4 — Phase boundaries and typed critical moments (2027-02)

- **Objective:** replace fixed ply phases and CPL-only key moments.
- **Features / engineering:** select and license a compact opening line source or keep opening boundary unknown; implement theory exit and reviewed material-based endgame flags; annotate edge cases; add typed swing/missed-win/collapse/escape/turning-point events with commission/omission evidence.
- **Architecture:** add phase-boundary evidence and typed event storage/version; preserve UI compatibility during migration.
- **Research:** compare candidate phase boundaries with annotated games and experienced-player review; inspect deep-search stability on high-swing positions.
- **Deliverables:** phase map, event API response and analysis viewer badges with confidence/evidence.
- **Dependencies:** metric versions and durable re-analysis.
- **Validation / Definition of Done:** phase fixtures for gambit, queenless middlegame, short game, long theory, promotions; moment fixture set demonstrates stable WDL class shifts and deduplicates overlapping plies.
- **Risks / fallback:** if no acceptable opening dataset license is established, ship “opening known from PGN / boundary unknown” and material endgame only.

### Month 5 — Tactical motifs v1 (2027-03)

- **Objective:** provide conservative, reviewable motif evidence.
- **Features / engineering:** implement candidate rules for fork, pin, skewer, discovered attack, back rank, hanging piece, trapped piece, deflection, overloading and mate patterns; validate with Stockfish; persist the action tag, evidence, confidence and detector version.
- **Architecture:** motif detector service behind analyzer; bounded candidate budget and deterministic no-tag fallback; new migration only if schema requires it.
- **Research:** write FEN examples and counterexamples for every motif/action; manually inspect false positives in sampled user games; distinguish “missed offense” from “missed defense.”
- **Deliverables:** motif counts on analysis screen and per-game event evidence; internal detector report.
- **Dependencies:** same-depth engine policy, types and phase data.
- **Validation / Definition of Done:** full FEN acceptance suite, zero golden-suite false positives, engine output pinned/versioned, manual review accepted before global profile is enabled.
- **Risks / fallback:** defer ambiguous overload/trapped heuristics; ship only high-precision tactical motifs with clearly stated coverage.

### Month 6 — Evidence-linked weakness profile (2027-04)

- **Objective:** aggregate verified motif and conversion evidence into a truthful diagnosis.
- **Features / engineering:** motif frequency normalized per opportunity; by-color/phase/time-control filters; minimum sample sizes; per-claim game/move evidence; uncertain and contradictory evidence states; player feedback (“useful / not useful”) stored locally.
- **Architecture:** deterministic profile service/query contracts; no chat/RAG yet; ensure every query filters owner and metric version.
- **Research:** manually compare profile output with a human review of 10–20 games; track unsupported/unstable claims and tester usefulness.
- **Deliverables:** weakness profile v1 and test report; no Elo gain estimates.
- **Dependencies:** Month 5 detector; Month 3 metrics; owner authorization.
- **Validation / Definition of Done:** hand-calculated cross-game fixtures, minimum-sample behavior, direct links reproduce exact tagged positions, privacy isolation test.
- **Risks / fallback:** reduce profile to confidence-qualified counts and examples if detector review is mixed; do not add LLM summaries to hide uncertainty.

## 25. Quarter 3 monthly milestones (Months 7–9)

### Month 7 — Blindspot-linked puzzle review (2027-05)

- **Objective:** direct practice to a verified weakness without pretending the catalog is complete.
- **Features / engineering:** map source motif labels to compatible CC0 puzzle themes; select due SM-2 reviews first then blindspot pool then mixed controls; show game/move source for custom review positions; log first-try success and solve time.
- **Architecture:** selection policy in service layer; add provenance fields and idempotency; no synthetic puzzle generation.
- **Research:** estimate theme coverage for each motif and rating band; document gaps and avoid giving a 1000-rated player master-only opening tasks.
- **Deliverables:** optional personalized queue and a weekly session summary; existing generic queue remains available.
- **Dependencies:** verified Month 5 motifs and Month 6 profile.
- **Validation / Definition of Done:** solution replay, queue priority tests, no repeated unresolved errors beyond configured retry cadence, source deletion hides derived puzzle.
- **Risks / fallback:** if CC0 theme coverage is low, schedule the player's original position only when engine verifies uniqueness; otherwise show generic puzzles and disclose gap.

### Month 8 — Review retention, scheduler comparison and Time Capsule (2027-06)

- **Objective:** measure whether practice is remembered and evaluate scheduler improvements.
- **Features / engineering:** first-try, recall-after-7/30/90-days, review load and drop-off metrics; add honest user recall grades; shadow-run SM-2 and FSRS on the same attempt histories; Time Capsule retests old errors with opt-out.
- **Architecture:** store attempts as immutable events plus current schedule state; scheduler version; migration preserves due dates/history.
- **Research:** offline schedule replay and small opt-in prospective comparison; no user data leaves local install.
- **Deliverables:** retention curves for a single self-hosted user, scheduler report, Time Capsule flow.
- **Dependencies:** Month 7 provenance and attempt logging.
- **Validation / Definition of Done:** deterministic scheduler fixtures; same attempts reproduce both schedules; re-test metrics exclude exposed/revealed answers and report denominators.
- **Risks / fallback:** retain SM-2 and ship recall tracking only when sample histories are insufficient to compare schedulers.

### Month 9 — Endgame drills and rating-aware plan rules (2027-07)

- **Objective:** make conversion evidence actionable with a low-cost tablebase path and level-appropriate tasks.
- **Features / engineering:** opt-in remote Syzygy lookup for ≤7 pieces; local cache and offline engine fallback; endgame type drills; plan task mapping from evidence to level-appropriate materials; manual/self-reported rating band with confidence.
- **Architecture:** provider adapter with timeout/backoff and cache; no heavy tablebase files, no paid endpoints.
- **Research:** validate WDL/DTZ/DTM semantics and endpoint terms/limits; compare task relevance with user feedback.
- **Deliverables:** drill page and evidence-linked weekly plan v1, optional remote lookup preference.
- **Dependencies:** conversion profile and endgame types; Month 8 retention data shapes.
- **Validation / Definition of Done:** eligible/ineligible FEN fixtures, API timeout fallback, no repeated outbound lookup when cached, plan fixture for 1000-band user excludes advanced opening theory.
- **Risks / fallback:** remove remote dependency and use local Stockfish if API policy or uptime cannot be depended on; drills remain optional.

## 26. Quarter 4 monthly milestones (Months 10–12)

### Month 10 — Grounded explanation quality (2027-08)

- **Objective:** improve explanations only where they add value beyond deterministic evidence.
- **Features / engineering:** structured explanation contract, FEN/claim validator, line validation, deterministic fallback, model/prompt version, sampled reviewer queue and “helpful / incorrect” feedback.
- **Architecture:** provider adapter, disabled by default, strict request budget and timeout; template remains complete when offline.
- **Research:** golden positions across tactics, quiet moves, mate and endgames; score contradiction rate, specificity and usefulness. Compare a deterministic template baseline.
- **Deliverables:** optional grounded explanations for selected high-confidence moments; public explanation evaluation protocol.
- **Dependencies:** validated metrics, motifs, typed moments and evidence links.
- **Validation / Definition of Done:** no invalid piece/square claim in golden suite; every factual assertion maps to input facts; quota/error path uses template; no secret/PGN prompt in logs.
- **Risks / fallback:** if free providers are unstable or template wins user ratings, keep the provider disabled and improve templates.

### Month 11 — Local-first self-host release candidate (2027-09)

- **Objective:** a stranger can clone, configure, run, backup, export and delete data without paid services.
- **Features / engineering:** finish CONTRIBUTING, issue templates/labels, architecture/development docs, privacy/data flow, license notices, clean demo dataset, one-owner bootstrap, export/delete, migration and backup/restore instructions, threat review.
- **Architecture:** Compose health checks, safe secrets, migration sequencing, resource limits, no default public binding assumptions; explain supported single-host deployment.
- **Research:** license and dependency review, clean-machine run, accessibility and basic security review by a peer, contributor feedback on first issue.
- **Deliverables:** release candidate tag, reproducible install guide, demo profile with no private games, draft release notes.
- **Dependencies:** prior milestones, especially auth, data deletion, worker and Compose.
- **Validation / Definition of Done:** fresh clone using documented commands from empty Postgres volume; CI green; backup/restore and user delete tests; secret scan; all included assets and model/data licenses recorded.
- **Risks / fallback:** ship a local beta and defer public exposure if auth/privacy/security review is incomplete.

### Month 12 — Pilot, reliability and v1.0 decision (2027-10)

- **Objective:** learn whether the diagnosis-and-practice loop helps, then choose what to build next.
- **Features / engineering:** small voluntary pilot (target 5–10 users if available); onboarding and time-to-first-insight; analyze errors and retention; optimize slow analysis only from profiles; fix top usability issues; publish known limitations and roadmap change log.
- **Architecture:** stability and data migration review; performance tests across short/long games on documented hardware; no service decomposition.
- **Research:** qualitative interviews and per-user before/after behavior; compare to each participant's own baseline and state confounders. Do not claim causal rating gains.
- **Deliverables:** v1.0 or beta decision, evidence report, updated roadmap, prioritized next-year issues.
- **Dependencies:** cloneable release candidate and opt-in pilot consent.
- **Validation / Definition of Done:** install and privacy checks pass; KPI report includes denominators and missing data; all user feedback can be deleted; release decision records unresolved defects.
- **Risks / fallback:** if there are no external users, run a single-user longitudinal study and publish only engineering and measurement results.

## 27. Agent-ready backlog, living rules, decisions and open questions

### Backlog hierarchy and task rules

The stable task ID is the GitHub issue key stem and maps one-to-one to one issue. Parent epic, feature and story IDs are labels/relationships, not additional implementation tickets. Tasks are intentionally sized to a small PR for a weaker free-tier model; split any task that needs multiple migrations or touches unrelated agent roles. Existing implementation is not automatically Completed. All roadmap backlog items start **Not Started** until work begins.

| Epic | Feature | User story | Engineering-task range |
|---|---|---|---|
| EP-01 Trustworthy analysis | FE-01 Win% accuracy | US-01 Player sees meaningful accuracy with its method/version | CH-001, CH-002, CH-003 |
| EP-01 Trustworthy analysis | FE-02 Analysis metadata and variant safety | US-02 Player can trust reproducible, supported standard-game analysis | CH-004, CH-005 |
| EP-02 Cloneability | FE-03 CI/Compose/open-source readiness | US-03 Contributor can run and verify a fresh clone | CH-006, CH-007, CH-008 |
| EP-03 Durable personal data | FE-04 Owner identity/jobs | US-04 My imports/jobs remain private and survive restart | CH-009a–d, CH-010a–d, CH-011, CH-024 |
| EP-04 Diagnosis | FE-05 Conversion/clock/phase/moments | US-05 I can see measured opportunities with evidence | CH-012, CH-013, CH-014a–b |
| EP-05 Tactical learning | FE-06 Motifs and puzzles | US-06 I can review a validated recurring error | CH-015a–g, CH-016a–b, CH-023 |
| EP-06 Practice | FE-07 Retention/endgame plan | US-07 I can re-test an old error and practice the right endgame | CH-017a–b, CH-018 |
| EP-07 Grounded coaching | FE-08 Explanation and coach summary | US-08 I receive grounded language linked to my games | CH-019a–b, CH-020a–b |
| EP-08 Public release | FE-09 Pilot and release | US-09 I can self-host and contribute safely | CH-021, CH-022 |

### Engineering tasks

Each task item includes: ID, description, priority, effort, dependencies, status, acceptance criteria, role, files likely touched, verification commands, and size. Allowed task statuses are Not Started, In Progress, Blocked, Under Review, Completed and Deferred. `S` means one small PR that a weaker free-tier model can complete with one bounded acceptance target; if a task grows beyond that, create a new ID/issue rather than expanding the original. File paths are repository-root-relative. Existing paths were verified; paths described as new are destinations under verified directories. Verification commands are run from the named repo subdirectory; schema work must also run disposable-DB migration checks. Standard commands for all code PRs: backend `cd backend && python -c "from app.main import app" && pytest`; frontend `cd frontend && npx tsc --noEmit && npm run lint`; applicable Docker check `docker compose config -q`. Use `GROQ_API_KEY=` in tests that must exercise offline fallback. CI output and exact command output go in the PR.

#### CH-001 — Win% transform and mover POV

- **Description:** replace ACPL-fed accuracy transform with pure score-to-Win% and mover-perspective loss functions; keep the formula named/versioned.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · none · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** white/black perspective fixtures agree; equal or improving move has zero loss; large loss from a won position is bounded and differs from same CPL in an equal position; mate inputs handled through explicit score kind; no NaN/overflow.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/analyzer.py`; new tests under verified directory `backend/tests/`.
- **Verification:** `cd backend && python -m pytest tests/test_analyzer.py` (new test file); then standard backend checks.

#### CH-002 — Objective classification policy

- **Description:** remove negative-CPL brilliant branch; classify versioned Win% loss bands and preserve “forced/unclassified” as explicit states.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-001 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** no negative CPL can be “brilliant”; thresholds documented and golden-position tested; no labels depend on score from a different depth; Great/Brilliant absent until a separate approved spec.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/analyzer.py`; tests in `backend/tests/`.
- **Verification:** targeted classification pytest; standard backend checks.

#### CH-003 — Per-move and game accuracy tests

- **Description:** build formula fixtures for equal, advantage, near-mate, terminal, white/black and phase cases; compare to published curve values.
- **Priority / effort / dependencies / status:** P0 · 1 day · CH-001 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** numerical expected values are independently hand-calculated or referenced to a fixture generator; old ACPL bug reproduces as a regression case; no network call in tests.
- **Role:** qa.
- **Files likely touched:** new test file under verified `backend/tests/`; existing `backend/tests/test_sm2.py` is not to be changed for this task.
- **Verification:** `cd backend && python -m pytest tests/test_analyzer.py -q`.

#### CH-004 — Version analysis settings and raw scores

- **Description:** add additive migration and persistence fields for metric/classifier/policy version, engine build, requested/achieved depth and cp/mate score kind.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-001 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** new analysis rows record metadata; existing rows remain explicitly v1/stale; migration upgrade/downgrade works on disposable PostgreSQL; no historical migration edited.
- **Role:** backend.
- **Files likely touched:** `backend/app/models/__init__.py`, `backend/app/services/crud.py`, `backend/alembic/versions/` (new migration), `backend/alembic/env.py` only if required.
- **Verification:** `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`; standard backend checks.

#### CH-005 — Standard-variant import guard

- **Description:** identify unsupported variants from PGN variant headers/board type and return per-game import rejection before persistence or engine search.
- **Priority / effort / dependencies / status:** P0 · 1 day · none · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** standard chess imports; Chess960 and at least one other variant rejected with explicit reason; batch import continues for valid games; analysis route cannot bypass guard.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/importer.py`, `backend/app/routers/import_.py`, `backend/app/services/analyzer.py`.
- **Verification:** `cd backend && python -m pytest tests/test_importer.py tests/test_analyzer.py -q`; standard backend checks.

#### CH-006 — CI correctness gate

- **Description:** adjust the existing `.github/workflows/ci.yml` rather than create a second workflow; pin supported runtimes, ensure offline fallback test config, add relevant schema/Docker validation where runner budget allows.
- **Priority / effort / dependencies / status:** P0 · 1 day · none · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** PR job includes backend import, pytest, frontend typecheck/lint; failure blocks merge; no secret required; docs task does not pretend remote workflow ran locally.
- **Role:** qa.
- **Files likely touched:** `.github/workflows/ci.yml` (existing).
- **Verification:** `cd backend && python -c "from app.main import app" && GROQ_API_KEY= pytest -q`; `cd frontend && npx tsc --noEmit && npm run lint`; inspect workflow YAML with available CI linter if installed.

#### CH-007 — Clean Compose first boot

- **Description:** repair root Compose, Docker build context/startup, health checks and separate dev/self-host configuration; one migration runner only.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-006 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** from empty volume, Compose builds, Postgres becomes healthy, one migration reaches head, backend health responds and frontend loads; documented environment defaults do not publish unsafe credentials; no paid service required.
- **Role:** devops.
- **Files likely touched:** `docker-compose.yml`, `backend/Dockerfile`, `backend/entrypoint.sh`, `frontend/Dockerfile`, `.env.example`.
- **Verification:** `docker compose config -q`; `docker compose up --build -d`; `docker compose ps`; `curl -fsS http://localhost:8000/api/health`; manual page check; teardown only the task's disposable volume after retaining logs.

#### CH-008 — Contributor setup and privacy guide

- **Description:** add contributor guide, data/privacy statement, license inventory, demo PGN policy and first-run troubleshooting.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-007 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** new contributor can follow exact setup/check commands; docs explain local-only default and what external APIs receive; sample PGNs are license-reviewed; good-first-issue label procedure exists.
- **Role:** docs.
- **Files likely touched:** new root `CONTRIBUTING.md`, new files under verified `docs/`; existing `README.md`, `LICENSE`.
- **Verification:** review every command against repository; follow clean-clone steps; link check if a local checker is available.

#### CH-009a — Bootstrap a local owner account

- **Description:** replace automatic shared dev-user creation with a one-time local owner bootstrap and authenticated owner dependency.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-004, CH-007 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** no password or token is hardcoded; bootstrap is one-time and documented; no public registration is implied; session security and password hashing are reviewed.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/auth.py`, `backend/app/config.py`, `backend/app/models/__init__.py`, new migration under `backend/alembic/versions/`.
- **Verification:** targeted auth tests; migration check on disposable DB; standard backend checks.

#### CH-009b — Enforce ownership in games and imports

- **Description:** replace router calls to `ensure_dev_user()` in import and game routes with authenticated owner identity and apply owner scope to their reads/writes.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-009a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** tests prove cross-owner game/import access returns no data; opening aggregates filter by owner; game dedup is scoped by owner; no shared dev-user fallback remains in these routes.
- **Role:** backend.
- **Files likely touched:** `backend/app/routers/games.py`, `backend/app/routers/import_.py`, `backend/app/services/crud.py`.
- **Verification:** targeted ownership/API tests; standard backend checks.

#### CH-009c — Enforce ownership in analysis and training APIs

- **Description:** apply authenticated owner ID to analysis, puzzle and plan reads/writes.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-009a, CH-009b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** cross-owner analysis, puzzle attempts and plan tasks cannot be read or modified; no shared dev-user fallback remains in these routes.
- **Role:** backend.
- **Files likely touched:** `backend/app/routers/analysis.py`, `puzzles.py`, `plan.py`, `backend/app/services/crud.py`.
- **Verification:** targeted ownership/API tests; standard backend checks.

#### CH-009d — Export and delete owner data

- **Description:** export a user's games and derived records in a documented format; add cascade-safe delete with cleanup of jobs and caches.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-009b, CH-009c, CH-010a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** export is complete and machine-readable; delete leaves no user-owned PGN, analysis, explanations, puzzle attempts, job or cache references; deletion is confirmed in disposable DB.
- **Role:** backend.
- **Files likely touched:** `backend/app/routers/games.py`, `backend/app/services/crud.py`, `backend/app/models/__init__.py`, new migration under `backend/alembic/versions/` only if required.
- **Verification:** targeted export/delete tests; migration check if schema changes; standard backend checks.

#### CH-010a — Persist analysis job state

- **Description:** add job table and job lifecycle fields with unique idempotency per game/policy.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-004, CH-007 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** pending/running/complete/failed state and bounded attempts persist; old game-analysis status remains readable during rollout; migration works both ways on disposable DB.
- **Role:** backend.
- **Files likely touched:** `backend/app/models/__init__.py`, new migration under `backend/alembic/versions/`, `backend/app/services/crud.py`.
- **Verification:** targeted model/CRUD tests; Alembic upgrade/downgrade; standard backend checks.

#### CH-010b — Build restart-safe worker

- **Description:** claim PostgreSQL jobs with a lease, heartbeat and bounded retry; handle backend restart and duplicate worker startup.
- **Priority / effort / dependencies / status:** P0 · 2 days · CH-010a, CH-007 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** an expired lease is reclaimed; concurrent workers cannot execute one active job twice; failure reason is redacted; processing survives web-process restart.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/`, `backend/app/main.py`, `backend/app/config.py`.
- **Verification:** worker/restart integration tests against disposable Postgres; standard backend checks; Docker smoke test.

#### CH-010c — Connect analysis API to durable job state

- **Description:** update the analysis endpoints to enqueue and return persisted job state, including idempotent retries.
- **Priority / effort / dependencies / status:** P0 · 1–2 days · CH-010a, CH-010b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** route does not execute analysis as `BackgroundTasks`; API returns stable job ID and lifecycle state; a retry cannot create duplicate active work.
- **Role:** backend.
- **Files likely touched:** `backend/app/routers/analysis.py`, `backend/app/services/crud.py`, `backend/app/services/`.
- **Verification:** targeted API/job integration tests; standard backend checks.

#### CH-010d — Show durable analysis progress

- **Description:** expose pending/running/retrying/complete/failed job states in library and analysis pages.
- **Priority / effort / dependencies / status:** P1 · 1 day · CH-010c · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** user can see failure and retry state; polling stops at terminal state; refresh does not lose progress; no infinite polling for stale state.
- **Role:** frontend.
- **Files likely touched:** `frontend/src/app/library/page.tsx`, `frontend/src/app/analysis/[id]/page.tsx`.
- **Verification:** `cd frontend && npx tsc --noEmit && npm run lint`; manual API state fixtures.

#### CH-011 — Import identity confirmation

- **Description:** make platform identity explicit per source and confirm ambiguous PGN archives; do not infer from modal frequency without user confirmation.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-009a, CH-009b, CH-024 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** user color is known or shown unknown; old imports can be confirmed; mixed archive does not silently claim a single owner; opening aggregates omit unresolved identity.
- **Role:** frontend.
- **Files likely touched:** `frontend/src/components/Library/ImportPanel.tsx`, `frontend/src/app/library/page.tsx`, `frontend/src/app/openings/page.tsx`; backend API changes are a separate backend issue.
- **Verification:** `cd frontend && npx tsc --noEmit && npm run lint`; manual API contract review.

#### CH-012 — Conversion and resilience profile

- **Description:** add stable WDL-band opportunity counts for convert/hold/save, suppress small denominators and link to evidence.
- **Priority / effort / dependencies / status:** P1 · 2 days · CH-001, CH-004, CH-009c · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** fixtures cover each transition and color; confidence/minimum sample policy visible; mixed analysis versions excluded; no Elo estimates.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/`, `backend/app/services/crud.py`, `backend/app/routers/games.py`, `backend/app/schemas/__init__.py`.
- **Verification:** targeted metric tests; standard backend checks; response fixture checked against hand-calculated games.

#### CH-013 — Clock metric and provenance

- **Description:** compute normalized time bands and time spent with missing/increment handling; add explicit clock-data source and tests.
- **Priority / effort / dependencies / status:** P1 · 2 days · CH-004 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** first move remains unknown without initial clock; increments do not produce negative time spent; no-clock data yields no rate; language says correlation only.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/analyzer.py`, `backend/app/services/importer.py`, `backend/app/models/__init__.py`, new tests under `backend/tests/`.
- **Verification:** targeted PGN clock tests; standard backend checks.

#### CH-014a — Theory exit and material phase boundaries

- **Description:** replace index-based phase slices with evidence-backed theory exit and material endgame markers, including an unknown boundary state.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-001, CH-004 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** Section 12 edge cases pass; missing licensed theory data produces unknown opening boundary; phase accuracy is by player and null when insufficient moves.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/analyzer.py`, `backend/app/models/__init__.py`, `backend/app/services/crud.py`, new migration under `backend/alembic/versions/`.
- **Verification:** phase FEN/PGN tests; migration check; standard backend checks.

#### CH-014b — Typed critical moment records

- **Description:** store same-depth swing, missed-win, collapse, escape and turning-point records with commission/omission evidence.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-001, CH-004, CH-010c · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** event fixtures distinguish event type and commission/omission; unstable search results are suppressed; duplicate events are deduplicated; no top-CPL-only selection.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/analyzer.py`, `backend/app/models/__init__.py`, `backend/app/services/crud.py`, `backend/app/schemas/__init__.py`, new migration under `backend/alembic/versions/`.
- **Verification:** targeted FEN/PGN suite; migration check; standard backend checks.

#### CH-015a — Motif fixture format and fork detector

- **Description:** create a small fixture convention and implement engine-validated fork candidates with one action tag per evidence case.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-001, CH-004, CH-014b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** fork fixtures cover both colors, executed/missed offense/missed defense/walked into and false-positive neighbors; ambiguous cases return no tag; detector version recorded.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/analyzer.py`, new module under verified `backend/app/services/`, `backend/app/models/__init__.py`, tests under verified `backend/tests/`.
- **Verification:** targeted fork FEN tests; pinned Stockfish integration test; standard backend checks.

#### CH-015b — Persist one validated motif family

- **Description:** persist the fork detector's evidence packet through CRUD/API and expose it to profile queries.
- **Priority / effort / dependencies / status:** P1 · 1 day · CH-015a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** motif/action/evidence/version round-trips; null remains null when inconclusive; no fabricated motif values; user ownership is enforced.
- **Role:** backend.
- **Files likely touched:** `backend/app/models/__init__.py`, `backend/app/services/crud.py`, `backend/app/routers/analysis.py`, `backend/app/schemas/__init__.py`.
- **Verification:** CRUD/API fixture tests; migration check if required; standard backend checks.

#### CH-015c — Add pin and skewer detectors

- **Description:** implement pin/skewer candidates and engine validation as one tightly related family.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-015a, CH-015b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** positive/negative FEN fixtures, both colors, action tags and false-positive review; low-confidence cases omitted.
- **Role:** backend.
- **Files likely touched:** modules under verified `backend/app/services/`; tests under verified `backend/tests/`.
- **Verification:** targeted FEN suite; pinned engine tests; standard backend checks.

#### CH-015d — Add discovered attack and back-rank detectors

- **Description:** implement discovered attack and back-rank candidates with engine validation.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-015c · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** positive/negative FEN fixtures, both colors, action tags and false-positive review; low-confidence cases omitted.
- **Role:** backend.
- **Files likely touched:** modules under verified `backend/app/services/`; tests under verified `backend/tests/`.
- **Verification:** targeted FEN suite; pinned engine tests; standard backend checks.

#### CH-015e — Add hanging piece and trapped piece detectors

- **Description:** implement material-loss candidates for hanging and trapped pieces with conservative confirmation.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-015d · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** positive/negative FEN fixtures, engine-confirmed loss, action tags and false-positive review; ambiguous mobility cases omitted.
- **Role:** backend.
- **Files likely touched:** modules under verified `backend/app/services/`; tests under verified `backend/tests/`.
- **Verification:** targeted FEN suite; pinned engine tests; standard backend checks.

#### CH-015f — Add deflection and overload detectors

- **Description:** implement forcing deflection first and add overload only when candidate rules remain precise.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-015e · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** fixtures prove the forcing line and the target piece/defender; quiet ambiguous cases have no motif tag.
- **Role:** backend.
- **Files likely touched:** modules under verified `backend/app/services/`; tests under verified `backend/tests/`.
- **Verification:** targeted FEN suite; pinned engine tests; standard backend checks.

#### CH-015g — Add discovered mate-pattern labels

- **Description:** label only engine-confirmed mating patterns with explicit legal continuation.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-015f · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** mate and non-mate neighbor FENs pass; mate distance and score type preserved; terminal positions are handled separately.
- **Role:** backend.
- **Files likely touched:** modules under verified `backend/app/services/`; tests under verified `backend/tests/`.
- **Verification:** targeted FEN suite; pinned engine tests; standard backend checks.

#### CH-016a — Blindspot-linked puzzle selector

- **Description:** use only validated motif evidence and CC0 theme tags to rank existing puzzles; keep a mixed queue and source link.
- **Priority / effort / dependencies / status:** P1 · 2 days · CH-015b, CH-009c · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** due reviews still precede new puzzles; sparse theme coverage falls back to mixed queue; game-derived position is unique or omitted; user can hide/remove source.
- **Role:** backend.
- **Files likely touched:** `backend/app/routers/puzzles.py`, `backend/app/models/__init__.py`, `backend/app/services/crud.py`.
- **Verification:** queue selection and solution replay tests; standard backend checks.

#### CH-016b — Show puzzle provenance

- **Description:** show whether a puzzle is a public CC0 puzzle or a reviewed position from the user's own game and link to its source.
- **Priority / effort / dependencies / status:** P1 · 1 day · CH-016a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** user can open source game/ply; deleting the source removes derived review access; generic puzzles remain available when no motif data exists.
- **Role:** frontend.
- **Files likely touched:** `frontend/src/app/puzzles/page.tsx`, `frontend/src/app/analysis/[id]/page.tsx`.
- **Verification:** `cd frontend && npx tsc --noEmit && npm run lint`; manual API contract review.

#### CH-017a — Record first-try recall events

- **Description:** persist first-try outcome, honest recall grade, solve time and scheduler version as auditable attempt data.
- **Priority / effort / dependencies / status:** P2 · 1–2 days · CH-016a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** reveal/retry is not first-try success; event has source, rating band and motif; migration preserves existing SM-2 due state.
- **Role:** backend.
- **Files likely touched:** `backend/app/models/__init__.py`, `backend/app/routers/puzzles.py`, new migration under `backend/alembic/versions/`.
- **Verification:** targeted API tests; migration check; standard backend checks.

#### CH-017b — Compare SM-2 and FSRS offline

- **Description:** replay recorded grades through both schedulers and report recall prediction/review burden without changing production scheduling.
- **Priority / effort / dependencies / status:** P2 · 1–2 days · CH-017a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** identical histories replay deterministically; output reports sample size and uncertainty; no scheduler switch unless a separate evaluation decision is recorded.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/sm2.py`, `backend/pyproject.toml`, tests under verified `backend/tests/`. Any new dependency requires explicit issue approval.
- **Verification:** scheduler unit suite; `cd backend && GROQ_API_KEY= pytest -q`.

#### CH-018 — Endgame tablebase adapter

- **Description:** optional, bounded Lichess Syzygy lookup for eligible ≤7-piece positions with cache and local-engine fallback.
- **Priority / effort / dependencies / status:** P2 · 2 days · CH-009a, CH-012, CH-014a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** clear eligibility and remote preference; correct WDL/DTZ interpretation; outage/timeouts fallback; no large tablebase files; no paid endpoint.
- **Role:** backend.
- **Files likely touched:** new module under verified `backend/app/services/`, `backend/app/config.py`, existing `backend/app/routers/`.
- **Verification:** mocked API/timeout tests, known endgame FEN fixtures, standard backend checks.

#### CH-019a — Validate factual explanation claims

- **Description:** build a structured fact packet and reject unsupported piece, square, move, PV or score claims.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-014b, CH-015b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** invalid claim rejected; PV is legal from FEN; outputs only reference supplied metric/depth; contradiction set recorded.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/explainer.py`, `backend/app/routers/analysis.py`, new tests under verified `backend/tests/`.
- **Verification:** golden explanation tests with fake output; no outbound calls; standard backend checks.

#### CH-019b — Add deterministic explanation fallbacks

- **Description:** render a short template from validated facts and clearly report unavailable/invalid optional provider output.
- **Priority / effort / dependencies / status:** P1 · 1 day · CH-019a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** no API key needed; template contains no fact beyond the input packet; model/provider name is not misreported; failures do not block analysis completion.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/explainer.py`, `backend/app/routers/analysis.py`, tests under verified `backend/tests/`.
- **Verification:** offline golden tests; default no-key test; standard backend checks.

#### CH-020a — Build evidence-linked plan data

- **Description:** replace placeholder metrics and arbitrary expected Elo gains with deterministic SQL profile facts and rating-band-aware task rules.
- **Priority / effort / dependencies / status:** P2 · 1–2 days · CH-012, CH-015b, CH-016a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** each weakness has source games, denominator and confidence; sparse data returns collection guidance; no unsupported rating gain or unsupported advanced opening task.
- **Role:** backend.
- **Files likely touched:** `backend/app/services/curriculum.py`, `backend/app/routers/plan.py`, `backend/app/schemas/__init__.py`.
- **Verification:** hand-built profile fixtures; default no-key test; standard backend checks.

#### CH-020b — Render evidence-linked plan actions

- **Description:** show evidence links, sample counts and “not enough data” state in the plan UI.
- **Priority / effort / dependencies / status:** P2 · 1 day · CH-020a · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** every metric links to its source; low-sample state is visible; task links remain valid; no made-up Elo gains shown.
- **Role:** frontend.
- **Files likely touched:** `frontend/src/app/plan/page.tsx`, `frontend/src/app/plan/plan.module.css`.
- **Verification:** `cd frontend && npx tsc --noEmit && npm run lint`; manual response fixture.

#### CH-021 — Self-host release and privacy path

- **Description:** perform fresh-clone, backup/restore, Compose and CI release checks; fix only release-blocking infrastructure issues.
- **Priority / effort / dependencies / status:** P0 for public release · 1–2 days · CH-007, CH-009d, CH-010b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** new contributor can run without paid service; no private games in demo; LLM disabled by default; delete and export verified; all bundled source licenses recorded.
- **Role:** devops.
- **Files likely touched:** `docker-compose.yml`, `.env.example`, `backend/Dockerfile`, `backend/entrypoint.sh`, `.github/workflows/ci.yml`.
- **Verification:** clean-clone instructions, Compose boot, CI green, license and secret scans, backup/delete manual log.

#### CH-022 — Pilot measures and release decision

- **Description:** run opt-in usability/retention pilot or single-user longitudinal study; publish evidence report and revise next-year roadmap.
- **Priority / effort / dependencies / status:** P1 · 1–2 days after pilot data exists · CH-012, CH-016a, CH-019a, CH-021 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** report includes user count, denominators, missing data, consent/deletion, confidence and limitations; no causal Elo claim; roadmap change log updated.
- **Role:** docs.
- **Files likely touched:** new report under verified `docs/`; `CHESSIAN_PROJECT_ROADMAP.md`.
- **Verification:** source data reproducibility, report peer review, links and methodology reviewed.

#### CH-023 — Add issue templates and good-first-issue labels

- **Description:** add small bug/feature templates and document the label workflow so outside contributors can pick bounded tasks.
- **Priority / effort / dependencies / status:** P1 · 1 day · CH-008 · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** templates request reproduction/acceptance evidence; good-first-issue labels point to a single backlog ID and role; no external service is required.
- **Role:** devops.
- **Files likely touched:** new files under verified `.github/`; existing `.github/pull_request_template.md`.
- **Verification:** inspect rendered GitHub templates through repository tree and validate YAML/front matter syntax if used.

#### CH-024 — Persist confirmed player identity per game

- **Description:** add an owner-scoped API operation to confirm which color belongs to the importing player, including an explicit unknown state for ambiguous archives.
- **Priority / effort / dependencies / status:** P1 · 1–2 days · CH-009b · Not Started. **Size:** S (one small PR).
- **Acceptance criteria:** confirmation is persisted per game; callers can only update owned games; identity can be cleared to unknown; opening and profile queries consume the confirmed field; existing rows are not silently rewritten from username frequency.
- **Role:** backend.
- **Files likely touched:** `backend/app/routers/games.py`, `backend/app/services/crud.py`, `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`, new migration under `backend/alembic/versions/`.
- **Verification:** targeted ownership/API tests; migration upgrade on disposable DB; standard backend checks.

### Required living-document rules

- The roadmap is the single source of truth.
- A task is marked Completed only after repository-level verification, with the PR link and the verification output recorded.
- New features enter the roadmap only after an evaluation entry (problem, value, cost, dependencies).
- Architecture changes and decisions are recorded with rationale in a decision log. Superseded decisions are marked superseded, never deleted.
- A defined update procedure runs after each milestone: reconcile backlog with repository state, update the progress tracker, add a change log entry, review dependencies.

### Milestone update procedure

At the end of every month: (1) read `git status`, merged PRs and changed source; (2) verify each in-scope task against its acceptance criteria and recorded commands; (3) set status only from the allowed list; (4) add PR link and exact output for Completed tasks; (5) update risks, dependencies and the progress tracker; (6) append a change-log line with date and reason; (7) review open questions and defer lower priorities if the next milestone is blocked. A roadmap edit is documentation work; implementation status is never inferred from a plan or issue merge alone.

### Progress tracker at audit start

| Area | Baseline as of 2026-10-30 | Next evidence gate |
|---|---|---|
| Import/library/analysis UI | Verified present | End-to-end import and analysis on disposable DB + Stockfish |
| Opening repertoire | Verified present, accuracy dependent on faulty metric | Reconcile response to games from both colors after v2 re-analysis |
| Puzzle/SM-2 | Code present; 15 backend tests pass | DB/UI attempt and due-queue integration test |
| Play vs engine | Code present | Run with installed Stockfish; remove misleading random fallback or label it clearly |
| Diagnosis/coach | Plan route present but inputs flawed; `/coach` placeholder | Versioned, confidence-qualified profile with evidence links |
| CI | Existing workflow and local checks pass | Capture a green remote PR run, add Docker/migration gates |
| Self-host release | Compose syntax passes; runtime unverified | Fresh clone, empty-volume build/boot, backup/delete and license checks |

### Decision log

| ID | Proposed decision | Rationale | Status / revisit condition |
|---|---|---|---|
| ADR-001 | Keep a modular monolith and PostgreSQL | Smallest maintainable system for solo contributor; current stack already exists | Proposed; revisit only with measured scale pressure |
| ADR-002 | Use a Postgres job table + worker before adopting broker | Survives restart without adding Redis/Celery operations | Proposed; revisit with throughput evidence |
| ADR-003 | Owner-first self-host authentication, no shared dev identity | Protects user data while keeping clone setup manageable | Proposed; public multi-user release requires threat review |
| ADR-004 | Deterministic profile/SQL before RAG or broad chat | User-game questions are usually structured queries and need citations | Proposed; revisit only with validated unstructured query demand |
| ADR-005 | Keep SM-2 until recall data supports a scheduler comparison | Avoids replacing known behavior on theory alone | Proposed; revisit after prospective histories exist |
| ADR-006 | Optional free-provider LLM, disabled without explicit configuration, templates always work | Free quotas and models change; zero spend must be enforceable | Proposed; revisit provider only when current free terms are verified |

### Open questions and decisions

| Question | Why unresolved | Owner decision needed by | Safe default |
|---|---|---|---|
| What exact meaning should “accuracy” have: per-move mean or Lichess-style volatility-weighted/harmonic game score? | Both are defensible; identical naming would mislead | Month 1 | Name and version a simple mean, benchmark before more complexity |
| Which Stockfish release/build and supported hardware define reproducible analysis? | Installed binary/build is not recorded today | Month 1 | Pin/test one supported release; expose different local builds in provenance |
| Which opening line dataset has suitable redistribution license and adequate 800–1800 coverage? | No opening database dependency or license inventory exists | Month 4 | Boundary unknown; never infer from ECO header alone |
| What endgame material rule best matches player learning rather than academic definition? | Material heuristics have edge cases and require review | Month 4 | Separate “no queens/low material” rule and uncertain transition label |
| Should self-host auth support one owner only or multiple accounts on one instance? | Privacy support and setup/security cost differ | Month 2 | One owner per instance, with strict ownership model to permit later expansion |
| Which free LLM provider/model remains available without billing and with acceptable privacy? | Free tiers and retention terms change | Month 10 | No key/no outbound LLM; deterministic templates |
| Can puzzle dataset additions be fetched on first run, or must the demo be fully offline? | Current seed requires network and undeclared `zstandard` | Month 1 | Check in a small license-reviewed demo subset, not full data |
| Are existing `pgdata`, `qdrant`, `storage`, virtualenvs and test PGN user-owned, generated or tracked? | Directory presence alone does not establish ownership | Before any cleanup work | Audit git tracking and preserve all data until owner confirms |
| Does public self-hosting need direct internet exposure or only localhost/reverse proxy? | Changes auth, TLS, CORS and threat model | Month 11 | Localhost/reverse proxy documented; no promise of internet-safe turnkey hosting |
| What constitutes enough sample size for profile rates and motif summaries? | No pilot data exists | Months 3–6 | Show numerator/denominator and suppress low counts; tune only from pilot evidence |

### Change log

| Date | Change |
|---|---|
| 2026-10-30 | Initial repository-backed audit and proposed roadmap. No source changes made. |

## 28. KPI definitions and sources

### KPI definitions

| KPI | Measurement | Single-user / no-user-base method | Guardrail |
|---|---|---|---|
| Analysis accuracy | Compare position scores and best-move/WDL labels to a reference Stockfish build at a fixed depth/nodes policy; report score MAE, label agreement and threshold flips | Versioned golden FENs plus 20+ stratified PGNs; re-run when engine/policy changes | Never compare unlike depths/builds without explicit caveat; preserve mate scores and confidence |
| Explanation contradiction rate | Manually sample outputs and automatically validate piece/square/move/PV claims; `contradictory outputs / reviewed outputs` | Golden positions plus each user's optional feedback queue | Target zero invalid legal/piece claims in golden tests; publish denominator and review policy |
| Puzzle retention curve | First-try correct recall at scheduled 1/7/30/90-day review by motif and rating band | One user can contribute a longitudinal curve; display due/attempted counts | Revealed, retried or missed reviews are not counted as successful first recall |
| Time-to-first-insight | Time from import completion to first completed analysis and first evidence-linked profile finding | Per local instance; report median and p90 once enough imports exist | Separate queue wait, engine runtime and profile latency; no silent failed analysis |
| Analysis latency | Wall time per game and per searched position by depth/build/position count and hardware | Local benchmark PGNs, repeat runs and per-instance history | Report median/p95 and hardware; CPU cost is local and bounded by queue concurrency |
| Cost | External spend and provider calls | Default expected cost is $0; monthly counter for outbound LLM/tablebase calls | No paid provider, billing fallback or usage-based hosting; users opt in to remote free endpoints and quota loss is graceful |
| Player behavior change | Change in repeated, measurable error/opportunity rates and first-try re-test recall across windows | One user compares own 30/60/90-day baseline with same time control and analysis version | Correlation only; rating changes are contextual, not causal proof of product effect |
| Contributor health | External first PRs, time to first review, CI pass rate, issue age and docs setup completion | Public GitHub issue/PR history and a short contributor survey | Do not optimize raw issue volume; prioritize safe small contributions and maintainer response capacity |

### Source list

**Chess evaluation and engines**

- [Lichess Accuracy metric](https://lichess.org/page/accuracy) — Win% transform, move accuracy transform, and game aggregation description.
- [Lichess `AccuracyPercent.scala`](https://github.com/lichess-org/lila/blob/master/modules/analyse/src/main/AccuracyPercent.scala) — source implementation; implementation details can evolve.
- [Lichess `Advice.scala`](https://raw.githubusercontent.com/lichess-org/lila/master/modules/tree/src/main/Advice.scala) — current move-judgment bands are applied to normalized winning-chance loss; this is a product policy reference, not a universal chess standard.
- [Stockfish](https://stockfishchess.org/about/) and [official Stockfish source](https://github.com/official-stockfish/Stockfish) — engine, UCI implementation and GPLv3 licensing information.
- [python-chess PGN documentation](https://python-chess.readthedocs.io/en/latest/pgn.html) and [engine documentation](https://python-chess.readthedocs.io/en/latest/engine.html) — board/variant PGN handling and UCI process APIs.
- [Lichess Tablebase API specification](https://github.com/lichess-org/api/blob/master/doc/specs/tags/tablebase/standard.yaml), [tablebase service](https://github.com/lichess-org/lila-tablebase), and [seven-piece tablebase announcement](https://lichess.org/@/lichess/blog/7-piece-syzygy-tablebases-are-complete/W3WeMyQA) — remote Syzygy lookup concept and endpoint source.

**Data, schedulers and human chess models**

- [Lichess open database](https://database.lichess.org/) — states that exports, including puzzle CSV, are CC0 and documents downloadable datasets.
- [Open Spaced Repetition / FSRS](https://open-spaced-repetition.github.io/) and [FSRS implementation docs](https://docs.rs/fsrs/latest/fsrs/) — open implementation and scheduler overview; compare with local data before adoption.
- [Maia paper, “Aligning Superhuman AI with Human Behavior: Chess as a Model System”](https://arxiv.org/abs/2006.01855) — human move prediction research; a research result, not a requirement for this product.

**Competitive product references**

- [Lichess feature list](https://lichess.org/features) — analysis, Chess Insights, puzzles, personal opening explorer and tablebase availability.
- [Chess.com Game Review documentation](https://support.chess.com/en/articles/8584089-how-does-game-review-work), [Chess.com Analysis](https://www.chess.com/analysis), and [Chess.com Insights](https://support.chess.com/en/articles/8708925-what-is-insights-on-chess-com).
- [Aimchess](https://aimchess.com/) — public product description of cross-game analytics and personalized exercises; claims are vendor descriptions, not independently validated here.
- [DecodeChess features](https://decodechess.com/features/) — engine explanation and position-insight positioning.
- [ChessTempo manual](https://chesstempo.com/manual/en/manual.html) and [feature overview](https://ch.chesstempo.com/) — tactics rating, opening training, endgame and spaced repetition features.
- [Chessable](https://www.chessable.com/) — course and interactive chess learning platform; this audit did not verify current plan/feature limits.
- [ChessBase Opening Repertoire](https://mymoves.chessbase.com/en/Openings) and [ChessBase '26](https://cb26.chessbase.com/) — repertoire training and opening research examples.

**Project-specific evidence**

- `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `docs/feature-research.md`, `.agents/{backend,frontend,qa,docs,devops}.md`, `.github/workflows/ci.yml`, backend source and tests, frontend source, `docker-compose.yml`, Dockerfiles, `.env.example`, `LICENSE`.

### Open Questions and Decisions

The full unresolved decision list is maintained in Section 27, including metric semantics, engine build, opening dataset license, endgame definitions, authentication scope, free-provider choice, offline demo data, local artifacts ownership, deployment exposure and minimum sample sizes. No question below should be silently treated as approved merely because a roadmap task references the safe default.
