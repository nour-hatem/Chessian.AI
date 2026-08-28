"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import Navbar from "@/components/Layout/Navbar";
import styles from "./openings.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types (mirror crud.get_opening_repertoire) ─── */
interface Opening {
  eco: string;
  name: string;
  games_played: number;
  wins: number;
  losses: number;
  draws: number;
  games_as_white: number;
  games_as_black: number;
  score_pct: number | null;
  avg_user_accuracy: number | null;
  avg_opponent_accuracy: number | null;
}

interface RepertoireResponse {
  openings: Opening[];
  total: number;
  identity_resolved: boolean;
}

type SortKey = "played" | "best" | "worst";

/* ─── Helpers ─── */
function accuracyClass(val: number | null): string {
  if (val === null) return styles.accNull;
  if (val >= 80) return styles.accExcellent;
  if (val >= 60) return styles.accGood;
  return styles.accWeak;
}

function formatPct(val: number | null, suffix = "%"): string {
  if (val === null) return "—";
  return `${val.toFixed(1)}${suffix}`;
}

/* ─── Component ─── */
export default function OpeningsPage() {
  const [openings, setOpenings] = useState<Opening[]>([]);
  const [identityResolved, setIdentityResolved] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("played");

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
        setOpenings(data.openings ?? []);
        setIdentityResolved(data.identity_resolved !== false);
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
    const rows = [...openings];

    if (sortKey === "played") {
      rows.sort((a, b) => b.games_played - a.games_played);
      return rows;
    }

    // Accuracy sorts: rows without accuracy always sink to the bottom.
    rows.sort((a, b) => {
      const av = a.avg_user_accuracy;
      const bv = b.avg_user_accuracy;
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortKey === "best" ? bv - av : av - bv;
    });
    return rows;
  }, [openings, sortKey]);

  const SORTS: { key: SortKey; label: string }[] = [
    { key: "played", label: "Most played" },
    { key: "best", label: "Best accuracy" },
    { key: "worst", label: "Worst accuracy" },
  ];

  return (
    <>
      <Navbar />
      <main className={styles.openingsPage}>
        <div className={styles.container}>
          <h1 className={styles.pageTitle}>
            <span className="gradient-text">Opening</span> Repertoire
          </h1>
          <p className={styles.pageSubtitle}>
            Openings you&apos;ve played in 3 or more analyzed games. Results and
            accuracy are shown from your side of the board.
          </p>

          {!loading && !error && !identityResolved && openings.length > 0 && (
            <div className={styles.warningBanner} id="identity-warning">
              ⚠ Could not work out which side you played, so results and accuracy
              are unavailable. Re-run an import to record your platform username.
            </div>
          )}

          {!loading && !error && openings.length > 0 && (
            <div className={styles.controls}>
              <span className={styles.totalLabel}>
                {openings.length} opening{openings.length !== 1 ? "s" : ""}
              </span>
              <div className={styles.sortGroup}>
                <span className={styles.sortLabel}>Sort by</span>
                {SORTS.map((s) => (
                  <button
                    key={s.key}
                    id={`sort-${s.key}`}
                    className={`${styles.sortBtn} ${sortKey === s.key ? styles.sortBtnActive : ""}`}
                    onClick={() => setSortKey(s.key)}
                    aria-pressed={sortKey === s.key}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {loading && <div className={styles.loadingState}>Loading openings…</div>}

          {!loading && error && <div className={styles.errorState}>{error}</div>}

          {!loading && !error && openings.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>♞</div>
              <p>No openings yet.</p>
              <p className={styles.emptyHint}>
                Import and analyze at least 3 games in the same opening to see
                repertoire stats here.
              </p>
              <Link href="/library" className={styles.emptyCta}>
                → Go to Game Library
              </Link>
            </div>
          )}

          {!loading && !error && sorted.length > 0 && (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col" className={styles.thEco}>ECO</th>
                    <th scope="col">Opening</th>
                    <th scope="col" className={styles.thNum}>Games</th>
                    <th scope="col" className={styles.thResults}>Results</th>
                    <th scope="col" className={styles.thNum}>Score</th>
                    <th scope="col" className={styles.thNum}>Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((op, i) => {
                    const total = op.games_played || 1;
                    const winPct = (op.wins / total) * 100;
                    const drawPct = (op.draws / total) * 100;
                    const lossPct = (op.losses / total) * 100;

                    return (
                      <tr key={`${op.eco}-${op.name}`} id={`opening-row-${i}`}>
                        <td className={styles.tdEco}>
                          {op.eco ? (
                            <span className={styles.eco}>{op.eco}</span>
                          ) : (
                            <span className={styles.muted}>—</span>
                          )}
                        </td>

                        <td className={styles.tdName}>
                          {op.eco ? (
                            <Link
                              href={`/library?opening=${encodeURIComponent(op.eco)}`}
                              className={styles.nameLink}
                              title="Show these games in the library"
                            >
                              {op.name}
                            </Link>
                          ) : (
                            <span>{op.name}</span>
                          )}
                          <span className={styles.colorSplit}>
                            {op.games_as_white}W / {op.games_as_black}B
                          </span>
                        </td>

                        <td className={styles.tdNum}>{op.games_played}</td>

                        <td className={styles.tdResults}>
                          <div
                            className={styles.resultBar}
                            title={`${op.wins}W  ${op.draws}D  ${op.losses}L`}
                          >
                            {winPct > 0 && (
                              <div className={styles.barWin} style={{ width: `${winPct}%` }} />
                            )}
                            {drawPct > 0 && (
                              <div className={styles.barDraw} style={{ width: `${drawPct}%` }} />
                            )}
                            {lossPct > 0 && (
                              <div className={styles.barLoss} style={{ width: `${lossPct}%` }} />
                            )}
                          </div>
                          <div className={styles.resultLabels}>
                            <span className={styles.labelWin}>{op.wins}W</span>
                            <span className={styles.labelDraw}>{op.draws}D</span>
                            <span className={styles.labelLoss}>{op.losses}L</span>
                          </div>
                        </td>

                        <td className={styles.tdNum}>
                          <span className={styles.score}>
                            {formatPct(op.score_pct)}
                          </span>
                        </td>

                        <td className={styles.tdNum}>
                          <span
                            className={`${styles.accuracy} ${accuracyClass(op.avg_user_accuracy)}`}
                          >
                            {formatPct(op.avg_user_accuracy)}
                          </span>
                          {op.avg_opponent_accuracy !== null && (
                            <span className={styles.oppAccuracy}>
                              vs {formatPct(op.avg_opponent_accuracy)}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
