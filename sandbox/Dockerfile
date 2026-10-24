# Hardened image for the email-agent prompt-injection experiments.
# Fixes over the original "DOCKER SETUP.docx":
#   * code is owned by root and read-only to the runtime user (the chmod happens before USER)
#   * no API keys; the model is reached only via the llm-gateway service
#   * no shell login for the runtime user
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data

RUN groupadd -g 10001 appgroup \
 && useradd -u 10001 -g appgroup -M -d /nonexistent -s /usr/sbin/nologin appuser

WORKDIR /opt/experiment

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src

# Root-owned, world-readable, not writable by appuser. Mount points for data.
RUN chown -R root:root /opt/experiment \
 && chmod -R u=rwX,go=rX /opt/experiment \
 && mkdir -p /data/benchmark /data/results \
 && chown appuser:appgroup /data/results

USER 10001:10001

CMD ["python", "src/run_eval.py", "--smoke"]
