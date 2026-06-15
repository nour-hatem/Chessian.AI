"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { Chess } from "chess.js";
import Navbar from "@/components/Layout/Navbar";
import ChessBoard from "@/components/Board/ChessBoard";
import EvalBar from "@/components/EvalBar/EvalBar";
import MoveList, { MoveEntry } from "@/components/MoveList/MoveList";
import EvalChart from "@/components/EvalChart/EvalChart";
import type { EvalPoint } from "@/components/EvalChart/EvalChart";
import styles from "./analysis.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types ─── */
interface MoveAnalysis {
  move_number: number;
  color: string;
  move_san: string;
  eval_before: number | null;
  eval_after: number | null;
  cp_loss: number | null;
  classification: string | null;
  best_move_san: string | null;
  is_critical_moment: boolean;
  explanation: string | null;
}

interface GameAnalysis {
  game_id: string;
  status: string;
  white_accuracy: number | null;
  black_accuracy: number | null;
  white_blunders: number;
  white_mistakes: number;
  white_inaccuracies: number;
  black_blunders: number;
  black_mistakes: number;
  black_inaccuracies: number;
  opening_accuracy: number | null;
  middlegame_accuracy: number | null;
  endgame_accuracy: number | null;
  moves: MoveAnalysis[];
}

interface GameMeta {
  id: string;
  white_username: string | null;
  black_username: string | null;
  result: string | null;
  opening_name: string | null;
  opening_eco: string | null;
  time_control: string | null;
  played_at: string | null;
  source: string;
}

/* ─── Helpers ─── */
function getResultClass(result: string | null): string {
  if (result === "1-0") return styles.resultWin;
  if (result === "0-1") return styles.resultLoss;
  return styles.resultDraw;
}

function getClassBadge(classification: string | null): string {
  switch (classification) {
    case "brilliant":   return styles.classBrilliant;
    case "great":       return styles.classGreat;
    case "best":        return styles.classBest;
    case "good":        return styles.classGood;
    case "inaccuracy":  return styles.classInaccuracy;
    case "mistake":     return styles.classMistake;
    case "blunder":     return styles.classBlunder;
    default:            return "";
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/* ─── Component ─── */
export default function AnalysisPage() {
  const params = useParams();
  const gameId = params.id as string;

  const [gameMeta, setGameMeta] = useState<GameMeta | null>(null);
  const [analysis, setAnalysis] = useState<GameAnalysis | null>(null);
  const [pgn, setPgn] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0);

  /* ─── Fetch all data ─── */
  useEffect(() => {
    if (!gameId) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [metaResp, analysisResp, pgnResp] = await Promise.all([
          fetch(`${API_BASE}/api/games/${gameId}`),
          fetch(`${API_BASE}/api/analysis/${gameId}`),
          fetch(`${API_BASE}/api/games/${gameId}/pgn`),
        ]);

        if (!metaResp.ok) throw new Error("Game not found");
        setGameMeta(await metaResp.json());

        if (analysisResp.ok) {
          setAnalysis(await analysisResp.json());
        }

        if (pgnResp.ok) {
          setPgn(await pgnResp.text());
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [gameId]);

  /* ─── Parse PGN into ordered FEN array ─── */
  const fenHistory = useMemo(() => {
    if (!pgn) return [];
    try {
      const chess = new Chess();
      chess.loadPgn(pgn);
      const history = chess.history({ verbose: true });

      // Rebuild from scratch to get FEN at each position
      const rebuild = new Chess();
      const fens = [rebuild.fen()]; // starting position
      for (const move of history) {
        rebuild.move(move.san);
        fens.push(rebuild.fen());
      }
      return fens;
    } catch {
      return [];
    }
  }, [pgn]);

  /* ─── Build move list entries ─── */
  const moveEntries: MoveEntry[] = useMemo(() => {
    if (!analysis?.moves) return [];

    const entries: MoveEntry[] = [];
    const grouped = new Map<number, { white?: MoveAnalysis; black?: MoveAnalysis }>();

    for (const m of analysis.moves) {
      const existing = grouped.get(m.move_number) || {};
      if (m.color === "white") existing.white = m;
      else existing.black = m;
      grouped.set(m.move_number, existing);
    }

    for (const [num, pair] of grouped) {
      if (pair.white) {
        entries.push({
          number: num,
          white: {
            san: pair.white.move_san,
            classification: pair.white.classification || undefined,
          },
          black: pair.black
            ? {
                san: pair.black.move_san,
                classification: pair.black.classification || undefined,
              }
            : undefined,
        });
      }
    }

    return entries;
  }, [analysis]);

  /* ─── Build eval chart data ─── */
  const evalData: EvalPoint[] = useMemo(() => {
    if (!analysis?.moves) return [];
    return analysis.moves.map((m, i) => ({
      moveIndex: i + 1, // 1-indexed to match FEN history
      eval: m.eval_after ?? 0,
      classification: m.classification || undefined,
    }));
  }, [analysis]);

  /* ─── Current FEN ─── */
  const currentFen = fenHistory[currentMoveIndex] || fenHistory[0] || "start";

  /* ─── Current eval (for EvalBar) ─── */
  const currentEval = useMemo(() => {
    if (!analysis?.moves || currentMoveIndex === 0) return 0;
    const moveData = analysis.moves[currentMoveIndex - 1];
    return moveData?.eval_after ?? 0;
  }, [analysis, currentMoveIndex]);

  /* ─── Current move detail ─── */
  const currentMoveDetail = useMemo(() => {
    if (!analysis?.moves || currentMoveIndex === 0) return null;
    return analysis.moves[currentMoveIndex - 1] || null;
  }, [analysis, currentMoveIndex]);

  /* ─── Critical moments ─── */
  const criticalMoments = useMemo(() => {
    if (!analysis?.moves) return [];
    return analysis.moves
      .filter((m) => m.is_critical_moment)
      .sort((a, b) => (b.cp_loss ?? 0) - (a.cp_loss ?? 0));
  }, [analysis]);

  /* ─── Navigation ─── */
  const goToMove = useCallback(
    (index: number) => {
      const maxIndex = fenHistory.length - 1;
      setCurrentMoveIndex(Math.max(0, Math.min(maxIndex, index)));
    },
    [fenHistory.length]
  );

  const goFirst = useCallback(() => goToMove(0), [goToMove]);
  const goPrev = useCallback(
    () => setCurrentMoveIndex((prev) => Math.max(0, prev - 1)),
    []
  );
  const goNext = useCallback(
    () =>
      setCurrentMoveIndex((prev) =>
        Math.min(fenHistory.length - 1, prev + 1)
      ),
    [fenHistory.length]
  );
  const goLast = useCallback(
    () => goToMove(fenHistory.length - 1),
    [goToMove, fenHistory.length]
  );

  /* ─── Keyboard navigation ─── */
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") goPrev();
      else if (e.key === "ArrowRight") goNext();
      else if (e.key === "Home") goFirst();
      else if (e.key === "End") goLast();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [goPrev, goNext, goFirst, goLast]);

  /* ─── Find move index from analysis move ─── */
  const findMoveIndex = useCallback(
    (m: MoveAnalysis): number => {
      if (!analysis?.moves) return 0;
      const idx = analysis.moves.findIndex(
        (mv) =>
          mv.move_number === m.move_number &&
          mv.color === m.color &&
          mv.move_san === m.move_san
      );
      return idx >= 0 ? idx + 1 : 0;
    },
    [analysis]
  );

  /* ─── Loading state ─── */
  if (loading) {
    return (
      <>
        <Navbar />
        <main className={styles.analysisPage}>
          <div className={styles.loadingState}>
            <div className={styles.loadingSpinner} />
            <p>Loading analysis...</p>
          </div>
        </main>
      </>
    );
  }

  /* ─── Error state ─── */
  if (error || !gameMeta) {
    return (
      <>
        <Navbar />
        <main className={styles.analysisPage}>
          <div className={styles.errorState}>
            <h2>Game Not Found</h2>
            <p>{error || "Unable to load game data."}</p>
            <a href="/library" className={styles.backLink}>← Back to Library</a>
          </div>
        </main>
      </>
    );
  }

  /* ─── Analysis pending / processing ─── */
  if (!analysis || analysis.status === "pending" || analysis.status === "processing") {
    return (
      <>
        <Navbar />
        <main className={styles.analysisPage}>
          <div className={styles.pendingState}>
            <div className={styles.pendingIcon}>⏳</div>
            <h2 className={styles.pendingTitle}>
              {analysis?.status === "processing" ? "Analyzing..." : "Analysis Not Started"}
            </h2>
            <p className={styles.pendingText}>
              {analysis?.status === "processing"
                ? "Stockfish is evaluating every move. This can take a few minutes depending on the game length."
                : "This game hasn't been analyzed yet. Go back to the library and click Analyze."}
            </p>
            <a href="/library" className={styles.backLink}>← Back to Library</a>
          </div>
        </main>
      </>
    );
  }

  /* ─── Main analysis view ─── */
  const maxMoveIndex = fenHistory.length - 1;

  return (
    <>
      <Navbar />
      <main className={styles.analysisPage}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <div className={styles.headerPlayers}>
              ⬜ {gameMeta.white_username || "White"} vs ⬛ {gameMeta.black_username || "Black"}
            </div>
            <div className={styles.headerMeta}>
              <span>{gameMeta.opening_name || gameMeta.opening_eco || "—"}</span>
              <span>·</span>
              <span>{gameMeta.time_control || "—"}</span>
              <span>·</span>
              <span>{formatDate(gameMeta.played_at)}</span>
            </div>
          </div>
          <span className={`${styles.headerResult} ${getResultClass(gameMeta.result)}`}>
            {gameMeta.result || "?"}
          </span>
        </div>

        {/* Main Layout */}
        <div className={styles.analysisLayout}>
          {/* Board + EvalBar */}
          <div className={styles.boardSection}>
            <EvalBar evaluation={currentEval} />

            <div className={styles.boardColumn}>
              <ChessBoard
                fen={currentFen}
                orientation="white"
                interactive={false}
                viewOnly={true}
              />

              {/* Navigation Controls */}
              <div className={styles.navControls}>
                <button
                  className={styles.navBtn}
                  onClick={goFirst}
                  disabled={currentMoveIndex <= 0}
                  title="First move (Home)"
                  id="nav-first"
                >
                  ⏮
                </button>
                <button
                  className={styles.navBtn}
                  onClick={goPrev}
                  disabled={currentMoveIndex <= 0}
                  title="Previous move (←)"
                  id="nav-prev"
                >
                  ◀
                </button>
                <button
                  className={styles.navBtn}
                  onClick={goNext}
                  disabled={currentMoveIndex >= maxMoveIndex}
                  title="Next move (→)"
                  id="nav-next"
                >
                  ▶
                </button>
                <button
                  className={styles.navBtn}
                  onClick={goLast}
                  disabled={currentMoveIndex >= maxMoveIndex}
                  title="Last move (End)"
                  id="nav-last"
                >
                  ⏭
                </button>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className={styles.sidebar}>
            {/* Accuracy Stats */}
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>White Accuracy</div>
                <div className={`${styles.statValue} ${styles.statValueWhite}`}>
                  {analysis.white_accuracy != null
                    ? `${analysis.white_accuracy.toFixed(1)}%`
                    : "—"}
                </div>
                <div className={styles.statSub}>{gameMeta.white_username || "White"}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>Black Accuracy</div>
                <div className={`${styles.statValue} ${styles.statValueBlack}`}>
                  {analysis.black_accuracy != null
                    ? `${analysis.black_accuracy.toFixed(1)}%`
                    : "—"}
                </div>
                <div className={styles.statSub}>{gameMeta.black_username || "Black"}</div>
              </div>
            </div>

            {/* Error Summary */}
            <div className={styles.errorSummary}>
              <div className={styles.errorSummaryTitle}>Move Classification</div>
              <div className={styles.errorRow}>
                <span className={styles.errorLabel}>
                  <span className={styles.errorDot} style={{ background: "var(--move-blunder)" }} />
                  Blunders
                </span>
                <div className={styles.errorCounts}>
                  <span className={styles.errorCountWhite}>{analysis.white_blunders}</span>
                  <span className={styles.errorCountBlack}>{analysis.black_blunders}</span>
                </div>
              </div>
              <div className={styles.errorRow}>
                <span className={styles.errorLabel}>
                  <span className={styles.errorDot} style={{ background: "var(--move-mistake)" }} />
                  Mistakes
                </span>
                <div className={styles.errorCounts}>
                  <span className={styles.errorCountWhite}>{analysis.white_mistakes}</span>
                  <span className={styles.errorCountBlack}>{analysis.black_mistakes}</span>
                </div>
              </div>
              <div className={styles.errorRow}>
                <span className={styles.errorLabel}>
                  <span className={styles.errorDot} style={{ background: "var(--move-inaccuracy)" }} />
                  Inaccuracies
                </span>
                <div className={styles.errorCounts}>
                  <span className={styles.errorCountWhite}>{analysis.white_inaccuracies}</span>
                  <span className={styles.errorCountBlack}>{analysis.black_inaccuracies}</span>
                </div>
              </div>
            </div>

            {/* Eval Chart */}
            <EvalChart
              evalData={evalData}
              currentMoveIndex={currentMoveIndex}
              onMoveClick={goToMove}
            />

            {/* Critical Moments */}
            {criticalMoments.length > 0 && (
              <div className={styles.criticalMoments}>
                <div className={styles.criticalTitle}>
                  Critical Moments ({criticalMoments.length})
                </div>
                <div className={styles.criticalList}>
                  {criticalMoments.map((m, i) => (
                    <div
                      key={i}
                      className={styles.criticalItem}
                      onClick={() => goToMove(findMoveIndex(m))}
                    >
                      <span className={styles.criticalIcon}>
                        {m.classification === "blunder" ? "💥" : "⚠️"}
                      </span>
                      <div className={styles.criticalInfo}>
                        <div className={styles.criticalMove}>
                          {m.move_number}. {m.color === "black" ? "..." : ""}{m.move_san}
                        </div>
                        <div className={styles.criticalClass}>{m.classification}</div>
                      </div>
                      <span className={styles.criticalCpLoss}>
                        {m.cp_loss != null ? `-${Math.round(m.cp_loss)}cp` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Current Move Detail */}
            {currentMoveDetail && (
              <div className={styles.moveDetail}>
                <div className={styles.moveDetailTitle}>Move Detail</div>
                <div className={styles.moveDetailContent}>
                  <div className={styles.moveDetailRow}>
                    <span className={styles.moveDetailLabel}>Move</span>
                    <span className={styles.moveDetailValue}>
                      {currentMoveDetail.move_number}.
                      {currentMoveDetail.color === "black" ? ".." : ""}{" "}
                      {currentMoveDetail.move_san}
                    </span>
                  </div>
                  <div className={styles.moveDetailRow}>
                    <span className={styles.moveDetailLabel}>Classification</span>
                    <span
                      className={`${styles.classificationBadge} ${getClassBadge(
                        currentMoveDetail.classification
                      )}`}
                    >
                      {currentMoveDetail.classification || "—"}
                    </span>
                  </div>
                  {currentMoveDetail.cp_loss != null && currentMoveDetail.cp_loss > 0 && (
                    <div className={styles.moveDetailRow}>
                      <span className={styles.moveDetailLabel}>CP Loss</span>
                      <span className={styles.moveDetailValue}>
                        {Math.round(currentMoveDetail.cp_loss)}
                      </span>
                    </div>
                  )}
                  {currentMoveDetail.best_move_san &&
                    currentMoveDetail.best_move_san !== currentMoveDetail.move_san && (
                      <div className={styles.moveDetailRow}>
                        <span className={styles.moveDetailLabel}>Best Move</span>
                        <span className={styles.moveDetailValue}>
                          {currentMoveDetail.best_move_san}
                        </span>
                      </div>
                    )}
                  {currentMoveDetail.eval_after != null && (
                    <div className={styles.moveDetailRow}>
                      <span className={styles.moveDetailLabel}>Eval After</span>
                      <span className={styles.moveDetailValue}>
                        {currentMoveDetail.eval_after > 0 ? "+" : ""}
                        {(currentMoveDetail.eval_after / 100).toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Move List */}
            <MoveList
              moves={moveEntries}
              currentMoveIndex={currentMoveIndex}
              onMoveClick={goToMove}
            />
          </div>
        </div>
      </main>
    </>
  );
}
