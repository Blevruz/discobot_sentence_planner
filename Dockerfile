# Use a base image with Python 3.11 and CUDA support
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

# Set environment variables
ENV PYTHON_VERSION=3.11
ENV DEBIAN_FRONTEND=noninteractive
ENV RUST_VERSION=1.81.0
ENV UV_VERSION=0.4.4

# Install system dependencies including Rust
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    curl \
    unzip \
    gcc \
    g++ \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain $RUST_VERSION
ENV PATH="/root/.cargo/bin:${PATH}"

# Install uv
RUN curl -LsSf https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-installer.sh | sh

# Set Python as the default python command
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Set working directory
WORKDIR /app

# Copy requirements.txt
COPY requirements.txt .

# Install dependencies using uv
RUN uv venv venv -p 3.11 && \
    . venv/bin/activate && \
    uv pip install -r requirements.txt

# Copy the rest of the project files
COPY . .

# Default entrypoint
ENTRYPOINT ["/bin/sh", "run.sh"]
