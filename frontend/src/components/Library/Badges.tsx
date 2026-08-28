"use client";

import styles from "./Badges.module.css";

/* ─── Result badge ───────────────────────────────────────────────────────── */

export type UserResult = "win" | "loss" | "draw" | null;

interface ResultBadgeProps {
  /** Result from the library owner's perspective, as returned by the API. */
  userResult: UserResult;
  /** Raw PGN result ("1-0" / "0-1" / "1/2-1/2"), used as a fallback. */
  rawResult?: string | null;
}

/**
 * Shows W / L / D from the user's point of view.
 *
 * When the backend could not determine which side the user played,
 * `userResult` is null and we fall back to the raw score so the row still
 * says something truthful rather than inventing a win or a loss.
 */
export function ResultBadge({ userResult, rawResult }: ResultBadgeProps) {
  if (userResult === "win") {
    return <span className={`${styles.result} ${styles.win}`} title="Win">W</span>;
  }
  if (userResult === "loss") {
    return <span className={`${styles.result} ${styles.loss}`} title="Loss">L</span>;
  }
  if (userResult === "draw") {
    return <span className={`${styles.result} ${styles.draw}`} title="Draw">D</span>;
  }

  return (
    <span
      className={`${styles.result} ${styles.unknown}`}
      title="Which side you played could not be determined"
    >
      {rawResult && rawResult !== "*" ? rawResult : "—"}
    </span>
  );
}

/* ─── Analysis status pill ───────────────────────────────────────────────── */

export type AnalysisStatus =
  | "complete"
  | "processing"
  | "pending"
  | "failed"
  | null;

interface StatusPillProps {
  status: AnalysisStatus;
  /** True while this client is actively polling an analysis it just queued. */
  busy?: boolean;
}

export function StatusPill({ status, busy = false }: StatusPillProps) {
  if (busy || status === "processing" || status === "pending") {
    return (
      <span className={`${styles.status} ${styles.statusRunning}`}>
        <span className={styles.dot} />
        Analyzing
      </span>
    );
  }
  if (status === "complete") {
    return (
      <span className={`${styles.status} ${styles.statusComplete}`}>
        <span className={styles.dot} />
        Analyzed
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className={`${styles.status} ${styles.statusFailed}`}>
        <span className={styles.dot} />
        Failed
      </span>
    );
  }
  return (
    <span className={`${styles.status} ${styles.statusNone}`}>
      <span className={styles.dot} />
      Not analyzed
    </span>
  );
}
