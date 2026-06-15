"use client";

import styles from "./EvalBar.module.css";

interface EvalBarProps {
  evaluation: number; // centipawns, positive = white advantage
  mate?: number | null; // mate-in-N, positive = white mates
  orientation?: "white" | "black";
}

export default function EvalBar({
  evaluation = 0,
  mate = null,
  orientation = "white",
}: EvalBarProps) {
  // Convert evaluation to percentage (0-100 where 50 is equal)
  const getWhitePercentage = (): number => {
    if (mate !== null && mate !== undefined) {
      return mate > 0 ? 100 : 0;
    }
    // Sigmoid-like scaling: eval of ±500cp maps to ~90%
    const scaled = 50 + 50 * (2 / (1 + Math.exp(-0.004 * evaluation)) - 1);
    return Math.max(2, Math.min(98, scaled));
  };

  const getDisplayText = (): string => {
    if (mate !== null && mate !== undefined) {
      return `M${Math.abs(mate)}`;
    }
    const evalInPawns = Math.abs(evaluation / 100);
    if (evalInPawns < 0.1) return "0.0";
    const sign = evaluation > 0 ? "+" : "-";
    return `${sign}${evalInPawns.toFixed(1)}`;
  };

  const isWhiteAdvantage = mate !== null ? (mate ?? 0) > 0 : evaluation >= 0;
  const whitePercent = getWhitePercentage();
  const flipped = orientation === "black";

  return (
    <div
      className={`${styles.evalBar} ${flipped ? styles.flipped : ""}`}
      id="eval-bar"
    >
      <div
        className={styles.whiteSection}
        style={{ height: `${whitePercent}%` }}
      />
      <div className={styles.evalLabel}>
        <span
          className={`${styles.evalText} ${isWhiteAdvantage ? styles.evalWhite : styles.evalBlack}`}
        >
          {getDisplayText()}
        </span>
      </div>
    </div>
  );
}
