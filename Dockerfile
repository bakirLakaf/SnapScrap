FROM python:3.9-slim

# Install system dependencies (ffmpeg is required for video merging)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

# Environment Variables
ENV FLASK_APP=webapp.app:app
ENV FLASK_ENV=production

# Expose port (Railway passes $PORT dynamically)
EXPOSE 5000

# Start Gunicorn server
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 webapp.app:app
