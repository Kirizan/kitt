FROM python:3.12-slim

# System deps for Docker CLI (agent manages containers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev docker.io curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files first (for layer caching)
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --without dev -E web

# Copy source
COPY src/ ./src/
COPY configs/ ./configs/
RUN poetry install --only-root

ENV KITT_AUTH_TOKEN=""
ENV KITT_SERVER_URL=""

EXPOSE 8090

ENTRYPOINT ["kitt", "agent", "start"]
CMD ["--foreground", "--insecure"]
