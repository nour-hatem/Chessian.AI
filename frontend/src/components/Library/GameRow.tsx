"use client";

import Link from "next/link";
import { ResultBadge, StatusPill } from "./Badges";
import type { AnalysisStatus, UserResult } from "./Badges";
import styles from "./GameRow.module.css";

export interface LibraryGame {
  id: string;
  white_username: string | null;
  black_username: string | null;
  result: string | null;
  opening_name: string | null;
  opening_eco: string | null;
  played_at: string | null;
  source: string;
  time_control: string | null;
  has_analysis: boolean;
  analysis_status: AnalysisStatus;
  user_color: "white" | "black" | null;
  user_result: UserResult;
  imported_at: string;
}

interface GameRowProps {
  game: LibraryGame;
  /** True while this client is polling an analysis it queued for this game. */
  busy: boolean;
  onAnalyze: (gameId: string) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  lichess: "♞ Lichess",
  chesscom: "♟ Chess.com",
  pgn_upload: "📄 PGN",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Time control arrives in three different vocabularies depending on the import
 * source: a speed word from the platforms ("blitz"), or a raw "<base>+<inc>"
 * header in seconds from PGN uploads. Normalise both to a readable label.
 */
function formatTimeControl(tc: string | null): string {
  if (!tc || tc === "unknown") return "—";

  const numeric = /^(\d+)(?:\+(\d+))?$/.exec(tc);
  if (numeric) {
    const base = Number(numeric[1]);
    const inc = Number(numeric[2] ?? 0);
    const minutes = base % 60 === 0 ? `${base / 60}` : (base / 60).toFixed(1);
    return inc > 0 ? `${minutes}+${inc}` : `${minutes} min`;
  }

  return tc.charAt(0).toUpperCase() + tc.slice(1);
}

export default function GameRow({ game, busy, onAnalyze }: GameRowProps) {
  const status = game.analysis_status;
  const isRunning = busy || status === "processing" || status === "pending";

  // Prefer naming the actual opponent; fall back to the raw pairing when the
  // user's side is unknown.
  const opponent =
    game.user_color === "white"
      ? game.black_username
      : game.user_color === "black"
        ? game.white_username
        : null;

  const label = opponent
    ? `Game vs ${opponent}`
    : `${game.white_username || "White"} vs ${game.black_username || "Black"}`;

  return (
    <div className={styles.row} id={`game-${game.id}`}>
      <Link
        href={`/analysis/${game.id}`}
        className={styles.rowLink}
        aria-label={`${label} — open analysis`}
        /* Long, paginated list: skip viewport prefetching of every row. */
        prefetch={false}
      >
        Open analysis
      </Link>

      <ResultBadge userResult={game.user_result} rawResult={game.result} />

      <div className={styles.main}>
        <div className={styles.players}>
          {game.user_color && (
            <span className={styles.colorChip}>
              <span
                className={`${styles.chipSwatch} ${
                  game.user_color === "white" ? styles.chipWhite : styles.chipBlack
                }`}
              />
              as {game.user_color}
            </span>
          )}
          {opponent ? (
            <>
              <span className={styles.vs}>vs</span>
              <span className={styles.opponent}>{opponent}</span>
            </>
          ) : (
            <span className={styles.opponent}>
              {game.white_username || "White"}
              <span className={styles.vs}> vs </span>
              {game.black_username || "Black"}
            </span>
          )}
        </div>

        <div className={styles.meta}>
          {game.opening_eco && <span className={styles.eco}>{game.opening_eco}</span>}
          <span className={styles.opening}>
            {game.opening_name || "Unknown opening"}
          </span>
          <span className={styles.dot}>·</span>
          <span>{formatTimeControl(game.time_control)}</span>
          <span className={styles.dot}>·</span>
          <span>{formatDate(game.played_at)}</span>
        </div>
      </div>

      <div className={styles.side}>
        <span className={styles.sourceBadge}>
          {SOURCE_LABELS[game.source] ?? game.source}
        </span>

        <StatusPill status={status} busy={busy} />

        {status !== "complete" && (
          <button
            className={`${styles.actionBtn} ${
              status === "failed" ? styles.retryBtn : ""
            }`}
            onClick={() => onAnalyze(game.id)}
            disabled={isRunning}
            id={`analyze-${game.id}`}
          >
            {isRunning
              ? "Analyzing…"
              : status === "failed"
                ? "Retry"
                : "Analyze"}
          </button>
        )}
      </div>
    </div>
  );
}
