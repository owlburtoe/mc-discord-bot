# --- Build Stage ---
FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a multi-stage build
ENV UV_LINK_MODE=copy

# Install dependencies
COPY pyproject.toml .
# We don't need a virtual environment in the builder stage since we are copying .local out
RUN /uv/bin/uv pip install --no-cache --system --target /root/.local -r pyproject.toml

# --- Final Stage ---
FROM python:3.11-slim

# Prevent Python from buffering logs
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/botuser/.local/bin:${PATH}"

WORKDIR /app

# Create a non-privileged user (use a fixed UID for better predictability)
RUN useradd -m -u 1000 botuser
USER botuser

# Copy installed packages from builder
COPY --from=builder --chown=botuser:botuser /root/.local /home/botuser/.local
COPY --chown=botuser:botuser . .

CMD ["python", "bot.py"]
