"use client";

import { useEffect, useRef } from "react";
import styles from "./MoveList.module.css";

export interface MoveEntry {
  number: number;
  white: {
    san: string;
    classification?: string;
    /**
     * Position index this move leads to, matching the consumer's FEN history.
     * Optional: when omitted the list falls back to assuming a dense,
     * white-first ply sequence (`row * 2 + 1`).
     */
    ply?: number;
  };
  black?: {
    san: string;
    classification?: string;
    ply?: number;
  };
}

interface MoveListProps {
  moves: MoveEntry[];
  currentMoveIndex: number;
  onMoveClick: (index: number) => void;
}

function getClassColor(classification?: string): string {
  switch (classification) {
    case "brilliant": return "var(--move-brilliant)";
    case "great": return "var(--move-great)";
    case "best": return "var(--move-best)";
    case "good": return "var(--move-good)";
    case "book": return "var(--move-book)";
    case "inaccuracy": return "var(--move-inaccuracy)";
    case "mistake": return "var(--move-mistake)";
    case "blunder": return "var(--move-blunder)";
    default: return "inherit";
  }
}

function getClassSymbol(classification?: string): string {
  switch (classification) {
    case "brilliant": return "!!";
    case "great": return "!";
    case "best": return "✓";
    case "inaccuracy": return "?!";
    case "mistake": return "?";
    case "blunder": return "??";
    default: return "";
  }
}

export default function MoveList({
  moves,
  currentMoveIndex,
  onMoveClick,
}: MoveListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  /* Keep the active move in view as the user steps through the game. */
  useEffect(() => {
    const active = activeRef.current;
    const container = scrollRef.current;
    if (!active || !container) return;

    const activeTop = active.offsetTop;
    const activeBottom = activeTop + active.offsetHeight;
    const viewTop = container.scrollTop;
    const viewBottom = viewTop + container.clientHeight;

    if (activeTop < viewTop || activeBottom > viewBottom) {
      container.scrollTop = activeTop - container.clientHeight / 2;
    }
  }, [currentMoveIndex]);

  return (
    <div className={styles.moveList} id="move-list">
      <div className={styles.header}>
        <span className={styles.headerTitle}>Moves</span>
      </div>
      <div className={styles.movesScroll} ref={scrollRef}>
        {moves.length === 0 ? (
          <div className={styles.emptyMoves}>No moves to show</div>
        ) : (
          moves.map((move, i) => {
            const whiteIndex = move.white.ply ?? i * 2 + 1;
            const blackIndex = move.black?.ply ?? i * 2 + 2;
            const whiteActive = currentMoveIndex === whiteIndex;
            const blackActive = currentMoveIndex === blackIndex;

            return (
              <div key={`${move.number}-${i}`} className={styles.moveRow}>
                <span className={styles.moveNumber}>{move.number}.</span>
                <button
                  ref={whiteActive ? activeRef : undefined}
                  className={`${styles.moveBtn} ${whiteActive ? styles.moveBtnActive : ""}`}
                  style={{ color: getClassColor(move.white.classification) }}
                  onClick={() => onMoveClick(whiteIndex)}
                >
                  {move.white.san}
                  <span className={styles.classSymbol}>
                    {getClassSymbol(move.white.classification)}
                  </span>
                </button>
                {move.black && (
                  <button
                    ref={blackActive ? activeRef : undefined}
                    className={`${styles.moveBtn} ${blackActive ? styles.moveBtnActive : ""}`}
                    style={{ color: getClassColor(move.black.classification) }}
                    onClick={() => onMoveClick(blackIndex)}
                  >
                    {move.black.san}
                    <span className={styles.classSymbol}>
                      {getClassSymbol(move.black.classification)}
                    </span>
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
