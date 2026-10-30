"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Layout/Navbar";
import styles from "./plan.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface WeaknessItem {
  id: string;
  title: string;
  description: string;
  severity: "high" | "medium" | "low";
  expected_gain_elo: number;
  dimension: string;
  metric: string;
}

interface PlanTask {
  id: string;
  title: string;
  category: string;
  duration_minutes: number;
  description: string;
  action_url: string;
  action_label: string;
  completed: boolean;
}

interface ImprovementPlan {
  user_id: string;
  resolved_username: string | null;
  total_games_analyzed: number;
  overall_accuracy: number | null;
  opening_accuracy: number | null;
  middlegame_accuracy: number | null;
  endgame_accuracy: number | null;
  weakest_phase: string;
  blunder_rate_per_game: number;
  mistake_rate_per_game: number;
  puzzle_rating_center: number;
  puzzles_due_count: number;
  puzzle_streak: number;
  coaching_summary: string;
  focus_headline: string;
  planned_hours: number;
  weaknesses: WeaknessItem[];
  tasks: PlanTask[];
}

export default function PlanPage() {
  const [plan, setPlan] = useState<ImprovementPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null);

  const fetchPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/plan`);
      if (!res.ok) {
        throw new Error(`Failed to load plan: ${res.statusText}`);
      }
      const data: ImprovementPlan = await res.json();
      setPlan(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error loading plan";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) void fetchPlan();
    });
    return () => {
      active = false;
    };
  }, []);

  const handleToggleTask = async (taskId: string) => {
    if (!plan) return;

    // Optimistic UI update
    setPlan((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        tasks: prev.tasks.map((t) =>
          t.id === taskId ? { ...t, completed: !t.completed } : t
        ),
      };
    });

    setTogglingTaskId(taskId);
    try {
      const res = await fetch(`${API_BASE}/api/plan/tasks/${taskId}/toggle`, {
        method: "POST",
      });
      if (!res.ok) {
        // Rollback on failure
        fetchPlan();
      }
    } catch {
      fetchPlan();
    } finally {
      setTogglingTaskId(null);
    }
  };

  const completedCount = plan?.tasks.filter((t) => t.completed).length || 0;
  const totalTasks = plan?.tasks.length || 0;
  const progressPct =
    totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;

  return (
    <>
      <Navbar />
      <main className={styles.planPage}>
        <div className={styles.container}>
          {loading ? (
            <div className={styles.loadingContainer}>
              <div className={styles.spinner} />
              <p>Analyzing behavioral data & synthesizing your plan...</p>
            </div>
          ) : error ? (
            <div className={styles.loadingContainer}>
              <p style={{ color: "var(--move-blunder)" }}>{error}</p>
              <button onClick={fetchPlan} className={styles.refreshBtn}>
                Try Again
              </button>
            </div>
          ) : !plan ? null : (
            <>
              {/* Header */}
              <div className={styles.header}>
                <div className={styles.titleRow}>
                  <div>
                    <h1 className={styles.pageTitle}>Personalized Improvement Plan</h1>
                    <p className={styles.pageSubtitle}>
                      Data-driven weekly curriculum synthesized from {plan.total_games_analyzed} of your analyzed games.
                      Weaknesses are scored and prioritized by expected rating gain.
                    </p>
                  </div>
                  <button
                    onClick={fetchPlan}
                    className={styles.refreshBtn}
                    id="plan-refresh-btn"
                  >
                    <span>🔄</span> Refresh Plan
                  </button>
                </div>
              </div>

              {/* Coach Briefing Banner */}
              <section className={styles.coachCard} id="coach-briefing">
                <div className={styles.coachHeader}>
                  <span className={styles.coachBadge}>
                    <span>🤖</span> AI Coach Diagnostic
                  </span>
                  <span className={styles.focusHeadline}>
                    Focus: {plan.focus_headline}
                  </span>
                </div>
                <p className={styles.coachSummary}>{plan.coaching_summary}</p>
              </section>

              {/* Diagnostic Metrics Grid */}
              <section className={styles.diagnosticsGrid}>
                {/* Phase Breakdown */}
                <div className={styles.statCard}>
                  <div className={styles.statCardTitle}>Phase-Separated Accuracy</div>
                  <div className={styles.statMainValue}>
                    {plan.overall_accuracy !== null ? `${plan.overall_accuracy}%` : "—"}
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--text-tertiary)",
                        fontWeight: 400,
                        marginLeft: 8,
                      }}
                    >
                      overall
                    </span>
                  </div>
                  <div className={styles.phaseBarGroup}>
                    <div className={styles.phaseRow}>
                      <span className={styles.phaseLabel}>Opening</span>
                      <div className={styles.phaseBarTrack}>
                        <div
                          className={styles.phaseBarFill}
                          style={{ width: `${Math.min(100, (plan.opening_accuracy || 0) * 1.5)}%` }}
                        />
                      </div>
                      <span className={styles.phaseAccVal}>
                        {plan.opening_accuracy || 0}%
                      </span>
                    </div>
                    <div className={styles.phaseRow}>
                      <span className={styles.phaseLabel}>Middlegame</span>
                      <div className={styles.phaseBarTrack}>
                        <div
                          className={`${styles.phaseBarFill} ${plan.weakest_phase === "Middlegame" ? styles.phaseBarFillWeakest : ""}`}
                          style={{ width: `${Math.min(100, (plan.middlegame_accuracy || 0) * 1.5)}%` }}
                        />
                      </div>
                      <span className={styles.phaseAccVal}>
                        {plan.middlegame_accuracy || 0}%
                      </span>
                    </div>
                    <div className={styles.phaseRow}>
                      <span className={styles.phaseLabel}>Endgame</span>
                      <div className={styles.phaseBarTrack}>
                        <div
                          className={`${styles.phaseBarFill} ${plan.weakest_phase === "Endgame" ? styles.phaseBarFillWeakest : ""}`}
                          style={{ width: `${Math.min(100, (plan.endgame_accuracy || 0) * 1.5)}%` }}
                        />
                      </div>
                      <span className={styles.phaseAccVal}>
                        {plan.endgame_accuracy || 0}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tactical Health */}
                <div className={styles.statCard}>
                  <div className={styles.statCardTitle}>Tactical Error Frequency</div>
                  <div className={styles.statMainValue}>
                    {plan.blunder_rate_per_game}
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--move-blunder)",
                        fontWeight: 500,
                        marginLeft: 8,
                      }}
                    >
                      blunders / game
                    </span>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.5 }}>
                    Plus <strong>{plan.mistake_rate_per_game}</strong> mistakes per game.
                    Eliminating 1 blunder per game translates to approximately ~120 ELO gain in rapid play.
                  </p>
                </div>

                {/* Puzzle & Spaced Repetition */}
                <div className={styles.statCard}>
                  <div className={styles.statCardTitle}>Tactical Retention (SM-2)</div>
                  <div className={styles.statMainValue}>
                    {plan.puzzle_rating_center}
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--text-tertiary)",
                        fontWeight: 400,
                        marginLeft: 8,
                      }}
                    >
                      target ELO
                    </span>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.5 }}>
                    <strong>{plan.puzzles_due_count}</strong> puzzles due today in your spaced-repetition queue.
                    Solve daily to prevent tactical pattern decay.
                  </p>
                </div>
              </section>

              {/* Prioritized Weakness Matrix */}
              <section style={{ marginBottom: "var(--space-2xl)" }}>
                <h2 className={styles.sectionTitle}>
                  <span>🎯</span> Prioritized Weaknesses
                </h2>
                <p className={styles.sectionSubtitle}>
                  Identified by cross-referencing your game results, tactical centipawn loss, and opening performance.
                </p>
                <div className={styles.weaknessList}>
                  {plan.weaknesses.map((w, idx) => (
                    <div key={w.id} className={styles.weaknessCard}>
                      <div className={styles.weaknessRank}>#{idx + 1}</div>
                      <div className={styles.weaknessContent}>
                        <div className={styles.weaknessHeader}>
                          <span className={styles.weaknessTitle}>{w.title}</span>
                          <span
                            className={
                              w.severity === "high"
                                ? styles.severityHigh
                                : w.severity === "medium"
                                ? styles.severityMedium
                                : styles.severityLow
                            }
                          >
                            {w.severity}
                          </span>
                          <span className={styles.gainBadge}>+{w.expected_gain_elo} ELO potential</span>
                          <span className={styles.metricBadge}>{w.metric}</span>
                        </div>
                        <p className={styles.weaknessDesc}>{w.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Actionable Curriculum Section */}
              <section className={styles.curriculumCard} id="weekly-curriculum">
                <div className={styles.curriculumHeader}>
                  <div>
                    <h2 className={styles.sectionTitle}>
                      <span>📋</span> Weekly Action Tasks
                    </h2>
                    <p className={styles.sectionSubtitle} style={{ marginBottom: 0 }}>
                      Complete these 5 focused exercises this week (~{plan.planned_hours} hrs total).
                    </p>
                  </div>
                  <div className={styles.progressWrap}>
                    <div className={styles.progressBar}>
                      <div
                        className={styles.progressFill}
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                    <span className={styles.progressText}>
                      {completedCount} / {totalTasks} done ({progressPct}%)
                    </span>
                  </div>
                </div>

                <div className={styles.taskList}>
                  {plan.tasks.map((task) => (
                    <div
                      key={task.id}
                      className={`${styles.taskItem} ${
                        task.completed ? styles.taskItemCompleted : ""
                      }`}
                    >
                      <button
                        onClick={() => handleToggleTask(task.id)}
                        disabled={togglingTaskId === task.id}
                        className={`${styles.checkboxBtn} ${
                          task.completed ? styles.checkboxChecked : ""
                        }`}
                        title={task.completed ? "Mark incomplete" : "Mark completed"}
                        aria-label={`Toggle ${task.title}`}
                      >
                        {task.completed ? "✓" : ""}
                      </button>

                      <div className={styles.taskBody}>
                        <div className={styles.taskTop}>
                          <span className={styles.taskCategory}>{task.category}</span>
                          <span className={styles.taskDuration}>
                            ⏱ {task.duration_minutes} min
                          </span>
                          <span
                            className={`${styles.taskTitle} ${
                              task.completed ? styles.taskCompletedTitle : ""
                            }`}
                          >
                            {task.title}
                          </span>
                        </div>
                        <p className={styles.taskDesc}>{task.description}</p>
                      </div>

                      <Link
                        href={task.action_url}
                        className={styles.taskActionBtn}
                      >
                        {task.action_label} →
                      </Link>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </>
  );
}
