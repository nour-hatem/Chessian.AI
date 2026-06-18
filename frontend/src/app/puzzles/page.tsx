import Link from "next/link";
import Navbar from "@/components/Layout/Navbar";
import styles from "../coming-soon.module.css";

const FEATURES = [
  {
    icon: "🎯",
    name: "Weakness-Targeted Puzzles",
    desc: "Automatically selects puzzles that target your specific tactical blindspots — forks, pins, back-rank threats — based on your actual game history.",
  },
  {
    icon: "🔄",
    name: "Spaced Repetition",
    desc: "SM-2 algorithm schedules re-presentation of previously failed puzzles before you forget them, just like Anki for chess.",
  },
  {
    icon: "📈",
    name: "Separate Puzzle Rating",
    desc: "Track your puzzle rating independently from your game rating. Watch your tactical vision improve over time.",
  },
  {
    icon: "🏷️",
    name: "Motif Tagging",
    desc: "Every puzzle tagged with its tactical motif. Focus on specific themes or let the AI choose based on your blindspot map.",
  },
  {
    icon: "🧠",
    name: "Flow State Difficulty",
    desc: "Dynamic difficulty keeps puzzles just beyond your current ability — challenging enough to learn, easy enough to stay engaged.",
  },
  {
    icon: "📊",
    name: "Game-to-Puzzle Pipeline",
    desc: "No other platform connects your game analysis to puzzle selection. Missed a fork in your game? You'll drill forks until you don't.",
  },
];

export default function PuzzlesPage() {
  return (
    <>
      <Navbar />
      <main className={styles.comingSoonPage}>
        <div className={styles.hero}>
          <div className={styles.heroIcon}>🧩</div>
          <h1 className={styles.heroTitle}>Smart Puzzles</h1>
          <p className={styles.heroSubtitle}>
            Puzzles auto-selected to target your specific weaknesses with spaced
            repetition scheduling. Not random — personalized to your game data.
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
          <Link href="/library" className={styles.ctaLink} id="puzzles-cta">
            ← Go to Game Library
          </Link>
        </div>
      </main>
    </>
  );
}
