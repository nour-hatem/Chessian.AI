import Link from "next/link";
import Navbar from "@/components/Layout/Navbar";
import styles from "./page.module.css";

/**
 * `soon: true` marks a feature that is not built yet. The landing page used to
 * present all six identically, which promised an AI coach and a blindspot map
 * that don't exist behind any working route.
 */
const FEATURES: {
  icon: string;
  title: string;
  desc: string;
  tag: string;
  soon?: boolean;
}[] = [
  {
    icon: "🔍",
    title: "Deep Move Analysis",
    desc: "Every move evaluated by Stockfish. Classified as brilliant, best, inaccuracy, mistake, or blunder with centipawn-loss precision.",
    tag: "Engine-Powered",
  },
  {
    icon: "💬",
    title: "Natural Language Explanations",
    desc: "AI-generated coaching explanations for every critical moment. Understand why a move was wrong, not just that it was.",
    tag: "LLM-Powered",
  },
  {
    icon: "📊",
    title: "Phase-Separated Accuracy",
    desc: "Separate accuracy scores for opening, middlegame, and endgame. Know exactly which phase of your game needs work.",
    tag: "Novel",
  },
  {
    icon: "🧩",
    title: "Smart Puzzle Engine",
    desc: "Puzzles scheduled by an SM-2 spaced-repetition system and matched to your rating band. Not random — adaptive.",
    tag: "Adaptive",
  },
  {
    icon: "🎯",
    title: "Tactical Blindspot Map",
    desc: "Identifies which tactical motifs you repeatedly miss — forks, pins, back-rank threats — across your entire game history.",
    tag: "Planned",
    soon: true,
  },
  {
    icon: "🤖",
    title: "AI Chess Coach",
    desc: "Chat with an AI coach that knows your games. Ask about your patterns, weaknesses, or any position — grounded in your data.",
    tag: "Planned",
    soon: true,
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        {/* Hero */}
        <section className={styles.hero} id="hero-section">
          <div className={styles.heroContent}>
            <div className={styles.badge}>
              <span className={styles.badgeDot} />
              AI-Powered Chess Improvement
            </div>
            <h1 className={styles.title}>
              Understand Your Chess.
              <br />
              <span className={styles.titleHighlight}>Improve Faster.</span>
            </h1>
            <p className={styles.subtitle}>
              Chessian.AI analyzes your games from Chess.com and Lichess,
              identifies your recurring weaknesses, and builds a personalized
              plan to make you a stronger player.
            </p>
            <div className={styles.heroCta}>
              <Link
                href="/library"
                className={styles.ctaPrimary}
                id="cta-import"
              >
                Import Your Games
              </Link>
              <Link href="/puzzles" className={styles.ctaSecondary} id="cta-puzzles">
                Train with Puzzles
              </Link>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className={styles.features} id="features-section">
          <p className={styles.sectionLabel}>Features</p>
          <h2 className={styles.sectionTitle}>
            Everything you need to improve
          </h2>
          <div className={styles.featureGrid}>
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className={`${styles.featureCard} ${f.soon ? styles.featureCardSoon : ""}`}
              >
                <span className={styles.featureIcon}>{f.icon}</span>
                <h3 className={styles.featureTitle}>{f.title}</h3>
                <p className={styles.featureDesc}>{f.desc}</p>
                <span
                  className={`${styles.featureTag} ${f.soon ? styles.featureTagSoon : ""}`}
                >
                  {f.tag}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Platforms */}
        <section className={styles.platforms} id="platforms-section">
          <p className={styles.sectionLabel}>Import From</p>
          <h2 className={styles.sectionTitle}>
            All your games, one place
          </h2>
          <div className={styles.platformLogos}>
            <div className={styles.platformItem}>
              <span className={styles.platformIcon}>♟</span>
              <span className={styles.platformName}>Chess.com</span>
            </div>
            <div className={styles.platformItem}>
              <span className={styles.platformIcon}>♞</span>
              <span className={styles.platformName}>Lichess</span>
            </div>
            <div className={styles.platformItem}>
              <span className={styles.platformIcon}>📄</span>
              <span className={styles.platformName}>PGN Files</span>
            </div>
          </div>
        </section>

        {/* Bottom CTA */}
        <section className={styles.bottomCta} id="bottom-cta">
          <h2 className={styles.bottomCtaTitle}>
            Ready to find your weaknesses?
          </h2>
          <p className={styles.bottomCtaText}>
            Import your games and get your first analysis in under a minute.
          </p>
          <Link href="/library" className={styles.ctaPrimary} id="cta-get-started">
            Get Started — Free
          </Link>
        </section>

        {/* Footer */}
        <footer className={styles.footer}>
          <p className={styles.footerText}>
            © 2026 Chessian.AI — Built at Helwan University. MIT Licensed.
          </p>
        </footer>
      </main>
    </>
  );
}
