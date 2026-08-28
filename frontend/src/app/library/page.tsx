"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Layout/Navbar";
import ImportPanel from "@/components/Library/ImportPanel";
import LibraryFilters, {
  EMPTY_FILTERS,
} from "@/components/Library/LibraryFilters";
import type { LibraryFilterState } from "@/components/Library/LibraryFilters";
import GameRow from "@/components/Library/GameRow";
import type { LibraryGame } from "@/components/Library/GameRow";
import styles from "./library.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PER_PAGE = 20;
const POLL_INTERVAL_MS = 3000;
/**
 * Give up polling after ~10 minutes. Analysis runs in an in-process background
 * task, so a backend restart mid-run leaves the record stuck on "processing"
 * forever — without a cap the client would poll for the life of the tab.
 */
const MAX_POLL_ATTEMPTS = 200;

/**
 * `useSearchParams` suspends during prerendering, so the reader lives in a
 * child under its own Suspense boundary.
 */
export default function LibraryPage() {
  return (
    <>
      <Navbar />
      <Suspense
        fallback={
          <main className={styles.libraryPage}>
            <div className={styles.container}>
              <div className={styles.loadingState}>Loading library…</div>
            </div>
          </main>
        }
      >
        <LibraryContent />
      </Suspense>
    </>
  );
}

function LibraryContent() {
  const searchParams = useSearchParams();
  const openingParam = searchParams.get("opening") ?? "";

  const [games, setGames] = useState<LibraryGame[]>([]);
  const [totalGames, setTotalGames] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [showImport, setShowImport] = useState(false);

  const [filters, setFilters] = useState<LibraryFilterState>(EMPTY_FILTERS);
  // Search is debounced separately so typing doesn't fire a request per key.
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // ECO drill-down arrives via ?opening=<eco> from the openings table. Held in
  // state so it can be dismissed without a navigation.
  const [openingEco, setOpeningEco] = useState(openingParam);

  const [analyzing, setAnalyzing] = useState<Set<string>>(new Set());
  const pollTimersRef = useRef<Map<string, ReturnType<typeof setInterval>>>(
    new Map(),
  );

  const { result, analyzed, timeControl } = filters;

  useEffect(() => {
    setOpeningEco(openingParam);
  }, [openingParam]);

  /* ─── Debounce the search field ─── */
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(filters.search), 300);
    return () => clearTimeout(timer);
  }, [filters.search]);

  /* ─── Any filter change returns to the first page ─── */
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, result, analyzed, timeControl, openingEco]);

  /* ─── Fetch ─── */
  const fetchGames = useCallback(async () => {
    setError("");
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: String(PER_PAGE),
      });
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (result) params.set("result", result);
      if (analyzed) params.set("analyzed", analyzed);
      if (timeControl) params.set("time_control", timeControl);
      if (openingEco) params.set("opening_eco", openingEco);

      const resp = await fetch(`${API_BASE}/api/games?${params}`);
      if (!resp.ok) {
        setError(`Failed to load games (HTTP ${resp.status})`);
        return;
      }

      const data = await resp.json();
      setGames(data.games ?? []);
      setTotalGames(data.total ?? 0);
    } catch {
      setError("Cannot connect to backend — is the server running?");
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, result, analyzed, timeControl, openingEco]);

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  /**
   * Poll timers outlive the `fetchGames` closure they were created with, so
   * they read it through a ref. Without this, an analysis finishing after the
   * user changed a filter would refetch using the filter values from when the
   * timer started.
   */
  const fetchGamesRef = useRef(fetchGames);
  useEffect(() => {
    fetchGamesRef.current = fetchGames;
  }, [fetchGames]);

  /* ─── Analysis polling ─── */
  const stopPolling = useCallback((gameId: string) => {
    const timer = pollTimersRef.current.get(gameId);
    if (timer) clearInterval(timer);
    pollTimersRef.current.delete(gameId);
    setAnalyzing((prev) => {
      const next = new Set(prev);
      next.delete(gameId);
      return next;
    });
  }, []);

  const pollAnalysis = useCallback(
    (gameId: string) => {
      // Never stack two pollers on the same game.
      if (pollTimersRef.current.has(gameId)) return;

      let attempts = 0;
      const timer = setInterval(async () => {
        attempts += 1;

        if (attempts > MAX_POLL_ATTEMPTS) {
          stopPolling(gameId);
          await fetchGamesRef.current();
          return;
        }

        try {
          const resp = await fetch(`${API_BASE}/api/analysis/${gameId}`);
          if (!resp.ok) return; // 404 until the record lands; keep waiting.

          const data = await resp.json();
          if (data.status === "complete" || data.status === "failed") {
            stopPolling(gameId);
            await fetchGamesRef.current();
          }
        } catch {
          stopPolling(gameId);
        }
      }, POLL_INTERVAL_MS);

      pollTimersRef.current.set(gameId, timer);
    },
    [stopPolling],
  );

  const handleAnalyze = useCallback(
    async (gameId: string) => {
      setAnalyzing((prev) => new Set(prev).add(gameId));

      try {
        const resp = await fetch(`${API_BASE}/api/analysis/${gameId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });

        if (!resp.ok) {
          stopPolling(gameId);
          setError(`Could not start analysis (HTTP ${resp.status})`);
          return;
        }

        const data = await resp.json();
        // "queued" on a fresh run, but an already-running analysis answers
        // "processing" — both mean we should watch for completion.
        if (["queued", "processing", "pending"].includes(data.status)) {
          pollAnalysis(gameId);
        } else {
          stopPolling(gameId);
          await fetchGamesRef.current();
        }
      } catch {
        stopPolling(gameId);
        setError("Cannot reach the backend to start analysis.");
      }
    },
    [pollAnalysis, stopPolling],
  );

  /* ─── Clear every poller on unmount ─── */
  useEffect(() => {
    const timers = pollTimersRef.current;
    return () => {
      timers.forEach((timer) => clearInterval(timer));
      timers.clear();
    };
  }, []);

  /* ─── Resume polling for anything the server reports as in-flight ─── */
  useEffect(() => {
    for (const game of games) {
      if (
        game.analysis_status === "processing" ||
        game.analysis_status === "pending"
      ) {
        pollAnalysis(game.id);
      }
    }
  }, [games, pollAnalysis]);

  const totalPages = Math.max(1, Math.ceil(totalGames / PER_PAGE));
  const isFiltered =
    debouncedSearch !== "" ||
    result !== "" ||
    analyzed !== "" ||
    timeControl !== "" ||
    openingEco !== "";

  const clearAllFilters = () => {
    setFilters({ ...EMPTY_FILTERS });
    setOpeningEco("");
  };

  return (
    <main className={styles.libraryPage}>
        <div className={styles.container}>
          <div className={styles.pageHeader}>
            <div>
              <h1 className={styles.pageTitle}>Game Library</h1>
              <p className={styles.pageSubtitle}>
                Every game you&apos;ve imported, with its analysis state.
              </p>
            </div>
            <button
              className="btn-primary"
              onClick={() => setShowImport((v) => !v)}
              id="btn-toggle-import"
              aria-expanded={showImport}
            >
              {showImport ? "✕ Close" : "＋ Import games"}
            </button>
          </div>

          {showImport && (
            <ImportPanel apiBase={API_BASE} onImported={fetchGames} />
          )}

          <LibraryFilters
            value={filters}
            onChange={setFilters}
            totalGames={totalGames}
          />

          {openingEco && (
            <div className={styles.activeFilter} id="opening-filter-chip">
              <span>
                Showing only opening <strong>{openingEco}</strong>
              </span>
              <button
                className={styles.chipClear}
                onClick={() => setOpeningEco("")}
                aria-label="Clear opening filter"
              >
                ✕
              </button>
            </div>
          )}

          {error && (
            <div className={styles.errorState} id="library-error">
              <span>⚠ {error}</span>
              <button className={styles.retryLink} onClick={fetchGames}>
                Retry
              </button>
            </div>
          )}

          <div className={styles.gamesList}>
            {loading ? (
              <div className={styles.loadingState}>Loading games…</div>
            ) : games.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>♟</div>
                {isFiltered ? (
                  <>
                    <p>No games match these filters.</p>
                    <button
                      className={styles.retryLink}
                      onClick={clearAllFilters}
                    >
                      Clear filters
                    </button>
                  </>
                ) : (
                  <>
                    <p>No games yet.</p>
                    <p className={styles.emptyHint}>
                      Import from Lichess or Chess.com, or upload a PGN file.
                    </p>
                    <button
                      className="btn-primary"
                      onClick={() => setShowImport(true)}
                    >
                      ＋ Import games
                    </button>
                  </>
                )}
              </div>
            ) : (
              games.map((game) => (
                <GameRow
                  key={game.id}
                  game={game}
                  busy={analyzing.has(game.id)}
                  onAnalyze={handleAnalyze}
                />
              ))
            )}
          </div>

          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className="btn-secondary"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                id="page-prev"
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
                id="page-next"
              >
                Next →
              </button>
            </div>
          )}
        </div>
    </main>
  );
}
