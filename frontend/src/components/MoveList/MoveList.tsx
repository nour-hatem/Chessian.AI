"use client";

import styles from "./MoveList.module.css";

export interface MoveEntry {
  number: number;
  white: {
    san: string;
    classification?: string;
  };
  black?: {
    san: string;
    classification?: string;
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
  return (
    <div className={styles.moveList} id="move-list">
      <div className={styles.header}>
        <span className={styles.headerTitle}>Moves</span>
      </div>
      <div className={styles.movesScroll}>
        {moves.map((move, i) => {
          const whiteIndex = i * 2 + 1;
          const blackIndex = i * 2 + 2;

          return (
            <div key={move.number} className={styles.moveRow}>
              <span className={styles.moveNumber}>{move.number}.</span>
              <button
                className={`${styles.moveBtn} ${currentMoveIndex === whiteIndex ? styles.moveBtnActive : ""}`}
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
                  className={`${styles.moveBtn} ${currentMoveIndex === blackIndex ? styles.moveBtnActive : ""}`}
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
        })}
      </div>
    </div>
  );
}
