FROM python:3.12-slim

# Install system dependencies
# - gcc and libpq-dev are often needed for compiling asyncpg/psycopg
# - stockfish is required for our analysis pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    stockfish \
    && rm -rf /var/lib/apt/lists/* \
    && if [ -f /usr/games/stockfish ] && [ ! -f /usr/bin/stockfish ]; then ln -s /usr/games/stockfish /usr/bin/stockfish; fi

# Set up working directory
WORKDIR /app

# Ensure output is unbuffered so logs flow directly to stdout
ENV PYTHONUNBUFFERED=1

# We just copy everything here, then use pip install .
# .dockerignore prevents copying .venv or __pycache__
COPY . .

# Install dependencies using pyproject.toml
RUN pip install --no-cache-dir .

# Expose API port
EXPOSE 8000

# Set entrypoint to run migrations
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command to start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
