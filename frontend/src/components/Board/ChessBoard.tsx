"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { Chessground } from "chessground";
import { Chess, Square } from "chess.js";
import type { Api } from "chessground/api";
import type { Key } from "chessground/types";
import styles from "./ChessBoard.module.css";

interface ChessBoardProps {
  fen?: string;
  orientation?: "white" | "black";
  onMove?: (from: string, to: string, promotion?: string) => void;
  interactive?: boolean;
  lastMove?: [string, string];
  viewOnly?: boolean;
  width?: number;
  highlights?: Map<string, string>;
}

export default function ChessBoard({
  fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  orientation = "white",
  onMove,
  interactive = true,
  lastMove,
  viewOnly = false,
  highlights,
}: ChessBoardProps) {
  const boardRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef<Api | null>(null);
  const chessRef = useRef(new Chess(fen));
  const [boardFlipped, setBoardFlipped] = useState(orientation === "black");

  const getTurnColor = useCallback((): "white" | "black" => {
    return chessRef.current.turn() === "w" ? "white" : "black";
  }, []);

  const getLegalMoves = useCallback((): Map<Key, Key[]> => {
    const dests = new Map<Key, Key[]>();
    const moves = chessRef.current.moves({ verbose: true });
    for (const move of moves) {
      const from = move.from as Key;
      if (!dests.has(from)) {
        dests.set(from, []);
      }
      dests.get(from)!.push(move.to as Key);
    }
    return dests;
  }, []);

  const handleMove = useCallback(
    (orig: Key, dest: Key) => {
      const chess = chessRef.current;

      // Check if promotion
      const piece = chess.get(orig as Square);
      const isPromotion =
        piece?.type === "p" &&
        ((piece.color === "w" && dest[1] === "8") ||
          (piece.color === "b" && dest[1] === "1"));

      const move = chess.move({
        from: orig as string,
        to: dest as string,
        promotion: isPromotion ? "q" : undefined,
      });

      if (move && apiRef.current) {
        apiRef.current.set({
          fen: chess.fen(),
          turnColor: getTurnColor(),
          movable: {
            color: getTurnColor(),
            dests: getLegalMoves(),
          },
          lastMove: [orig, dest],
        });

        onMove?.(orig, dest, isPromotion ? "q" : undefined);
      }
    },
    [onMove, getTurnColor, getLegalMoves]
  );

  // Initialize chessground
  useEffect(() => {
    if (!boardRef.current) return;

    const api = Chessground(boardRef.current, {
      fen,
      orientation: orientation,
      turnColor: getTurnColor(),
      viewOnly,
      movable: {
        free: false,
        color: interactive ? getTurnColor() : undefined,
        dests: interactive ? getLegalMoves() : new Map(),
        showDests: true,
      },
      lastMove: lastMove as [Key, Key] | undefined,
      highlight: {
        lastMove: true,
        check: true,
      },
      animation: {
        enabled: true,
        duration: 200,
      },
      premovable: {
        enabled: interactive,
      },
      draggable: {
        enabled: interactive,
        showGhost: true,
      },
      drawable: {
        enabled: true,
        defaultSnapToValidMove: true,
      },
      events: {
        move: handleMove,
      },
    });

    apiRef.current = api;

    return () => {
      api.destroy();
    };
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update FEN when prop changes
  useEffect(() => {
    if (!apiRef.current) return;
    chessRef.current = new Chess(fen);
    apiRef.current.set({
      fen,
      turnColor: getTurnColor(),
      movable: {
        color: interactive ? getTurnColor() : undefined,
        dests: interactive ? getLegalMoves() : new Map(),
      },
      lastMove: lastMove as [Key, Key] | undefined,
    });
  }, [fen, interactive, lastMove, getTurnColor, getLegalMoves]);

  // H5 fix: Update event handler when handleMove changes to prevent stale closures
  useEffect(() => {
    if (apiRef.current) {
      apiRef.current.set({
        events: { move: handleMove },
      });
    }
  }, [handleMove]);

  // M6 fix: Sync orientation when prop changes
  useEffect(() => {
    setBoardFlipped(orientation === "black");
  }, [orientation]);

  // Update orientation
  useEffect(() => {
    if (apiRef.current) {
      apiRef.current.set({
        orientation: boardFlipped ? "black" : "white",
      });
    }
  }, [boardFlipped]);

  const flipBoard = useCallback(() => {
    setBoardFlipped((prev) => !prev);
  }, []);



  return (
    <div className={styles.boardContainer} id="chess-board-container">
      <div className={styles.boardWrapper}>
        <div ref={boardRef} className={styles.board} id="chess-board" />
      </div>
      {interactive && (
        <div className={styles.boardControls}>
          <button
            className="btn-icon"
            onClick={flipBoard}
            title="Flip board"
            id="btn-flip-board"
          >
            🔄
          </button>
        </div>
      )}
    </div>
  );
}

export { ChessBoard };
