"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./Clock.module.css";

interface ClockProps {
  initialTime: number; // in seconds
  increment?: number; // in seconds
  active: boolean;
  color: "white" | "black";
  onTimeout?: () => void;
}

function formatTime(seconds: number): string {
  if (seconds <= 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return `${hrs}:${remainMins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export default function Clock({
  initialTime,
  increment = 0,
  active,
  color,
  onTimeout,
}: ClockProps) {
  const [timeLeft, setTimeLeft] = useState(initialTime);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastTickRef = useRef<number>(Date.now());
  const onTimeoutRef = useRef(onTimeout);

  // Keep the callback ref fresh without causing effect re-runs
  useEffect(() => {
    onTimeoutRef.current = onTimeout;
  }, [onTimeout]);

  const isLow = timeLeft < 30;
  const isCritical = timeLeft < 10;

  // H2 fix: timeLeft removed from deps — timer uses refs to avoid infinite re-runs
  useEffect(() => {
    if (active) {
      lastTickRef.current = Date.now();
      intervalRef.current = setInterval(() => {
        const now = Date.now();
        const elapsed = (now - lastTickRef.current) / 1000;
        lastTickRef.current = now;
        setTimeLeft((prev) => {
          const next = prev - elapsed;
          if (next <= 0) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            onTimeoutRef.current?.();
            return 0;
          }
          return next;
        });
      }, 100);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active]);

  // Add increment when clock becomes inactive (move made)
  const prevActive = useRef(active);
  useEffect(() => {
    if (prevActive.current && !active && increment > 0) {
      setTimeLeft((prev) => prev + increment);
    }
    prevActive.current = active;
  }, [active, increment]);

  return (
    <div
      className={`${styles.clock} ${active ? styles.active : ""} ${isCritical ? styles.critical : isLow ? styles.low : ""}`}
      id={`clock-${color}`}
    >
      <div className={styles.colorIndicator}>
        <span
          className={`${styles.dot} ${color === "white" ? styles.dotWhite : styles.dotBlack}`}
        />
      </div>
      <span className={styles.time}>{formatTime(timeLeft)}</span>
    </div>
  );
}

export { Clock };
