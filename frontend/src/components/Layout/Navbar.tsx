"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Navbar.module.css";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: "⚡" },
  { href: "/play", label: "Play", icon: "♟" },
  { href: "/library", label: "Library", icon: "📚" },
  { href: "/puzzles", label: "Puzzles", icon: "🧩", comingSoon: true },
  { href: "/coach", label: "Coach", icon: "🤖", comingSoon: true },
  { href: "/plan", label: "Plan", icon: "📈", comingSoon: true },
];

export default function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className={styles.navbar} id="main-navbar">
      <div className={styles.inner}>
        <Link href="/" className={styles.logo} id="nav-logo">
          <span className={styles.logoIcon}>♔</span>
          <span className={styles.logoText}>
            Chessian<span className={styles.logoDot}>.AI</span>
          </span>
        </Link>

        <ul
          className={`${styles.navLinks} ${mobileOpen ? styles.navLinksOpen : ""}`}
        >
          {NAV_ITEMS.map((item) => (
            <li key={item.href}>
              {item.comingSoon ? (
                <span
                  className={`${styles.navLink} ${styles.navLinkDisabled}`}
                  title="Coming Soon"
                  id={`nav-${item.label.toLowerCase()}`}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className={`${styles.navLink} ${pathname === item.href ? styles.navLinkActive : ""}`}
                  id={`nav-${item.label.toLowerCase()}`}
                  onClick={() => setMobileOpen(false)}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  {item.label}
                </Link>
              )}
            </li>
          ))}
        </ul>

        <div className={styles.navActions}>
          <button className="btn-secondary" id="nav-sign-in">
            Sign In
          </button>
          <button
            className={styles.hamburger}
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
            id="nav-hamburger"
          >
            <span className={`${styles.hamburgerLine} ${mobileOpen ? styles.hamburgerOpen : ""}`} />
            <span className={`${styles.hamburgerLine} ${mobileOpen ? styles.hamburgerOpen : ""}`} />
            <span className={`${styles.hamburgerLine} ${mobileOpen ? styles.hamburgerOpen : ""}`} />
          </button>
        </div>
      </div>
    </nav>
  );
}
