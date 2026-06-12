import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chessian.AI — AI-Powered Chess Improvement",
  description:
    "Analyze your chess games, identify recurring weaknesses, and get a personalized improvement plan powered by AI. Import from Chess.com and Lichess.",
  keywords: [
    "chess",
    "AI",
    "chess analysis",
    "chess improvement",
    "chess coach",
    "stockfish",
    "chess.com",
    "lichess",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div id="app-root">{children}</div>
      </body>
    </html>
  );
}
