# Streamlit app container for AWS ECS Fargate deployment.
FROM python:3.11-slim

# System libraries commonly needed by geopandas/shapely/pyproj/folium stacks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libexpat1 \
        libgl1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code and data needed at runtime.
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY assets/ ./assets/
# Career evidence viewer reads these output CSV/MD files at runtime.
COPY outputs/career/ ./outputs/career/

EXPOSE 8501

# ALB health check target: Streamlit exposes /_stcore/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
