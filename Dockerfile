# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies
# ffmpeg: required for audio processing (Whisper fallback)
# nodejs: required for pytubefix po_token generation
# git: for some dependency installations if needed
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    git \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser with dependencies
RUN playwright install chromium --with-deps

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 8000 for the FastAPI app
EXPOSE 8000

# Run the application (Shell form to allow variable expansion)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
