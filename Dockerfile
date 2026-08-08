# Use an official Python base image with Debian
FROM python:3.11-slim

# Install system build deps and curl for rustup
RUN apt-get update && \
    apt-get install -y build-essential curl git libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Rust toolchain non-interactively
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy only requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Upgrade pip/setuptools/wheel and install maturin
RUN python -m pip install --upgrade pip setuptools wheel maturin

# Install python deps (this will build pydantic-core if needed)
RUN python -m pip install -r /app/backend/requirements.txt

# Copy the application code
COPY . /app

# Expose port and run with gunicorn (Procfile equivalent)
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "backend.main:app"]
