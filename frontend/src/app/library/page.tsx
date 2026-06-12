"use client";

import { useState } from "react";
import Navbar from "@/components/Layout/Navbar";
import styles from "./library.module.css";

interface ImportedGame {
  id: string;
  white: string;
  black: string;
  result: string;
  opening: string;
  date: string;
  source: "lichess" | "chesscom" | "pgn";
  timeControl: string;
}

// Demo data for UI showcase
const DEMO_GAMES: ImportedGame[] = [
  {
    id: "1", white: "You", black: "opponent_42", result: "1-0",
    opening: "Sicilian Defense: Najdorf", date: "2026-06-12",
    source: "lichess", timeControl: "5+3",
  },
  {
    id: "2", white: "chess_master", black: "You", result: "0-1",
    opening: "Queen's Gambit Declined", date: "2026-06-11",
    source: "chesscom", timeControl: "10+0",
  },
  {
    id: "3", white: "You", black: "rapid_player", result: "1/2-1/2",
    opening: "Ruy Lopez: Berlin Defense", date: "2026-06-10",
    source: "lichess", timeControl: "15+10",
  },
];

export default function LibraryPage() {
  const [username, setUsername] = useState("");
  const [platform, setPlatform] = useState<"lichess" | "chesscom">("lichess");
  const [importing, setImporting] = useState(false);
  const [games, setGames] = useState<ImportedGame[]>(DEMO_GAMES);
  const [searchQuery, setSearchQuery] = useState("");

  const handleImport = async () => {
    if (!username.trim()) return;
    setImporting(true);
    // TODO: connect to backend API
    setTimeout(() => {
      setImporting(false);
    }, 2000);
  };

  const filteredGames = games.filter(
    (g) =>
      g.opening.toLowerCase().includes(searchQuery.toLowerCase()) ||
      g.white.toLowerCase().includes(searchQuery.toLowerCase()) ||
      g.black.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getSourceBadge = (source: string) => {
    switch (source) {
      case "lichess": return "♞ Lichess";
      case "chesscom": return "♟ Chess.com";
      case "pgn": return "📄 PGN";
      default: return source;
    }
  };

  const getResultClass = (result: string) => {
    if (result === "1-0") return styles.resultWin;
    if (result === "0-1") return styles.resultLoss;
    return styles.resultDraw;
  };

  return (
    <>
      <Navbar />
      <main className={styles.libraryPage}>
        <div className={styles.container}>
          <h1 className={styles.pageTitle}>Game Library</h1>

          {/* Import Section */}
          <div className={styles.importCard} id="import-section">
            <h2 className={styles.importTitle}>Import Games</h2>
            <div className={styles.importForm}>
              <div className={styles.platformToggle}>
                <button
                  className={`${styles.platformBtn} ${platform === "lichess" ? styles.platformBtnActive : ""}`}
                  onClick={() => setPlatform("lichess")}
                  id="platform-lichess"
                >
                  ♞ Lichess
                </button>
                <button
                  className={`${styles.platformBtn} ${platform === "chesscom" ? styles.platformBtnActive : ""}`}
                  onClick={() => setPlatform("chesscom")}
                  id="platform-chesscom"
                >
                  ♟ Chess.com
                </button>
              </div>
              <div className={styles.inputRow}>
                <input
                  type="text"
                  placeholder={`Enter your ${platform === "lichess" ? "Lichess" : "Chess.com"} username`}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={styles.input}
                  id="input-username"
                />
                <button
                  className="btn-primary"
                  onClick={handleImport}
                  disabled={importing}
                  id="btn-import"
                >
                  {importing ? "Importing..." : "Import"}
                </button>
              </div>
              <div className={styles.uploadRow}>
                <span className={styles.orDivider}>or</span>
                <label className={styles.uploadLabel} id="btn-upload-pgn">
                  📄 Upload PGN File
                  <input type="file" accept=".pgn" hidden />
                </label>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className={styles.searchBar}>
            <input
              type="text"
              placeholder="Search games by opening, player..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
              id="input-search"
            />
            <span className={styles.gameCount}>
              {filteredGames.length} game{filteredGames.length !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Games List */}
          <div className={styles.gamesList}>
            {filteredGames.map((game) => (
              <div key={game.id} className={styles.gameCard} id={`game-${game.id}`}>
                <div className={styles.gameMain}>
                  <div className={styles.gamePlayers}>
                    <span className={styles.playerWhite}>⬜ {game.white}</span>
                    <span className={styles.vs}>vs</span>
                    <span className={styles.playerBlack}>⬛ {game.black}</span>
                  </div>
                  <span className={`${styles.gameResult} ${getResultClass(game.result)}`}>
                    {game.result}
                  </span>
                </div>
                <div className={styles.gameMeta}>
                  <span className={styles.gameOpening}>{game.opening}</span>
                  <span className={styles.gameDot}>·</span>
                  <span className={styles.gameTime}>{game.timeControl}</span>
                  <span className={styles.gameDot}>·</span>
                  <span className={styles.gameDate}>{game.date}</span>
                  <span className={styles.sourceBadge}>{getSourceBadge(game.source)}</span>
                </div>
                <div className={styles.gameActions}>
                  <button className="btn-secondary" id={`analyze-${game.id}`}>
                    🔍 Analyze
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
