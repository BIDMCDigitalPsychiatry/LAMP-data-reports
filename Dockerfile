#------------------------------------------------------------------------------
# Builder
#------------------------------------------------------------------------------

FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

RUN apt-get update && apt-get install -y git clang

# Use specific path for python install so it can be copied to the Runtime Image
ENV UV_PYTHON_INSTALL_DIR=/python

# Do the work now to compile .py to .pyc (faster container start times)
ENV UV_COMPILE_BYTECODE=1

# Ensure our packages are copied into the virtual environment rather than mearly
# linking to the files in the global cache. Important for coping app into the
# Runtime Image.
ENV UV_LINK_MODE=copy

# Only use python installations provided by uv
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.12

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

#------------------------------------------------------------------------------
# Runtime Image
#------------------------------------------------------------------------------

FROM debian:bookworm-slim

# Copy uv's python
COPY --from=builder --chown=python:python /python /python

# Copy the application
COPY --from=builder --chown=app:app /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

CMD [ "/bin/bash", "-c", "gunicorn wsgi:app -b 0.0.0.0:$PORT" ]
