import Link from "next/link";
import Navbar from "@/components/Layout/Navbar";
import styles from "../coming-soon.module.css";

const FEATURES = [
  {
    icon: "📋",
    name: "Weekly Improvement Plan",
    desc: "Structured weekly tasks based on your behavioral profile. Prioritized by expected rating gain — the biggest weaknesses get addressed first.",
  },
  {
    icon: "🎯",
    name: "Data-Driven Priorities",
    desc: "Not generic advice. Your plan is computed from your actual game data: endgame conversion rate, tactical blindspots, opening accuracy.",
  },
  {
    icon: "📉",
    name: "Weakness Decay Tracking",
    desc: "As you improve a weakness, it's automatically downgraded. When new patterns emerge, they're elevated. Your plan is never static.",
  },
  {
    icon: "⏱️",
    name: "Time-Aware Scheduling",
    desc: "Tell us how many hours per week you can train. The plan adapts to fit — no unrealistic expectations.",
  },
  {
    icon: "🏆",
    name: "Goal-Based Progress",
    desc: "Set a target rating and date. The system back-calculates what improvement rate you need per dimension to get there.",
  },
  {
    icon: "🔄",
    name: "Continuous Adaptation",
    desc: "Every new game you play updates your profile. The plan evolves with you — what was a weakness last month may be a strength today.",
  },
];

export default function PlanPage() {
  return (
    <>
      <Navbar />
      <main className={styles.comingSoonPage}>
        <div className={styles.hero}>
          <div className={styles.heroIcon}>📈</div>
          <h1 className={styles.heroTitle}>Improvement Plan</h1>
          <p className={styles.heroSubtitle}>
            A personalized, data-driven curriculum that evolves with your play.
            Know exactly what to study, practice, and focus on each week.
          </p>
          <div className={styles.badge}>
            <span className={styles.badgeDot} />
            Coming Soon
          </div>
        </div>

        <div className={styles.featuresSection}>
          <p className={styles.featuresTitle}>What to expect</p>
          <div className={styles.featuresGrid}>
            {FEATURES.map((f) => (
              <div key={f.name} className={styles.featureCard}>
                <span className={styles.featureIcon}>{f.icon}</span>
                <div className={styles.featureName}>{f.name}</div>
                <p className={styles.featureDesc}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.ctaSection}>
          <p className={styles.ctaText}>
            In the meantime, import your games and get your analysis.
          </p>
          <Link href="/library" className={styles.ctaLink} id="plan-cta">
            ← Go to Game Library
          </Link>
        </div>
      </main>
    </>
  );
}
