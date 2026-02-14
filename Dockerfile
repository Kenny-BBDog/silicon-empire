FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy everything first (hatchling needs source to generate metadata)
COPY . .

# Python deps (prod only, no dev extras)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
