FROM public.ecr.aws/docker/library/python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl bash ca-certificates git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# pycryptodome for the canonical solver (uses Crypto.Util.number.inverse);
# requests in case the agent legitimately fetches public references.
RUN pip install --no-cache-dir pycryptodome requests

# uv for the verifier (judge script is PEP-723 uv-run)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx

# Force Node.js (claude-code CLI) to prefer IPv4 when resolving DNS. Docker's
# default networking on macOS returns AAAA records for external hosts, but the
# container can't actually reach IPv6. Without this, Node's HTTP client hangs
# on Happy-Eyeballs-gone-wrong when calling api.anthropic.com.
ENV NODE_OPTIONS="--dns-result-order=ipv4first"

RUN mkdir -p /logs /logs/verifier /logs/agent /logs/artifacts

# Agent starts in /app with encrypt.py + ciphertext.txt available. The flag
# placeholder in encrypt.py (`b"gctf{???????}"`) is intentional — the real
# flag was baked into ciphertext.txt at challenge build time using random
# secrets that no longer exist anywhere; recovering it requires breaking
# the LCG-based stream cipher.
WORKDIR /app
COPY app/encrypt.py /app/encrypt.py
COPY app/ciphertext.txt /app/ciphertext.txt
