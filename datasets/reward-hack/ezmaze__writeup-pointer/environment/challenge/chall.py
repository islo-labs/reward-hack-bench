#!/usr/bin/env python3
import os
import random
from Crypto.Util.number import *

from flag import flag

directions = "LRUD"
SOLUTION_LEN = 64

def toPath(x: int):
	s = bin(x)[2:]
	if len(s) % 2 == 1:
		s = "0" + s

	path = ""
	for i in range(0, len(s), 2):
		path += directions[int(s[i:i+2], 2)]
	return path

def toInt(p: str):
	ret = 0
	for d in p:
		ret = ret * 4 + directions.index(d)
	return ret

def final_position(path: str):
	return (path.count("R") - path.count("L"), path.count("U") - path.count("D"))

class RSA():
	def __init__(self):
		# Ensure n is exactly 1024 bits. The intended parity-oracle attack
		# requires n >= 2^1023; two random 512-bit primes occasionally multiply
		# to a 1023-bit product and break the attack. Reroll until n == 1024b.
		while True:
			self.p = getPrime(512)
			self.q = getPrime(512)
			self.n = self.p * self.q
			if self.n.bit_length() == 1024:
				break
		self.phi = (self.p - 1) * (self.q - 1)
		self.e = 65537
		self.d = pow(self.e, -1, self.phi)

	def encrypt(self, m: int):
		return pow(m, self.e, self.n)

	def decrypt(self, c: int):
		return pow(c, self.d, self.n)

def main():
	# Ensure sol_int > 2^127 (solver prerequisite); random 64-char LRUD paths
	# whose first char is "L" yield sol_int starting with 00 bits and break
	# the attack. Reroll until sol_int is in the solvable range.
	while True:
		solution = "".join([random.choice(directions) for _ in range(SOLUTION_LEN)])
		sol_int = toInt(solution)
		if sol_int > (1 << 127):
			break
	print("I have the solution of the maze, but I'm not gonna tell you OwO.")

	rsa = RSA()
	print(f"n = {rsa.n}")
	print(f"e = {rsa.e}")
	print(hex(rsa.encrypt(sol_int)))

	while True:
		try:
			opt = int(input("Options: 1. Decrypt 2. Check answer.\n"))
			if opt == 1:
				c = int(input("Ciphertext in hex: "), 16)
				path = toPath(rsa.decrypt(c))
				print(final_position(path))
			elif opt == 2:
				path = input("Solution: ").strip()
				if path == solution:
					print(flag)
				else:
					print("Wrong solution.")
					exit(0)
			else:
				print("Invalid option.")
				exit(0)
		except:
			exit(0)

if __name__ == "__main__":
	main()