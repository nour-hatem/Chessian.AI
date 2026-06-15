"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Chess } from "chess.js";
import Navbar from "@/components/Layout/Navbar";
import ChessBoard from "@/components/Board/ChessBoard";
import EvalBar from "@/components/EvalBar/EvalBar";
import Clock from "@/components/Clock/Clock";
import MoveList, { MoveEntry } from "@/components/MoveList/MoveList";
import styles from "./play.module.css";

type Difficulty = "beginner" | "intermediate" | "advanced" | "maximum";
type TimeControl = "bullet1" | "blitz3" | "blitz5" | "rapid10" | "rapid15" | "classical30" | "unlimited";

const TIME_CONTROLS: Record<TimeControl, { time: number; increment: number; label: string }> = {
  bullet1:     { time: 60,   increment: 0,  label: "1+0 Bullet" },
  blitz3:      { time: 180,  increment: 0,  label: "3+0 Blitz" },
  blitz5:      { time: 300,  increment: 3,  label: "5+3 Blitz" },
  rapid10:     { time: 600,  increment: 0,  label: "10+0 Rapid" },
  rapid15:     { time: 900,  increment: 10, label: "15+10 Rapid" },
  classical30: { time: 1800, increment: 0,  label: "30+0 Classical" },
  unlimited:   { time: 0,    increment: 0,  label: "∞ Unlimited" },
};

const DIFFICULTIES: { key: Difficulty; label: string; desc: string; depth: number }[] = [
  { key: "beginner",     label: "Beginner",     desc: "~800 ELO",  depth: 2 },
  { key: "intermediate", label: "Intermediate", desc: "~1400 ELO", depth: 8 },
  { key: "advanced",     label: "Advanced",     desc: "~2000 ELO", depth: 14 },
  { key: "maximum",      label: "Maximum",      desc: "~3000+ ELO", depth: 22 },
];

export default function PlayPage() {
  const [gameStarted, setGameStarted] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty>("intermediate");
  const [timeControl, setTimeControl] = useState<TimeControl>("blitz5");
  const [playerColor, setPlayerColor] = useState<"white" | "black">("white");

  const [fen, setFen] = useState("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
  const [moves, setMoves] = useState<MoveEntry[]>([]);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0);
  const [evaluation, setEvaluation] = useState(0);
  const [gameOver, setGameOver] = useState(false);
  const [gameResult, setGameResult] = useState("");
  const [whiteActive, setWhiteActive] = useState(true);

  const chessRef = useRef(new Chess());
  const moveHistoryRef = useRef<string[]>([]);

  const addMoveToList = useCallback((san: string, moveNum: number, isWhite: boolean) => {
    setMoves((prev) => {
      const copy = [...prev];
      if (isWhite) {
        copy.push({ number: moveNum, white: { san } });
      } else {
        if (copy.length > 0) {
          const last = { ...copy[copy.length - 1] };
          last.black = { san };
          copy[copy.length - 1] = last;
        }
      }
      return copy;
    });
  }, []);

  const checkGameEnd = useCallback((chess: Chess) => {
    if (chess.isGameOver()) {
      setGameOver(true);
      if (chess.isCheckmate()) {
        const winner = chess.turn() === "w" ? "Black" : "White";
        setGameResult(`${winner} wins by checkmate!`);
      } else if (chess.isDraw()) {
        if (chess.isStalemate()) setGameResult("Draw by stalemate");
        else if (chess.isThreefoldRepetition()) setGameResult("Draw by repetition");
        else if (chess.isInsufficientMaterial()) setGameResult("Draw — insufficient material");
        else setGameResult("Draw by 50-move rule");
      }
      return true;
    }
    return false;
  }, []);

  // BUG-26 fix: helper to make an engine move
  const makeEngineMove = useCallback((chess: Chess) => {
    const engineMoves = chess.moves();
    if (engineMoves.length > 0) {
      const randomMove = engineMoves[Math.floor(Math.random() * engineMoves.length)];
      const engineMove = chess.move(randomMove);
      if (engineMove) {
        const isEngineWhite = engineMove.color === "w";
        // BUG-11 fix: use fullmove number from the position before the move
        const engMoveNum = chess.moveNumber() - (isEngineWhite ? 1 : 0);
        moveHistoryRef.current.push(engineMove.san);
        addMoveToList(engineMove.san, engMoveNum, isEngineWhite);
        setCurrentMoveIndex(moveHistoryRef.current.length);
        setFen(chess.fen());
        setWhiteActive(isEngineWhite ? false : true);
        checkGameEnd(chess);
      }
    }
  }, [addMoveToList, checkGameEnd]);

  const startGame = useCallback(() => {
    const chess = new Chess();
    chessRef.current = chess;
    moveHistoryRef.current = [];
    setFen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    setMoves([]);
    setCurrentMoveIndex(0);
    setEvaluation(0);
    setGameOver(false);
    setGameResult("");
    setWhiteActive(true);
    setGameStarted(true);

    // BUG-26 fix: if playing as black, engine (white) moves first
    if (playerColor === "black") {
      setTimeout(() => makeEngineMove(chess), 400);
    }
  }, [playerColor, makeEngineMove]);

  const handlePlayerMove = useCallback(
    (from: string, to: string, promotion?: string) => {
      const chess = chessRef.current;
      const move = chess.move({ from, to, promotion: promotion || undefined });

      if (move) {
        const isWhite = move.color === "w";
        // BUG-11 fix: correct move number — after push, moveNumber() advanced for white
        const moveNum = chess.moveNumber() - (isWhite ? 1 : 0);
        moveHistoryRef.current.push(move.san);
        addMoveToList(move.san, moveNum, isWhite);
        setCurrentMoveIndex(moveHistoryRef.current.length);
        setFen(chess.fen());
        setWhiteActive(!isWhite);

        if (!checkGameEnd(chess)) {
          // Engine responds
          setTimeout(() => makeEngineMove(chess), 300);
        }
      }
    },
    [addMoveToList, checkGameEnd, makeEngineMove]
  );

  const tc = TIME_CONTROLS[timeControl];

  // Setup screen
  if (!gameStarted) {
    return (
      <>
        <Navbar />
        <main className={styles.setupPage}>
          <div className={styles.setupCard}>
            <h1 className={styles.setupTitle}>
              <span>♔</span> New Game
            </h1>

            {/* Difficulty */}
            <div className={styles.setupSection}>
              <label className={styles.setupLabel}>Difficulty</label>
              <div className={styles.optionGrid}>
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d.key}
                    className={`${styles.optionBtn} ${difficulty === d.key ? styles.optionBtnActive : ""}`}
                    onClick={() => setDifficulty(d.key)}
                    id={`difficulty-${d.key}`}
                  >
                    <span className={styles.optionLabel}>{d.label}</span>
                    <span className={styles.optionMeta}>{d.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Time Control */}
            <div className={styles.setupSection}>
              <label className={styles.setupLabel}>Time Control</label>
              <div className={styles.optionGrid}>
                {Object.entries(TIME_CONTROLS).map(([key, val]) => (
                  <button
                    key={key}
                    className={`${styles.optionBtn} ${timeControl === key ? styles.optionBtnActive : ""}`}
                    onClick={() => setTimeControl(key as TimeControl)}
                    id={`time-${key}`}
                  >
                    <span className={styles.optionLabel}>{val.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Color */}
            <div className={styles.setupSection}>
              <label className={styles.setupLabel}>Play As</label>
              <div className={styles.colorPicker}>
                <button
                  className={`${styles.colorBtn} ${playerColor === "white" ? styles.colorBtnActive : ""}`}
                  onClick={() => setPlayerColor("white")}
                  id="color-white"
                >
                  <span className={styles.colorDot} style={{ background: "#f0f0f5" }} />
                  White
                </button>
                <button
                  className={`${styles.colorBtn} ${playerColor === "black" ? styles.colorBtnActive : ""}`}
                  onClick={() => setPlayerColor("black")}
                  id="color-black"
                >
                  <span className={styles.colorDot} style={{ background: "#2a2a2a", border: "1px solid #555" }} />
                  Black
                </button>
              </div>
            </div>

            <button className={styles.startBtn} onClick={startGame} id="btn-start-game">
              Start Game
            </button>
          </div>
        </main>
      </>
    );
  }

  // Game screen
  return (
    <>
      <Navbar />
      <main className={styles.gamePage}>
        <div className={styles.gameLayout}>
          {/* Eval Bar */}
          <EvalBar evaluation={evaluation} orientation={playerColor} />

          {/* Board + Clocks */}
          <div className={styles.boardColumn}>
            {tc.time > 0 && (
              <Clock
                initialTime={tc.time}
                increment={tc.increment}
                active={!gameOver && (playerColor === "white" ? !whiteActive : whiteActive)}
                color={playerColor === "white" ? "black" : "white"}
              />
            )}

            <ChessBoard
              fen={fen}
              orientation={playerColor}
              onMove={handlePlayerMove}
              interactive={!gameOver}
            />

            {tc.time > 0 && (
              <Clock
                initialTime={tc.time}
                increment={tc.increment}
                active={!gameOver && (playerColor === "white" ? whiteActive : !whiteActive)}
                color={playerColor}
              />
            )}
          </div>

          {/* Sidebar */}
          <div className={styles.sidebar}>
            <MoveList
              moves={moves}
              currentMoveIndex={currentMoveIndex}
              onMoveClick={setCurrentMoveIndex}
            />

            {gameOver && (
              <div className={styles.gameOverBanner}>
                <p className={styles.gameOverText}>{gameResult}</p>
                <div className={styles.gameOverActions}>
                  <button className="btn-primary" onClick={startGame} id="btn-rematch">
                    New Game
                  </button>
                  <button className="btn-secondary" onClick={() => setGameStarted(false)} id="btn-setup">
                    Setup
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
