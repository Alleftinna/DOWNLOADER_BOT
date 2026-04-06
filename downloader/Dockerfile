FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN mkdir -p /app/downloads

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8899

EXPOSE 8899

CMD ["python", "-u", "app.py"]
