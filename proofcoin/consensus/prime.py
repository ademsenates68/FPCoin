"""
ProofCoin Primality Testing Module.

Implements Miller-Rabin probabilistic & deterministic primality verification.
Includes an initial small-prime trial division filter for ultra-fast rejection
of composite candidates before expensive modular exponentiations.
"""

import random

# First 70 prime numbers for rapid pre-sieve trial division
SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
    331, 337, 347, 349
]

# Proven deterministic base set for integers < 3.317 * 10^24
DETERMINISTIC_BASES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]


def miller_rabin(n: int, rounds: int = 32) -> bool:
    """
    Miller-Rabin Primality Test.
    
    Decomposes n - 1 = 2^s * d where d is odd.
    Tests witness base a:
      a^d = 1 (mod n) or a^(2^r * d) = -1 (mod n) for some 0 <= r < s.
      
    For 64-bit and 80-bit integers, tests using deterministic bases.
    For larger arbitrary integers, tests using random bases up to 'rounds' iterations.
    Error probability: <= 4^(-rounds) (for rounds=32: < 5.42e-20).
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    # Rapid small prime check & sieve
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    # Decompose n - 1 into 2^s * d
    s = 0
    d = n - 1
    while d % 2 == 0:
        s += 1
        d //= 2

    # Choose testing bases
    if n < 3_317_044_064_679_887_385_961_981:
        bases = [b for b in DETERMINISTIC_BASES if b < n]
    else:
        # Cryptographic security rounds
        rand_bases = set()
        rng = random.Random(n)  # Deterministic seed per candidate for consistency
        while len(rand_bases) < rounds:
            rand_bases.add(rng.randint(2, n - 2))
        bases = list(rand_bases)

    for a in bases:
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue

        composite = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break

        if composite:
            return False

    return True


def is_prime(n: int) -> bool:
    """Convenience alias for Miller-Rabin primality check."""
    return miller_rabin(n)
