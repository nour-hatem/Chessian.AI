"use client";

import { useRef, useEffect, useCallback } from "react";
import styles from "./EvalChart.module.css";

interface EvalPoint {
  moveIndex: number;
  eval: number; // centipawns, positive = white advantage
  classification?: string;
}

interface EvalChartProps {
  evalData: EvalPoint[];
  currentMoveIndex: number;
  onMoveClick?: (moveIndex: number) => void;
  height?: number;
}

const CLAMP = 600; // Max centipawns to display (±6 pawns)

function clampEval(cp: number): number {
  return Math.max(-CLAMP, Math.min(CLAMP, cp));
}

function getClassColor(classification?: string): string {
  switch (classification) {
    case "blunder":    return "#ef5350";
    case "mistake":    return "#ffb74d";
    case "inaccuracy": return "#ffd54f";
    default:           return "";
  }
}

export default function EvalChart({
  evalData,
  currentMoveIndex,
  onMoveClick,
  height = 120,
}: EvalChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const getWidth = useCallback((): number => {
    return containerRef.current?.clientWidth || 600;
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!onMoveClick || evalData.length === 0) return;
      const svg = svgRef.current;
      if (!svg) return;

      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const width = rect.width;
      const padding = 0;
      const chartWidth = width - padding * 2;

      const ratio = Math.max(0, Math.min(1, (x - padding) / chartWidth));
      const moveIndex = Math.round(ratio * (evalData.length - 1));
      const point = evalData[moveIndex];
      if (point) {
        onMoveClick(point.moveIndex);
      }
    },
    [onMoveClick, evalData]
  );

  // Render SVG chart
  useEffect(() => {
    // Force a re-render cycle when data changes
  }, [evalData, currentMoveIndex]);

  if (evalData.length === 0) {
    return (
      <div className={styles.chartContainer} ref={containerRef}>
        <div className={styles.emptyChart}>No evaluation data</div>
      </div>
    );
  }

  const width = getWidth();
  const paddingX = 0;
  const paddingY = 4;
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;
  const midY = paddingY + chartHeight / 2;

  // Build the area path
  const points = evalData.map((point, i) => {
    const x = paddingX + (i / Math.max(1, evalData.length - 1)) * chartWidth;
    const clamped = clampEval(point.eval);
    // Positive eval (white advantage) → above center line (lower Y)
    const y = midY - (clamped / CLAMP) * (chartHeight / 2);
    return { x, y, ...point };
  });

  // White advantage area (above center)
  const whiteAreaPath = buildAreaPath(points, midY, "above");
  // Black advantage area (below center)
  const blackAreaPath = buildAreaPath(points, midY, "below");
  // Main eval line
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");

  // Current move indicator
  const currentPoint = points.find((p) => p.moveIndex === currentMoveIndex);

  // Critical moment dots (blunders, mistakes)
  const criticalDots = points.filter(
    (p) => p.classification === "blunder" || p.classification === "mistake"
  );

  return (
    <div className={styles.chartContainer} ref={containerRef} id="eval-chart">
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className={styles.chartSvg}
        onClick={handleClick}
      >
        {/* Gradient definitions */}
        <defs>
          <linearGradient id="whiteGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(245, 245, 245, 0.35)" />
            <stop offset="100%" stopColor="rgba(245, 245, 245, 0.02)" />
          </linearGradient>
          <linearGradient id="blackGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(30, 30, 30, 0.02)" />
            <stop offset="100%" stopColor="rgba(30, 30, 30, 0.35)" />
          </linearGradient>
        </defs>

        {/* White advantage fill */}
        <path d={whiteAreaPath} fill="url(#whiteGrad)" />

        {/* Black advantage fill */}
        <path d={blackAreaPath} fill="url(#blackGrad)" />

        {/* Center line (equal evaluation) */}
        <line
          x1={paddingX}
          y1={midY}
          x2={paddingX + chartWidth}
          y2={midY}
          stroke="rgba(255,255,255,0.12)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />

        {/* Eval curve line */}
        <path
          d={linePath}
          fill="none"
          stroke="rgba(124, 92, 252, 0.7)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />

        {/* Critical moment markers */}
        {criticalDots.map((dot, i) => (
          <circle
            key={`crit-${i}`}
            cx={dot.x}
            cy={dot.y}
            r="4"
            fill={getClassColor(dot.classification)}
            stroke="rgba(0,0,0,0.5)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}

        {/* Current move indicator */}
        {currentPoint && (
          <>
            <line
              x1={currentPoint.x}
              y1={paddingY}
              x2={currentPoint.x}
              y2={height - paddingY}
              stroke="rgba(124, 92, 252, 0.5)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
            <circle
              cx={currentPoint.x}
              cy={currentPoint.y}
              r="5"
              fill="#7c5cfc"
              stroke="#fff"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            />
          </>
        )}
      </svg>

      {/* Legend */}
      <div className={styles.chartLegend}>
        <span className={styles.legendLabel}>
          <span className={styles.legendDot} style={{ background: "#f5f5f5" }} />
          White
        </span>
        <span className={styles.legendLabel}>
          <span className={styles.legendDot} style={{ background: "#333" }} />
          Black
        </span>
        <span className={styles.legendLabel}>
          <span className={styles.legendDot} style={{ background: "#ef5350" }} />
          Blunder
        </span>
        <span className={styles.legendLabel}>
          <span className={styles.legendDot} style={{ background: "#ffb74d" }} />
          Mistake
        </span>
      </div>
    </div>
  );
}

/**
 * Build a filled area path from points to the center line,
 * clipped to either "above" or "below" the midline.
 */
function buildAreaPath(
  points: { x: number; y: number }[],
  midY: number,
  side: "above" | "below"
): string {
  if (points.length === 0) return "";

  const clippedPoints = points.map((p) => ({
    x: p.x,
    y: side === "above" ? Math.min(p.y, midY) : Math.max(p.y, midY),
  }));

  let d = `M${clippedPoints[0].x},${midY}`;
  d += ` L${clippedPoints[0].x},${clippedPoints[0].y}`;
  for (let i = 1; i < clippedPoints.length; i++) {
    d += ` L${clippedPoints[i].x},${clippedPoints[i].y}`;
  }
  d += ` L${clippedPoints[clippedPoints.length - 1].x},${midY}`;
  d += " Z";

  return d;
}

export type { EvalPoint };
