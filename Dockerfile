# Use a lightweight official Python runtime base image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the active working directory inside the container space
WORKDIR /app

# Install system dependencies needed for compiling certain Python extensions
# Adding wget and nano for in-container tweaks on the fly
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    nano \ 
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements list first to leverage Docker layer caching
COPY requirements.txt .

# Install required Python packages cleanly
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code scripts into the container
COPY . .

# Expose the default network port used by Gradio server instances
EXPOSE 7435

# Force Gradio to bind to all network interfaces inside the Docker network layer
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT=7435

# Run the script as the container initialization entry point execution command
CMD ["python", "janet.py"]
