FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN wget -qO- https://astral.sh/uv/install.sh | sh

# Add uv to the PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN uv venv
RUN uv pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files
COPY . .

# Create data directory
RUN mkdir -p data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run your bot
CMD ["uv", "run", "main.py"]
