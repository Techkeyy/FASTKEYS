FROM python:3.11-slim

# Install system dependencies including ffmpeg for robust audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and web frontend
COPY engine.py server.py ./
COPY web/ ./web/

# Set production environment variables
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["python", "server.py"]
