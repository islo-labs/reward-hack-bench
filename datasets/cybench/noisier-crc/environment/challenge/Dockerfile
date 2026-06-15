FROM public.ecr.aws/docker/library/python:3.11-slim-bookworm

# Upstream Dockerfile used python:3.9-slim-buster (Debian 10), which is now
# end-of-life and the apt repositories return 404. Bumped to bookworm and
# python 3.11; chall.py is pure Python over pycryptodome so the runtime move
# is safe. lib32z1 (in upstream image for legacy 32-bit binaries) dropped —
# this challenge ships no native binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends xinetd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pycryptodome networkx

RUN useradd -m user
COPY app/chall.py app/flag.py /home/user/
COPY xinetd /etc/xinetd.d/user
RUN chown user:user /home/user/flag.py \
    && chmod 400 /home/user/flag.py \
    && chown user:user /home/user/chall.py \
    && chmod 500 /home/user/chall.py

EXPOSE 9999
CMD ["/usr/sbin/xinetd", "-dontfork"]
