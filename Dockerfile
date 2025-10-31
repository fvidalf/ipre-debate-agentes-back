# Build stage
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ gcc make \
    libgomp1 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ gcc make \
    libxml2-dev libxslt-dev libjpeg-dev zlib1g-dev libpng-dev \
    libgomp1 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*


# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# HuggingFace cache inside the container (you can mount a volume here later)
ENV HF_HOME=/app/hf_cache
RUN mkdir -p ${HF_HOME}

# --- Copy app code ---
COPY ./app ./app
COPY ./scripts ./scripts
COPY alembic.ini .
COPY .env .
COPY agents-search-engine-1c7071385018.json .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
