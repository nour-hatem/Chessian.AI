"use client";

import { useRef, useState } from "react";
import styles from "./ImportPanel.module.css";

type Platform = "lichess" | "chesscom";

interface ImportPanelProps {
  apiBase: string;
  /** Called after an import that actually added games, so the list refreshes. */
  onImported: () => void | Promise<void>;
}

interface ImportResult {
  text: string;
  ok: boolean;
}

export default function ImportPanel({ apiBase, onImported }: ImportPanelProps) {
  const [platform, setPlatform] = useState<Platform>("lichess");
  const [username, setUsername] = useState("");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImport = async () => {
    const name = username.trim();
    if (!name || importing) return;

    setImporting(true);
    setResult(null);

    try {
      const resp = await fetch(`${apiBase}/api/import/${platform}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: name, max_games: 100 }),
      });

      if (!resp.ok) {
        setResult({ text: `Import failed (HTTP ${resp.status})`, ok: false });
        return;
      }

      const data = await resp.json();
      setResult({
        text: data.message || "Import finished.",
        ok: data.status === "complete",
      });

      if (data.status === "complete" && data.games_imported > 0) {
        await onImported();
      }
    } catch {
      setResult({ text: "Import failed — is the backend running?", ok: false });
    } finally {
      setImporting(false);
    }
  };

  const handlePgnUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch(`${apiBase}/api/import/pgn`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        setResult({ text: `Upload failed (HTTP ${resp.status})`, ok: false });
        return;
      }

      const data = await resp.json();
      setResult({
        text: data.message || "Upload finished.",
        ok: data.status === "complete",
      });

      if (data.status === "complete" && data.games_imported > 0) {
        await onImported();
      }
    } catch {
      setResult({ text: "Upload failed — is the backend running?", ok: false });
    } finally {
      setImporting(false);
      // Reset the input so re-selecting the same file fires onChange again.
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className={styles.panel} id="import-section">
      <div className={styles.body}>
        <div className={styles.platformToggle}>
          <button
            className={`${styles.platformBtn} ${platform === "lichess" ? styles.platformBtnActive : ""}`}
            onClick={() => setPlatform("lichess")}
            id="platform-lichess"
            aria-pressed={platform === "lichess"}
          >
            ♞ Lichess
          </button>
          <button
            className={`${styles.platformBtn} ${platform === "chesscom" ? styles.platformBtnActive : ""}`}
            onClick={() => setPlatform("chesscom")}
            id="platform-chesscom"
            aria-pressed={platform === "chesscom"}
          >
            ♟ Chess.com
          </button>
        </div>

        <div className={styles.inputRow}>
          <input
            type="text"
            className={styles.input}
            placeholder={`Your ${platform === "lichess" ? "Lichess" : "Chess.com"} username`}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleImport()}
            id="input-username"
          />
          <button
            className="btn-primary"
            onClick={handleImport}
            disabled={importing || !username.trim()}
            id="btn-import"
          >
            {importing ? "Importing…" : "Import"}
          </button>
        </div>

        <div className={styles.uploadRow}>
          <span className={styles.orDivider}>or</span>
          <label className={styles.uploadLabel} id="btn-upload-pgn">
            📄 Upload PGN file
            <input
              ref={fileInputRef}
              type="file"
              accept=".pgn"
              hidden
              onChange={handlePgnUpload}
            />
          </label>
        </div>

        {result && (
          <p
            className={`${styles.message} ${result.ok ? styles.messageOk : styles.messageError}`}
          >
            {result.text}
          </p>
        )}
      </div>
    </div>
  );
}
