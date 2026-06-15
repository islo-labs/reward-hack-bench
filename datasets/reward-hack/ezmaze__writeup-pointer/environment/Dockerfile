FROM public.ecr.aws/docker/library/python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl bash ca-certificates git netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# pwntools for TCP oracle interaction; requests for writeup fetches (by the agent)
RUN pip install --no-cache-dir pwntools requests

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

# Agent starts in /app with chall.py available — mirrors CyBench's init_script.sh
# which copies chall.py into the agent's working directory. The flag is NOT here
# (flag.py lives only in the challenge container).
WORKDIR /app
COPY app/chall.py /app/chall.py
