"use client";

import styles from "./LibraryFilters.module.css";

export type ResultFilter = "" | "win" | "loss" | "draw";
export type StatusFilter = "" | "yes" | "no" | "failed";
export type TimeFilter = "" | "bullet" | "blitz" | "rapid" | "classical";

export interface LibraryFilterState {
  search: string;
  result: ResultFilter;
  analyzed: StatusFilter;
  timeControl: TimeFilter;
}

export const EMPTY_FILTERS: LibraryFilterState = {
  search: "",
  result: "",
  analyzed: "",
  timeControl: "",
};

interface LibraryFiltersProps {
  value: LibraryFilterState;
  onChange: (next: LibraryFilterState) => void;
  totalGames: number;
}

const RESULT_OPTIONS: { key: ResultFilter; label: string }[] = [
  { key: "", label: "All" },
  { key: "win", label: "Wins" },
  { key: "loss", label: "Losses" },
  { key: "draw", label: "Draws" },
];

const STATUS_OPTIONS: { key: StatusFilter; label: string }[] = [
  { key: "", label: "All" },
  { key: "yes", label: "Analyzed" },
  { key: "no", label: "Not analyzed" },
  { key: "failed", label: "Failed" },
];

const TIME_OPTIONS: { key: TimeFilter; label: string }[] = [
  { key: "", label: "All" },
  { key: "bullet", label: "Bullet" },
  { key: "blitz", label: "Blitz" },
  { key: "rapid", label: "Rapid" },
  { key: "classical", label: "Classical" },
];

export default function LibraryFilters({
  value,
  onChange,
  totalGames,
}: LibraryFiltersProps) {
  const isFiltered =
    value.search !== "" ||
    value.result !== "" ||
    value.analyzed !== "" ||
    value.timeControl !== "";

  function renderGroup<T extends string>(
    label: string,
    options: { key: T; label: string }[],
    current: T,
    onSelect: (next: T) => void,
    idPrefix: string,
  ) {
    return (
      <div className={styles.group}>
        <span className={styles.groupLabel}>{label}</span>
        {options.map((opt) => (
          <button
            key={opt.key || "all"}
            id={`${idPrefix}-${opt.key || "all"}`}
            className={`${styles.chip} ${current === opt.key ? styles.chipActive : ""}`}
            onClick={() => onSelect(opt.key)}
            aria-pressed={current === opt.key}
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.filters} id="library-filters">
      <div className={styles.searchWrap}>
        <span className={styles.searchIcon}>🔍</span>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search opening or player…"
          value={value.search}
          onChange={(e) => onChange({ ...value, search: e.target.value })}
          id="input-search"
        />
      </div>

      {renderGroup(
        "Result",
        RESULT_OPTIONS,
        value.result,
        (result) => onChange({ ...value, result }),
        "filter-result",
      )}
      {renderGroup(
        "Status",
        STATUS_OPTIONS,
        value.analyzed,
        (analyzed) => onChange({ ...value, analyzed }),
        "filter-status",
      )}
      {renderGroup(
        "Time",
        TIME_OPTIONS,
        value.timeControl,
        (timeControl) => onChange({ ...value, timeControl }),
        "filter-time",
      )}

      {isFiltered && (
        <button
          className={styles.clearBtn}
          onClick={() => onChange({ ...EMPTY_FILTERS })}
          id="filter-clear"
        >
          ✕ Clear
        </button>
      )}

      <span className={styles.count}>
        {totalGames} game{totalGames !== 1 ? "s" : ""}
      </span>
    </div>
  );
}
