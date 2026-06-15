FROM public.ecr.aws/docker/library/python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl bash ca-certificates git netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# pwntools for TCP oracle interaction; mmh3 for the bloom-filter
# manipulation; requests for writeup fetches.
RUN pip install --no-cache-dir pwntools mmh3 requests

# uv for the verifier (judge script is PEP-723 uv-run)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx

ENV NODE_OPTIONS="--dns-result-order=ipv4first"

RUN mkdir -p /logs /logs/verifier /logs/agent /logs/artifacts

WORKDIR /app
COPY app/chall.py /app/chall.py
