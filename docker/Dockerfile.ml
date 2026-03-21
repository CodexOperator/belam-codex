# ============================================================
# Belam ML Layer — extends belam-core with PyTorch stack
# ARM64 / aarch64 — PyTorch wheels available for linux/arm64
# ============================================================
# Build separately (slow — ~6GB image):
#   docker compose --profile ml build
# ============================================================

FROM belam-core:latest

USER root

# ── PyTorch for ARM64 ────────────────────────────────────────
# ARM64 wheels are on PyPI (CPU-only; no CUDA on Oracle ARM)
COPY requirements-ml.txt /tmp/requirements-ml.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-ml.txt \
    && rm /tmp/requirements-ml.txt

USER ubuntu

# Default to a bash shell for interactive use / one-off runs
CMD ["bash"]
