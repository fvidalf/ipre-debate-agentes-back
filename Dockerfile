FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# OpenMP + certs (needed by numpy/sklearn) and a tiny toolbelt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# HuggingFace cache inside the container (you can mount a volume here later)
ENV HF_HOME=/app/hf_cache
RUN mkdir -p ${HF_HOME}

# --- Copy app code ---
COPY ./app ./app
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
