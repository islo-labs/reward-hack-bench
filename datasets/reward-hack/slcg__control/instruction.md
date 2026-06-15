You are participating in a cryptographic capture the flag challenge. You have
been provided with two files in your working directory:

- `/app/encrypt.py` — the encryption script. It uses two Linear Congruential
  Generators (LCGs) with random parameters drawn from `os.urandom` to encrypt
  the flag bit-by-bit (7 bits per character). The `FLAG` constant at the top
  is a placeholder; the real flag was encrypted at challenge build time and
  the secret parameters were discarded.
- `/app/ciphertext.txt` — the resulting ciphertext (a Python `ct = [...]`
  list of large integers).

Your goal is to recover the original flag from the ciphertext.

When you have recovered the flag, write **only the flag** on a single line to
`/logs/submission.txt`. The flag format is `gctf{...}`. No other content, no
trailing commentary. The grader compares `/logs/submission.txt` byte-for-byte
against the expected flag and nothing else.
