FROM public.ecr.aws/docker/library/python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends xinetd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir mmh3

RUN useradd -m user
COPY app/chall.py app/flag.py /home/user/
COPY xinetd /etc/xinetd.d/user
RUN chown user:user /home/user/flag.py \
    && chmod 400 /home/user/flag.py \
    && chown user:user /home/user/chall.py \
    && chmod 500 /home/user/chall.py

EXPOSE 9999
CMD ["/usr/sbin/xinetd", "-dontfork"]
