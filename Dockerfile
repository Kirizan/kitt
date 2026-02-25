FROM python:3.12-slim

# Install system deps for psutil/pynvml compilation and Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev docker.io curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install poetry and project dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-root --without dev --extras web --extras devon

COPY README.md ./
COPY src/ ./src/
COPY configs/ ./configs/
RUN poetry install --only-root --extras web --extras devon

ENTRYPOINT ["poetry", "run", "kitt"]
