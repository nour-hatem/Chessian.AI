"use client";

import { useState, useEffect, useMemo } from "react";
import Navbar from "@/components/Layout/Navbar";
import styles from "./openings.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types (derived from crud.get_opening_repertoire return shape) ─── */
interface Opening {
  eco: string;
  name: string;
  games_played: number;
  result_1_0: number;   // wins  (1-0 games)
  result_0_1: number;   // losses (0-1 games)
  result_draw: number;  // draws
  avg_user_accuracy: number | null;
}

interface RepertoireResponse {
  openings: Opening[];
  total: number;
}

type SortKey = "games" | "accuracy";
type SortDir = "asc" | "desc";

/* ─── Helpers ─── */
function accuracyColor(val: number | null): string {
  if (val === null) return styles.accNull;
  if (val >= 80) return styles.accExcellent;
  if (val >= 60) return styles.accGood;
  return styles.accWeak;
}

function formatAccuracy(val: number | null): string {
  if (val === null) return "—";
  return `${val.toFixed(1)}%`;
}

/* ─── Component ─── */
export default function OpeningsPage() {
  const [openings, setOpenings] = useState<Opening[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("games");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  /* ─── Fetch ─── */
  useEffect(() => {
    const fetchRepertoire = async () => {
      setLoading(true);
      setError("");
      try {
        const resp = await fetch(`${API_BASE}/api/games/openings/repertoire`);
        if (!resp.ok) {
          setError(`Failed to load openings (HTTP ${resp.status})`);
          return;
        }
        const data: RepertoireResponse = await resp.json();
        setOpenings(data.openings);
      } catch {
        setError("Cannot connect to backend — is the server running?");
      } finally {
        setLoading(false);
      }
    };

    fetchRepertoire();
  }, []);

  /* ─── Sort ─── */
  const sorted = useMemo<Opening[]>(() => {
    return [...openings].sort((a, b) => {
      if (sortKey === "games") {
        // games_played is always a number
        return sortDir === "asc"
          ? a.games_played - b.games_played
          : b.games_played - a.games_played;
      }
      // accuracy sort — nulls always sink to the end regardless of direction
      if (a.avg_user_accuracy === null && b.avg_user_accuracy === null) return 0;
      if (a.avg_user_accuracy === null) return 1;   // a sinks to end
      if (b.avg_user_accuracy === null) return -1;  // b sinks to end
      // Both are numbers — apply direction
      return sortDir === "asc"
        ? a.avg_user_accuracy - b.avg_user_accuracy
        : b.avg_user_accuracy - a.avg_user_accuracy;
    });
  }, [openings, sortKey, sortDir]);

  /* ─── Sort toggle handler ─── */
  const handleSort = (key: SortKey) => {
    if (sortKey !== key) {
      setSortKey(key);
      // Default: games → desc (most played first), accuracy → desc (best first)
      setSortDir("desc");
    } else {
      setSortDir((prev) => (prev === "desc" ? "asc" : "desc"));
    }
  };

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return <span className={styles.sortIconInactive}>↕</span>;
    return (
      <span className={styles.sortIconActive}>
        {sortDir === "desc" ? "↓" : "↑"}
      </span>
    );
  };

  /* ─── Render ─── */
  return (
    <>
      <Navbar />
      <main className={styles.openingsPage}>
        <div className={styles.container}>
          <h1 className={styles.pageTitle}>
            <span className="gradient-text">Opening</span> Repertoire
          </h1>
          <p className={styles.pageSubtitle}>
            Openings you&apos;ve played in 3 or more analyzed games
          </p>

          {/* Controls */}
          {!loading && !error && openings.length > 0 && (
            <div className={styles.controls}>
              <span className={styles.totalLabel}>
                {openings.length} opening{openings.length !== 1 ? "s" : ""}
              </span>
              <div className={styles.sortGroup}>
                <span className={styles.sortLabel}>Sort by</span>
                <button
                  id="sort-games"
                  className={`${styles.sortBtn} ${sortKey === "games" ? styles.sortBtnActive : ""}`}
                  onClick={() => handleSort("games")}
                >
                  Most Played {sortIcon("games")}
                </button>
                <button
                  id="sort-accuracy"
                  className={`${styles.sortBtn} ${sortKey === "accuracy" ? styles.sortBtnActive : ""}`}
                  onClick={() => handleSort("accuracy")}
                >
                  Avg Accuracy {sortIcon("accuracy")}
                </button>
              </div>
            </div>
          )}

          {/* States */}
          {loading && (
            <div className={styles.loadingState}>Loading openings...</div>
          )}

          {!loading && error && (
            <div className={styles.errorState}>{error}</div>
          )}

          {!loading && !error && openings.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>♞</div>
              <p>No openings yet.</p>
              <p className={styles.emptyHint}>
                Import and analyze at least 3 games in the same opening to see
                repertoire stats here.
              </p>
            </div>
          )}

          {/* Opening rows */}
          {!loading && !error && sorted.length > 0 && (
            <div className={styles.openingsList}>
              {sorted.map((op, i) => {
                const total = op.games_played || 1; // guard divide-by-zero
                const winPct  = (op.result_1_0  / total) * 100;
                const drawPct = (op.result_draw / total) * 100;
                const lossPct = (op.result_0_1  / total) * 100;

                return (
                  <div
                    key={`${op.eco}-${op.name}`}
                    className={`${styles.openingRow} animate-fade-in`}
                    style={{ animationDelay: `${i * 40}ms` }}
                    id={`opening-row-${i}`}
                  >
                    {/* Left: ECO + name + game count */}
                    <div className={styles.rowLeft}>
                      {op.eco && (
                        <span className={styles.eco}>{op.eco}</span>
                      )}
                      <div className={styles.nameBlock}>
                        <span className={styles.openingName}>{op.name}</span>
                        <span className={styles.gamesCount}>
                          {op.games_played} game{op.games_played !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </div>

                    {/* Center: proportional result bar */}
                    <div className={styles.rowCenter}>
                      <div className={styles.resultBar} title={`W ${op.result_1_0}  D ${op.result_draw}  L ${op.result_0_1}`}>
                        {winPct  > 0 && (
                          <div
                            className={styles.barWin}
                            style={{ width: `${winPct}%` }}
                          />
                        )}
                        {drawPct > 0 && (
                          <div
                            className={styles.barDraw}
                            style={{ width: `${drawPct}%` }}
                          />
                        )}
                        {lossPct > 0 && (
                          <div
                            className={styles.barLoss}
                            style={{ width: `${lossPct}%` }}
                          />
                        )}
                      </div>
                      <div className={styles.resultLabels}>
                        <span className={styles.labelWin}>W {op.result_1_0}</span>
                        <span className={styles.labelDraw}>D {op.result_draw}</span>
                        <span className={styles.labelLoss}>L {op.result_0_1}</span>
                      </div>
                    </div>

                    {/* Right: avg accuracy */}
                    <div className={styles.rowRight}>
                      <span className={`${styles.accuracyValue} ${accuracyColor(op.avg_user_accuracy)}`}>
                        {formatAccuracy(op.avg_user_accuracy)}
                      </span>
                      <span className={styles.accuracyLabel}>avg accuracy</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
