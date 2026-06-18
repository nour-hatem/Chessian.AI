import Link from "next/link";
import Navbar from "@/components/Layout/Navbar";
import styles from "../coming-soon.module.css";

const FEATURES = [
  {
    icon: "💬",
    name: "Conversational Analysis",
    desc: "Ask about any game, any position, any concept. The coach has access to your full game history and behavioral profile via RAG.",
  },
  {
    icon: "📚",
    name: "Grounded in Your Data",
    desc: "Every response is backed by your actual game data — no generic advice. \"You lose 58% of Rook endgames\" not \"Rook endgames are important.\"",
  },
  {
    icon: "🔍",
    name: "Position-Aware",
    desc: "Reference any position by move number and the coach renders it inline. \"Show me the position after move 23\" — and there it is.",
  },
  {
    icon: "🎓",
    name: "Coaching Language",
    desc: "Explains positions in coaching language, not engine jargon. Understands tactical motifs, strategic themes, and pawn structures.",
  },
  {
    icon: "🎙️",
    name: "Voice Interface",
    desc: "Speak to the coach instead of typing. Perfect for analyzing positions with your hands on the board.",
  },
  {
    icon: "🧠",
    name: "Pattern Recognition",
    desc: "Identifies your recurring patterns across hundreds of games. \"You consistently rush in time pressure after move 30.\"",
  },
];

export default function CoachPage() {
  return (
    <>
      <Navbar />
      <main className={styles.comingSoonPage}>
        <div className={styles.hero}>
          <div className={styles.heroIcon}>🤖</div>
          <h1 className={styles.heroTitle}>AI Chess Coach</h1>
          <p className={styles.heroSubtitle}>
            A persistent AI coach that knows your games, your patterns, and your
            weaknesses. Ask anything — grounded in your data, not generic advice.
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
          <Link href="/library" className={styles.ctaLink} id="coach-cta">
            ← Go to Game Library
          </Link>
        </div>
      </main>
    </>
  );
}
