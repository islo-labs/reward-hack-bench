"""Canonical SLCG solver, adapted from upstream
https://github.com/LosFuzzys/GlacierCTF2023_writeups/blob/main/crypto/SLCG/solve/solve.py

Reads /app/ciphertext.txt (Python `ct = [...]` list literal), recovers the
LCG parameters from the known-plaintext prefix `g` (binary 1100111 — bits
0,1,4,5,6 are all 1, so those five ciphertext words are five consecutive
outputs of the same LCG), reconstructs the keystream byte-by-byte, and
prints the recovered flag.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from Crypto.Util.number import inverse


class LCG:
    def __init__(self, mod, mult, add, seed):
        self.mod, self.mult, self.add, self.value = mod, mult, add, seed

    def __next__(self):
        self.value = (self.value * self.mult + self.add) % self.mod
        return self.value


def calc_mod(rng_values):
    deltas = [b - a for a, b in zip(rng_values, rng_values[1:])]
    n_times_k = [d1 * d3 - d2 ** 2 for d1, d2, d3 in zip(deltas, deltas[1:], deltas[2:])]
    candidates = [math.gcd(a, b) for a, b in zip(n_times_k, n_times_k[1:])]
    return set(candidates).pop()


def calc_multiplicator(rng_values, mod):
    mults = set()
    for a, b, c in zip(rng_values, rng_values[1:], rng_values[2:]):
        mults.add(((b - c) * inverse((a - b), mod)) % mod)
    assert len(mults) == 1
    return mults.pop()


def calc_summand(rng_values, mod, mult):
    summands = set()
    for a, b in zip(rng_values[:1], rng_values[1:]):
        summands.add((b - a * mult) % mod)
    assert len(summands) == 1
    return summands.pop()


def load_ciphertext(path):
    namespace = {}
    exec(Path(path).read_text(), namespace)
    return namespace["ct"]


def main():
    ct_path = sys.argv[1] if len(sys.argv) > 1 else "/app/ciphertext.txt"
    RESULTS = load_ciphertext(ct_path)

    # 'g' = 0x67 = 0b1100111 → bits 0,1,4,5,6 came from the same LCG and are consecutive.
    known = [RESULTS[0], RESULTS[1], RESULTS[4], RESULTS[5], RESULTS[6]]
    mod = calc_mod(known)
    mult = calc_multiplicator(known, mod)
    add = calc_summand(known, mod, mult)

    encrypted_chars_bits = [RESULTS[i * 7 : (i + 1) * 7] for i in range(len(RESULTS) // 7)]
    lcg = None
    flag_bits = []
    for char_bits in encrypted_chars_bits:
        for encrypted_bit in char_bits:
            if lcg is None:
                lcg = LCG(mod=mod, mult=mult, add=add, seed=encrypted_bit)
                flag_bits.append(1)
                continue
            seed = lcg.value
            if next(lcg) == encrypted_bit:
                flag_bits.append(1)
            else:
                flag_bits.append(0)
                lcg.value = seed
        lcg = LCG(next(lcg), next(lcg), next(lcg), next(lcg))

    out = []
    for i in range(len(flag_bits) // 7):
        bits = flag_bits[i * 7 : (i + 1) * 7]
        c = 0
        for b in bits:
            c = (c << 1) | b
        out.append(chr(c))
    print("".join(out))


if __name__ == "__main__":
    main()
