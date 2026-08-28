"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Chess } from "chess.js";
import Navbar from "@/components/Layout/Navbar";
import ChessBoard from "@/components/Board/ChessBoard";
import styles from "./puzzles.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const OPPONENT_REPLY_MS = 450;
const WRONG_MOVE_RESET_MS = 700;

/* ── Types ── */
interface SM2Data {
  easiness: number;
  interval: number;
  repetitions: number;
  next_due_date: string;
}

interface PuzzleData {
  puzzle_id: string;
  lichess_id: string;
  fen: string;
  moves: string; // space-separated UCI
  themes: string[];
  opening_tags: string[];
  rating: number;
  is_new: boolean;
  sm2: SM2Data | null;
}

interface StatsData {
  total_attempted: number;
  total_correct: number;
  current_streak: number;
  puzzles_due_today: number;
  solved_today: number;
  rating_center: number;
}

type Feedback = "correct" | "wrong" | "solved" | "revealed" | null;

export default function PuzzlesPage() {
  const [puzzle, setPuzzle] = useState<PuzzleData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* Board state — the page is authoritative for the position. */
  const [fen, setFen] = useState("");
  const [revision, setRevision] = useState(0);
  const [movesList, setMovesList] = useState<string[]>([]);
  const [currentMoveIdx, setCurrentMoveIdx] = useState(0);
  const [orientation, setOrientation] = useState<"white" | "black">("white");

  /* Interaction state */
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [sm2Result, setSm2Result] = useState<SM2Data | null>(null);
  const [locked, setLocked] = useState(false);
  const [finished, setFinished] = useState(false);
  const [wrongAttempts, setWrongAttempts] = useState(0);

  const chessRef = useRef<Chess>(new Chess());
  /** Whether this puzzle has already been scored — SM-2 records one grade. */
  const scoredRef = useRef(false);
  /** Every pending timer, so navigating away can't setState on an unmount. */
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const schedule = useCallback((fn: () => void, ms: number) => {
    const t = setTimeout(fn, ms);
    timersRef.current.push(t);
    return t;
  }, []);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* ── Fetching ── */
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/puzzles/stats`);
      if (res.ok) setStats(await res.json());
    } catch {
      /* Stats are supplementary — a failure here must not block solving. */
    }
  }, []);

  const fetchNextPuzzle = useCallback(async () => {
    clearTimers();
    setLoading(true);
    setError("");
    setFeedback(null);
    setSm2Result(null);
    setLocked(false);
    setFinished(false);
    setWrongAttempts(0);
    scoredRef.current = false;

    try {
      const res = await fetch(`${API_BASE}/api/puzzles/next`);
      if (!res.ok) {
        setError(
          res.status === 404
            ? "No puzzles available in your rating band. Everything due has been reviewed."
            : `Failed to load puzzle (HTTP ${res.status})`,
        );
        setPuzzle(null);
        return;
      }

      const data: PuzzleData = await res.json();
      setPuzzle(data);

      const chess = new Chess(data.fen);
      chessRef.current = chess;

      const list = data.moves.trim().split(/\s+/);
      setMovesList(list);

      // The first move in the line is the opponent's setup move; play it so the
      // user sees the position they must solve.
      if (list.length > 0) chess.move(list[0]);

      setFen(chess.fen());
      setRevision((r) => r + 1);
      setCurrentMoveIdx(1);
      setOrientation(chess.turn() === "w" ? "white" : "black");
    } catch {
      setError("Cannot connect to backend.");
      setPuzzle(null);
    } finally {
      setLoading(false);
    }
  }, [clearTimers]);

  useEffect(() => {
    fetchStats();
    fetchNextPuzzle();
  }, [fetchStats, fetchNextPuzzle]);

  /* ── Scoring ── */
  const submitAttempt = useCallback(
    async (correct: boolean) => {
      if (!puzzle || scoredRef.current) return;
      // SM-2 takes one grade per puzzle: the first outcome is the honest one.
      // Without this guard, retrying a hard puzzle logged a fresh quality-0
      // every attempt and drove the easiness factor into its floor.
      scoredRef.current = true;

      try {
        const res = await fetch(
          `${API_BASE}/api/puzzles/${puzzle.puzzle_id}/attempt`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ correct, time_spent_ms: 0 }),
          },
        );
        if (res.ok) {
          const result = await res.json();
          setSm2Result(result.sm2);
          fetchStats();
        }
      } catch {
        /* Leave the grade unrecorded rather than blocking the UI. */
      }
    },
    [puzzle, fetchStats],
  );

  /* ── Move handling ── */
  const onMove = useCallback(
    (from: string, to: string, promotion?: string) => {
      if (locked || finished) return;

      const chess = chessRef.current;
      const expected = movesList[currentMoveIdx];
      const uci = `${from}${to}${promotion ?? ""}`;

      /* Wrong move — snap back to the authoritative position. */
      if (uci !== expected) {
        setWrongAttempts((n) => n + 1);
        setFeedback("wrong");
        setLocked(true);
        submitAttempt(false);

        schedule(() => {
          // chessRef was never advanced, so its FEN is the correct position.
          // Bumping `revision` forces the board to re-sync even though the FEN
          // string is unchanged, which is what actually returns the piece.
          setFen(chess.fen());
          setRevision((r) => r + 1);
          setFeedback(null);
          setLocked(false);
        }, WRONG_MOVE_RESET_MS);
        return;
      }

      /* Correct move. */
      try {
        chess.move({ from, to, promotion });
      } catch {
        return;
      }
      setFen(chess.fen());

      const isLast = currentMoveIdx === movesList.length - 1;
      if (isLast) {
        setFeedback(wrongAttempts === 0 ? "correct" : "solved");
        setFinished(true);
        setLocked(true);
        submitAttempt(wrongAttempts === 0);
        return;
      }

      /* Puzzle continues: the opponent replies. Lock input for that window so
         a fast second move can't desync the solution index. */
      setLocked(true);
      const replyIdx = currentMoveIdx + 1;
      schedule(() => {
        const reply = movesList[replyIdx];
        if (reply) {
          try {
            chess.move(reply);
          } catch {
            /* Malformed line — stop rather than corrupting the position. */
          }
          setFen(chess.fen());
        }
        setCurrentMoveIdx(replyIdx + 1);
        setLocked(false);
      }, OPPONENT_REPLY_MS);
    },
    [
      locked,
      finished,
      movesList,
      currentMoveIdx,
      wrongAttempts,
      submitAttempt,
      schedule,
    ],
  );

  /* ── Show solution ── */
  const showSolution = useCallback(() => {
    if (!puzzle || finished) return;

    clearTimers();
    setLocked(true);
    setFinished(true);
    setFeedback("revealed");
    submitAttempt(false);

    // Play out the rest of the line so the user sees the whole idea.
    const chess = chessRef.current;
    const remaining = movesList.slice(currentMoveIdx);
    remaining.forEach((mv, i) => {
      schedule(() => {
        try {
          chess.move(mv);
          setFen(chess.fen());
          setRevision((r) => r + 1);
        } catch {
          /* Ignore an unplayable tail. */
        }
      }, i * 550);
    });
  }, [puzzle, finished, movesList, currentMoveIdx, submitAttempt, schedule, clearTimers]);

  /* ── Render helpers ── */
  const formatInterval = (days: number) => {
    if (days === 1) return "1 day";
    if (days < 30) return `${days} days`;
    if (days < 365) return `${Math.round(days / 30)} mo`;
    return `${Math.round(days / 365)} yr`;
  };

  const accuracy =
    stats && stats.total_attempted > 0
      ? Math.round((stats.total_correct / stats.total_attempted) * 100)
      : null;

  const bannerText = (() => {
    switch (feedback) {
      case "correct": return "✓ Correct!";
      case "solved": return "✓ Solved";
      case "wrong": return "✗ Not the move — try again";
      case "revealed": return "Solution";
      default: return "Find the best move";
    }
  })();

  const bannerClass =
    feedback === "correct" || feedback === "solved"
      ? styles.feedbackCorrect
      : feedback === "wrong"
        ? styles.feedbackWrong
        : feedback === "revealed"
          ? styles.feedbackRevealed
          : "";

  return (
    <>
      <Navbar />
      <main className={styles.puzzlesPage}>
        <div className={styles.container}>
          {loading ? (
            <div className={styles.loadingState}>Loading next puzzle…</div>
          ) : error ? (
            <div className={styles.errorState}>
              <p>{error}</p>
              <button className="btn-primary" onClick={fetchNextPuzzle}>
                Try again
              </button>
            </div>
          ) : puzzle ? (
            <>
              {/* Board */}
              <div className={styles.boardArea}>
                <div className={`${styles.feedbackBanner} ${bannerClass}`}>
                  {bannerText}
                </div>

                <ChessBoard
                  fen={fen}
                  revision={revision}
                  orientation={orientation}
                  onMove={onMove}
                  interactive={!locked && !finished}
                  allowPremoves={false}
                />

                <p className={styles.turnHint}>
                  {orientation === "white" ? "White" : "Black"} to move
                </p>
              </div>

              {/* Sidebar */}
              <div className={styles.sidebar}>
                {stats && (
                  <div className={styles.card}>
                    <div className={styles.cardTitle}>Your stats</div>
                    <div className={styles.statsGrid}>
                      <div className={styles.statBox}>
                        <span className={styles.statValue}>
                          {stats.solved_today}
                        </span>
                        <span className={styles.statLabel}>Solved today</span>
                      </div>
                      <div className={styles.statBox}>
                        <span className={`${styles.statValue} ${styles.streakValue}`}>
                          {stats.current_streak}
                          {stats.current_streak > 0 ? " 🔥" : ""}
                        </span>
                        <span className={styles.statLabel}>Streak</span>
                      </div>
                      <div className={styles.statBox}>
                        <span className={styles.statValue}>
                          {stats.total_correct}
                        </span>
                        <span className={styles.statLabel}>Total solved</span>
                      </div>
                      <div className={styles.statBox}>
                        <span className={styles.statValue}>
                          {accuracy !== null ? `${accuracy}%` : "—"}
                        </span>
                        <span className={styles.statLabel}>Accuracy</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className={styles.card}>
                  <div className={styles.cardTitle}>This puzzle</div>
                  <div className={styles.infoRow}>
                    <span className={styles.infoLabel}>Rating</span>
                    <span className={styles.infoValue}>{puzzle.rating}</span>
                  </div>
                  <div className={styles.infoRow}>
                    <span className={styles.infoLabel}>Type</span>
                    <span className={styles.infoValue}>
                      {puzzle.is_new ? "New" : "Review"}
                    </span>
                  </div>

                  {/* Themes stay hidden until the puzzle is over — naming the
                      motif gives the answer away. */}
                  {finished && puzzle.themes.length > 0 && (
                    <div className={styles.tags}>
                      {puzzle.themes.slice(0, 5).map((t) => (
                        <span key={t} className={styles.tag}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>

                <div className={styles.actions}>
                  {!finished && (
                    <button
                      className={styles.secondaryAction}
                      onClick={showSolution}
                      id="btn-show-solution"
                    >
                      Show solution
                    </button>
                  )}
                  {finished && (
                    <button
                      className="btn-primary"
                      onClick={fetchNextPuzzle}
                      id="btn-next-puzzle"
                    >
                      Next puzzle →
                    </button>
                  )}
                </div>

                {sm2Result && (
                  <div className={`${styles.card} animate-fade-in`}>
                    <div className={styles.cardTitle}>Review schedule</div>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Next review</span>
                      <span className={styles.infoValue}>
                        in {formatInterval(sm2Result.interval)}
                      </span>
                    </div>
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Easiness</span>
                      <span className={styles.infoValue}>
                        {sm2Result.easiness.toFixed(2)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </main>
    </>
  );
}
