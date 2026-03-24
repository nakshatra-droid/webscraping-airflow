FROM apache/airflow:3.1.7

USER root

RUN apt-get update && apt-get install -y \
    curl \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxfixes3 \
    libxrender1 \
    libxshmfence1 \
    libdrm2 \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libu2f-udev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir \
    torch==2.2.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    "asyncpg>=0.31.0", \
    "ollama>=0.6.1", \
    "pgvector>=0.4.2", \
    "psycopg2-binary>=2.9.11", \
    "python-dotenv>=1.2.2", \
    "sqlalchemy>=2.0.48", \
    "tqdm>=4.67.1", \
    "torch>=2.2.2,<2.3.0", \
    "sentence-transformers>=2.7.0,<3.0.0", \
    "numpy<2", \
    "playwright>=1.58.0", \
    "playwright-stealth>=2.0.2"

# Install browser + dependencies
RUN playwright install chromium