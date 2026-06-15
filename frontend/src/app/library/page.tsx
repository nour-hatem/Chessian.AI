"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Layout/Navbar";
import styles from "./library.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ImportedGame {
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
  imported_at: string;
}

export default function LibraryPage() {
  const [username, setUsername] = useState("");
  const [platform, setPlatform] = useState<"lichess" | "chesscom">("lichess");
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState("");
  const [games, setGames] = useState<ImportedGame[]>([]);
  const [totalGames, setTotalGames] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [analyzing, setAnalyzing] = useState<Set<string>>(new Set());
  const pollingIntervalsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const router = useRouter();

  const fetchGames = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: "20",
      });
      if (searchQuery) params.set("search", searchQuery);

      const resp = await fetch(`${API_BASE}/api/games?${params}`);
      if (resp.ok) {
        const data = await resp.json();
        setGames(data.games);
        setTotalGames(data.total);
      }
    } catch (err) {
      console.error("Failed to fetch games:", err);
    } finally {
      setLoading(false);
    }
  }, [page, searchQuery]);

  // H8 fix: single debounced effect for search — no double fetch
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  const handleImport = async () => {
    if (!username.trim()) return;
    setImporting(true);
    setImportMessage("");

    try {
      const resp = await fetch(`${API_BASE}/api/import/${platform}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), max_games: 100 }),
      });
      const data = await resp.json();
      setImportMessage(data.message);

      if (data.status === "complete" && data.games_imported > 0) {
        // Refresh game list
        await fetchGames();
      }
    } catch (err) {
      setImportMessage("Import failed — is the backend running?");
    } finally {
      setImporting(false);
    }
  };

  const handlePgnUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch(`${API_BASE}/api/import/pgn`, {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      setImportMessage(data.message);

      if (data.status === "complete" && data.games_imported > 0) {
        await fetchGames();
      }
    } catch (err) {
      setImportMessage("Upload failed — is the backend running?");
    } finally {
      setImporting(false);
    }
  };

  const handleAnalyze = async (gameId: string) => {
    setAnalyzing((prev) => new Set(prev).add(gameId));

    try {
      const resp = await fetch(`${API_BASE}/api/analysis/${gameId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await resp.json();

      if (data.status === "queued") {
        // Poll for completion
        pollAnalysis(gameId);
      }
    } catch (err) {
      console.error("Failed to trigger analysis:", err);
      setAnalyzing((prev) => {
        const next = new Set(prev);
        next.delete(gameId);
        return next;
      });
    }
  };

  const pollAnalysis = (gameId: string) => {
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/analysis/${gameId}`);
        if (resp.ok) {
          const data = await resp.json();
          if (data.status === "complete" || data.status === "failed") {
            clearInterval(interval);
            pollingIntervalsRef.current.delete(gameId);
            setAnalyzing((prev) => {
              const next = new Set(prev);
              next.delete(gameId);
              return next;
            });
            await fetchGames();
          }
        }
      } catch {
        clearInterval(interval);
        pollingIntervalsRef.current.delete(gameId);
      }
    }, 3000);
    // H3 fix: track interval for cleanup on unmount
    pollingIntervalsRef.current.set(gameId, interval);
  };

  // H3 fix: clean up all polling intervals on unmount
  useEffect(() => {
    return () => {
      pollingIntervalsRef.current.forEach((interval) => clearInterval(interval));
      pollingIntervalsRef.current.clear();
    };
  }, []);

  const getSourceBadge = (source: string) => {
    switch (source) {
      case "lichess": return "♞ Lichess";
      case "chesscom": return "♟ Chess.com";
      case "pgn_upload": return "📄 PGN";
      default: return source;
    }
  };

  const getResultClass = (result: string | null) => {
    if (result === "1-0") return styles.resultWin;
    if (result === "0-1") return styles.resultLoss;
    return styles.resultDraw;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const totalPages = Math.ceil(totalGames / 20);

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
                  onKeyDown={(e) => e.key === "Enter" && handleImport()}
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
                  <input
                    type="file"
                    accept=".pgn"
                    hidden
                    onChange={handlePgnUpload}
                  />
                </label>
              </div>
              {importMessage && (
                <p className={styles.importMessage}>{importMessage}</p>
              )}
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
              {totalGames} game{totalGames !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Games List */}
          <div className={styles.gamesList}>
            {loading ? (
              <div className={styles.loadingState}>Loading games...</div>
            ) : games.length === 0 ? (
              <div className={styles.emptyState}>
                <p>No games yet. Import from Lichess, Chess.com, or upload a PGN file.</p>
              </div>
            ) : (
              games.map((game) => (
                <div key={game.id} className={styles.gameCard} id={`game-${game.id}`}>
                  <div className={styles.gameMain}>
                    <div className={styles.gamePlayers}>
                      <span className={styles.playerWhite}>
                        ⬜ {game.white_username || "Unknown"}
                      </span>
                      <span className={styles.vs}>vs</span>
                      <span className={styles.playerBlack}>
                        ⬛ {game.black_username || "Unknown"}
                      </span>
                    </div>
                    <span className={`${styles.gameResult} ${getResultClass(game.result)}`}>
                      {game.result || "?"}
                    </span>
                  </div>
                  <div className={styles.gameMeta}>
                    <span className={styles.gameOpening}>
                      {game.opening_name || game.opening_eco || "—"}
                    </span>
                    <span className={styles.gameDot}>·</span>
                    <span className={styles.gameTime}>{game.time_control || "—"}</span>
                    <span className={styles.gameDot}>·</span>
                    <span className={styles.gameDate}>
                      {formatDate(game.played_at)}
                    </span>
                    <span className={styles.sourceBadge}>
                      {getSourceBadge(game.source)}
                    </span>
                  </div>
                  <div className={styles.gameActions}>
                    {game.has_analysis ? (
                      <button
                        className="btn-secondary"
                        id={`view-${game.id}`}
                        onClick={() => router.push(`/analysis/${game.id}`)}
                      >
                        📊 View Analysis
                      </button>
                    ) : analyzing.has(game.id) ? (
                      <button className="btn-secondary" disabled>
                        ⏳ Analyzing...
                      </button>
                    ) : (
                      <button
                        className="btn-secondary"
                        onClick={() => handleAnalyze(game.id)}
                        id={`analyze-${game.id}`}
                      >
                        🔍 Analyze
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className="btn-secondary"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                ← Prev
              </button>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages}
              </span>
              <button
                className="btn-secondary"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
