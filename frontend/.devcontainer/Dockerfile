FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

ARG DEBIAN_FRONTEND=noninteractive

# System dependencies for the docs pipeline (lxml) and general tooling.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        jq \
        libxml2-dev \
        libxslt1-dev \
        make \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*

# The base image already ships a non-root "vscode" user (UID 1000).
# Keep the default user; the devcontainer runs with Podman's keep-id mapping.
USER vscode
WORKDIR /workspaces/pyjourney

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NEXT_TELEMETRY_DISABLED=1
