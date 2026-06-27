"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Chess } from "chess.js";
import Navbar from "@/components/Layout/Navbar";
import ChessBoard from "@/components/Board/ChessBoard";
import styles from "./puzzles.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  rating_center: number;
}

export default function PuzzlesPage() {
  const [puzzle, setPuzzle] = useState<PuzzleData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Game state
  const [fen, setFen] = useState("");
  const [movesList, setMovesList] = useState<string[]>([]);
  const [currentMoveIdx, setCurrentMoveIdx] = useState(0); // which move is NEXT
  const [orientation, setOrientation] = useState<"white" | "black">("white");
  
  // UI feedback
  const [feedback, setFeedback] = useState<"correct" | "wrong" | null>(null);
  const [sm2Result, setSm2Result] = useState<SM2Data | null>(null);
  const [waitingForNext, setWaitingForNext] = useState(false);

  const chessRef = useRef<Chess>(new Chess());

  /* ── Fetching ── */
  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/puzzles/stats`);
      if (res.ok) {
        setStats(await res.json());
      }
    } catch (err) {
      console.error("Failed to load stats", err);
    }
  };

  const fetchNextPuzzle = useCallback(async () => {
    setLoading(true);
    setError("");
    setFeedback(null);
    setSm2Result(null);
    setWaitingForNext(false);
    
    try {
      const res = await fetch(`${API_BASE}/api/puzzles/next`);
      if (!res.ok) {
        if (res.status === 404) {
          setError("No puzzles available in your rating band.");
        } else {
          setError(`Failed to load puzzle (HTTP ${res.status})`);
        }
        setLoading(false);
        return;
      }
      const data: PuzzleData = await res.json();
      setPuzzle(data);
      
      // Initialize board
      const chess = new Chess(data.fen);
      chessRef.current = chess;
      
      const mList = data.moves.split(" ");
      setMovesList(mList);
      
      // First move is opponent's setup move
      const setupMove = mList[0];
      chess.move(setupMove);
      setFen(chess.fen());
      setCurrentMoveIdx(1); // User must play move 1
      
      // The user's color is the side to move *after* the setup move
      setOrientation(chess.turn() === "w" ? "white" : "black");
      
    } catch (err) {
      setError("Cannot connect to backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchStats();
    fetchNextPuzzle();
  }, [fetchNextPuzzle]);

  /* ── Submission ── */
  const submitAttempt = async (correct: boolean) => {
    if (!puzzle) return;
    try {
      const res = await fetch(`${API_BASE}/api/puzzles/${puzzle.puzzle_id}/attempt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ correct, time_spent_ms: 5000 }), // dummy time for V1
      });
      if (res.ok) {
        const result = await res.json();
        setSm2Result(result.sm2);
        // Refresh stats (streak etc)
        fetchStats();
      }
    } catch (err) {
      console.error("Failed to submit attempt", err);
    }
  };

  /* ── Move Handling ── */
  const onMove = (from: string, to: string, promotion?: string) => {
    if (waitingForNext || feedback === "wrong") return;
    
    const uci = `${from}${to}${promotion ? promotion : ""}`;
    const expectedUci = movesList[currentMoveIdx];
    
    const chess = chessRef.current;
    
    if (uci === expectedUci) {
      // CORRECT MOVE
      // Move was already made on board by Chessground, but we need to update our Chess instance
      try {
        chess.move({ from, to, promotion });
        setFen(chess.fen());
      } catch (e) {
        console.error("Invalid move caught by chess.js", e);
        return;
      }
      
      if (currentMoveIdx === movesList.length - 1) {
        // Puzzle completed successfully!
        setFeedback("correct");
        submitAttempt(true);
        setWaitingForNext(true);
        setTimeout(() => {
          fetchNextPuzzle();
        }, 1500);
      } else {
        // Correct, but puzzle continues. Opponent replies.
        const nextIdx = currentMoveIdx + 1;
        const opponentMove = movesList[nextIdx];
        
        // Slight delay for realism
        setTimeout(() => {
          chess.move(opponentMove);
          setFen(chess.fen());
          setCurrentMoveIdx(nextIdx + 1);
        }, 500);
      }
    } else {
      // WRONG MOVE
      setFeedback("wrong");
      submitAttempt(false);
      setWaitingForNext(true);
      
      // We don't update chessRef with the wrong move, so we can revert
      setTimeout(() => {
        // Revert board to fen before wrong move
        setFen(chess.fen());
        setFeedback(null);
        setWaitingForNext(false);
        // We could let them try again, but attempt is already marked wrong.
        // Actually, just showing them the correct move or letting them retry is good UX.
        // For V1, we revert and let them keep trying until they get it right to finish the sequence.
      }, 1000);
    }
  };

  /* ── Render Helpers ── */
  const formatInterval = (days: number) => {
    if (days === 1) return "1 day";
    if (days < 30) return `${days} days`;
    if (days < 365) return `${Math.round(days / 30)} mo`;
    return `${Math.round(days / 365)} yr`;
  };

  /* ── Render ── */
  return (
    <>
      <Navbar />
      <main className={styles.puzzlesPage}>
        <div className={styles.container}>
          
          {loading ? (
            <div className={styles.loadingState}>Loading next puzzle...</div>
          ) : error ? (
            <div className={styles.errorState}>
              <p>{error}</p>
              <button className="btn-primary" onClick={fetchNextPuzzle} style={{ marginTop: 16 }}>
                Try Again
              </button>
            </div>
          ) : puzzle ? (
            <>
              {/* Left: Board */}
              <div className={styles.boardArea}>
                <div className={`${styles.feedbackBanner} ${
                  feedback === "correct" ? styles.feedbackCorrect :
                  feedback === "wrong" ? styles.feedbackWrong : ""
                }`}>
                  {feedback === "correct" ? "✓ Correct!" : 
                   feedback === "wrong" ? "✗ Incorrect. Try again." : 
                   (orientation === "white" ? "White to move" : "Black to move")}
                </div>
                
                <ChessBoard
                  fen={fen}
                  orientation={orientation}
                  onMove={onMove}
                  interactive={!waitingForNext}
                />
              </div>

              {/* Right: Sidebar */}
              <div className={styles.sidebar}>
                {stats && (
                  <div className={styles.statsGrid}>
                    <div className={styles.card}>
                      <div className={styles.statBox}>
                        <span className={styles.statLabel}>Current Streak</span>
                        <span className={`${styles.statValue} ${styles.streakValue}`}>
                          {stats.current_streak} 🔥
                        </span>
                      </div>
                    </div>
                    <div className={styles.card}>
                      <div className={styles.statBox}>
                        <span className={styles.statLabel}>Rating Band</span>
                        <span className={`${styles.statValue} ${styles.ratingValue}`}>
                          ~{stats.rating_center}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div className={styles.card}>
                  <div className={styles.cardTitle}>Puzzle Info</div>
                  <div className={styles.infoRow}>
                    <span className={styles.infoLabel}>Rating</span>
                    <span className={styles.infoValue}>{puzzle.rating}</span>
                  </div>
                  <div className={styles.infoRow}>
                    <span className={styles.infoLabel}>Status</span>
                    <span className={styles.infoValue}>
                      {puzzle.is_new ? "New" : "Review"}
                    </span>
                  </div>
                  
                  {(puzzle.themes.length > 0 || puzzle.opening_tags.length > 0) && (
                    <div className={styles.tags}>
                      {puzzle.themes.slice(0, 4).map(t => (
                        <span key={t} className={styles.tag}>{t}</span>
                      ))}
                      {puzzle.opening_tags.slice(0, 1).map(t => (
                        <span key={t} className={styles.tag}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>

                {sm2Result && (
                  <div className={`${styles.card} animate-fade-in`}>
                    <div className={styles.cardTitle}>SM-2 Update</div>
                    <div className={styles.sm2Row}>
                      <span className={styles.infoLabel}>Next Review</span>
                      <span className={styles.infoValue}>
                        in {formatInterval(sm2Result.interval)}
                      </span>
                    </div>
                    <div className={styles.sm2Row}>
                      <span className={styles.infoLabel}>Easiness Factor</span>
                      <span className={styles.infoValue}>{sm2Result.easiness.toFixed(2)}</span>
                    </div>
                  </div>
                )}
                
                {waitingForNext && feedback === "correct" && (
                  <button className={`btn-primary ${styles.nextButton}`} onClick={fetchNextPuzzle}>
                    Next Puzzle ➔
                  </button>
                )}
              </div>
            </>
          ) : null}
        </div>
      </main>
    </>
  );
}
