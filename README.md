# Chessian.AI

An AI-powered platform that analyzes your chess games, identifies recurring weaknesses, and generates a personalized improvement plan. Built around Stockfish analysis combined with LLM-generated coaching explanations.

## What it does

- Imports games from Chess.com and Lichess
- Runs engine analysis and classifies every move (blunder, mistake, inaccuracy, best)
- Breaks down accuracy by opening, middlegame, and endgame
- Builds an opening repertoire profile across all your games
- Generates plain language explanations for critical moments using an LLM
- Recommends puzzles targeting your specific tactical blindspots

## Tech stack

- Frontend - Next.js, chessground
- Backend - FastAPI
- Engine - Stockfish
- Database - PostgreSQL, Qdrant for embeddings
- LLM - Claude or Groq API

## Project structure
.
├── frontend/
├── backend/
├── docs/
│   └── feature-research.md
└── README.md

## Roadmap

Full feature research and build order is in `docs/feature-research.md`. Current MVP focus

- Game import and board interface
- Engine evaluation and move classification
- Phase separated accuracy
- Opening repertoire profiler
- Natural language move explanations
- Puzzle recommendations

## Status

Early development. Built as a graduation project at Helwan University.

## License

MIT. See LICENSE.
