"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Navbar.module.css";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: "⚡" },
  { href: "/play", label: "Play", icon: "♟" },
  { href: "/library", label: "Library", icon: "📚" },
  { href: "/puzzles", label: "Puzzles", icon: "🧩", tag: "soon" },
  { href: "/coach", label: "Coach", icon: "🤖", tag: "soon" },
  { href: "/plan", label: "Plan", icon: "📈", tag: "soon" },
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
              <Link
                href={item.href}
                className={`${styles.navLink} ${pathname === item.href ? styles.navLinkActive : ""}`}
                id={`nav-${item.label.toLowerCase()}`}
                onClick={() => setMobileOpen(false)}
              >
                <span className={styles.navIcon}>{item.icon}</span>
                {item.label}
                {item.tag && (
                  <span className={styles.navTag}>{item.tag}</span>
                )}
              </Link>
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
