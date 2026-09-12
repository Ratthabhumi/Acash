# ACASH Paper Service — Containerization Artifact (E3.6 / WS1)
#
# DESIGN REFERENCE: E3.6-DESIGN.md §5 (D1.1), §7 (D7.1/D7.2),
#   §10 (D10.2), §11 (D4.1), §19 (D19.1/D19.2).
#
# GOVERNANCE:
# - This Dockerfile is a BUILD ARTIFACT for the ACASH paper container.
# - It is NOT deployed here: creation of the HomeLab compose entry, the
#   interlock wiring, secure-scrape association, and container start are
#   later HomeLab-side stages gated by the deployment rule, AFTER local
#   ACASH-side validation gates pass.
# - Non-root paper UID 10001:10001 (O6 census-guarded decision).
# - No privileged access, no Docker socket, no NEW_PRIVS equivalents.
# - TZ normalized to UTC (D4.1). No published host ports (D19.1).
#
# Build chain bookkeeping (D7.2): the mapping git commit -> image digest is
# recorded as DATA (in the ACASH repo or the window manifest authoring step),
# so RUNTIME PROVENANCE can be re-asserted later. CI builds this image from
# the ACASH repo at a known commit; the digest is recorded at build time.

# PROVENANCE NOTE (D7.2): Base image digest pinning is
# REQUIRED BEFORE PRODUCTION-LIKE STAGING.
# In production-like staging, PYTHON_BASE_IMAGE must resolve to an immutable
# digest (e.g. python:3.13-slim@sha256:...). Do not fabricate or guess a digest.
ARG PYTHON_BASE_IMAGE=python@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
FROM ${PYTHON_BASE_IMAGE}

# One persistent mount root (D10.3): /data/docker/acash owns windows/, sessions/,
# logs/, review/ as logical subdirectories. The engine receives
# --storage /data/docker/acash/sessions — a subdirectory, not a separate mount.
ENV ACASH_STORAGE_ROOT=/data/docker/acash
ENV TZ=UTC
ENV PYTHONPATH=/opt/acash/src
# Non-root paper UID (D10.2 / O6): fixed 10001:10001, census-guarded.
RUN groupadd --gid 10001 paper && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin paper && \
    install -d -o paper -g paper /data/docker/acash/windows \
                              /data/docker/acash/sessions \
                              /data/docker/acash/logs \
                              /data/docker/acash/review

WORKDIR /opt/acash

# Install dependencies first for layer cache efficiency. Digest-pinned base
# image + pinned wheelhouse remain a build-time concern; runtime never checks
# the network.
COPY --chown=paper:paper pyproject.toml uv.lock ./
COPY --chown=paper:paper README.md ./README.md

# Build context is the ACASH repo root; application source is copied below.
COPY --chown=paper:paper src/ ./src/

RUN pip install --no-cache-dir .

# Paper service runs as the unprivileged paper UID only (no new privileges).
USER paper:paper

# The engine CLI is the process entrypoint (python -m acash.paper).
ENTRYPOINT ["python", "-m", "acash.paper"]
CMD ["--help"]

# HEALTHCHECK is left to the deployment stage (cAdvisor/VM observe the
# /metrics endpoint, WS9); no privileged ping is used.
