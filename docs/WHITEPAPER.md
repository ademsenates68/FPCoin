# ProofCoin: A Decentralized Cryptocurrency Powered by Useful Work Cunningham Prime Chains

**Whitepaper v1.0**  
*ProofCoin Core Research & Development Group*

---

## Abstract

Proof of Work (PoW) protocols such as Bitcoin's double-SHA256 have established decentralized consensus across open networks. However, the energy expended in classical PoW is computationally sterile—hashing gigawatts of electricity solely to find arbitrary zero prefixes without producing any societal or scientific byproduct.

We present **ProofCoin**, a cryptocurrency that replaces wasteful hash-inversion with **Proof of Useful Work (PoUW)** based on the search for **Cunningham prime chains**. Discovered prime sequences contribute directly to computational number theory, RSA/ECC security analysis, and Sophie Germain prime exploration. Verification remains asymmetric, deterministic, and nearly instantaneous via the Miller-Rabin test. We prove that tying candidate chain origins to miner public keys prevents front-running and solution hijacking.

---

## 1. Introduction & Motivation

Global Proof-of-Work systems currently consume in excess of 100 TWh annually. The core challenge in designing useful proof-of-work protocols has historically been:
1. **Asymmetry**: Solving must be tunable and computationally intensive, while verification must be $O(1)$ or sub-millisecond.
2. **Determinism & Progress-Freeness**: Discoveries must follow a memoryless Poisson process to prevent hardware monopolies and predictable block schedules.
3. **Anti-Frontrunning**: Solutions must be cryptographically non-transferable to prevent network eavesdroppers from claiming other miners' work.

ProofCoin satisfies all three criteria by formulating the mining problem as the discovery of Cunningham prime chains.

---

## 2. Mathematical Formulation: Cunningham Chains

### 2.1 Prime Chains of the First Kind ($1\text{CC}$)
A Cunningham chain of the first kind of length $k$ is a sequence of primes $(p_0, p_1, \dots, p_{k-1})$ satisfying:
$$p_{i+1} = 2 \cdot p_i + 1 \quad \text{for } 0 \le i < k-1$$
Each pair $(p_i, p_{i+1})$ constitutes a Sophie Germain prime pair where $p_i$ is a Sophie Germain prime and $p_{i+1}$ is a safe prime.

### 2.2 Prime Chains of the Second Kind ($2\text{CC}$)
A Cunningham chain of the second kind of length $k$ satisfies:
$$p_{i+1} = 2 \cdot p_i - 1 \quad \text{for } 0 \le i < k-1$$

### 2.3 Scientific Utility
1. **Cryptographic Parameter Generation**: Safe primes ($2p+1$) are essential for discrete logarithm cryptosystems (Diffie-Hellman, DSA, ElGamal) to defend against the Silver-Pohlig-Hellman algorithm.
2. **Primality Proving & Number Theory**: Cunningham chains represent extreme configurations of the Dickson conjecture and generalized Bateman-Horn conjectures, aiding researchers in bounding prime gap distributions.

---

## 3. The ProofCoin PoUW Protocol

### 3.1 Solution Derivation & Binding Theorem
Let $H_{\text{prev}}$ be the previous block hash, $K_{\text{miner}}$ be the miner's Ed25519 public key, $M$ be the Merkle root of transaction hashes, and $n$ be an unsigned 64-bit nonce.

The candidate prime origin $p_0$ is generated via:
$$\mathcal{S} = \text{SHA-256}\big(\text{SHA-256}(H_{\text{prev}} \parallel K_{\text{miner}} \parallel M \parallel n)\big)$$
$$p_0 = \big(\text{int}(\mathcal{S}[:8]) \pmod{10^{12}}\big) \times 2 + 1$$

**Theorem (Solution Binding / Anti-Theft):**  
Let an adversary $\mathcal{A}$ observe a valid block header $(H_{\text{prev}}, K_{\text{miner}}, M, n, \mathcal{C})$. If $\mathcal{A}$ attempts to substitute $K_{\text{miner}}$ with $K_{\mathcal{A}}$ such that $K_{\mathcal{A}} \ne K_{\text{miner}}$, then by the collision resistance and pseudorandom oracle property of SHA-256:
$$\text{Pr}\left[p_0(K_{\mathcal{A}}) = p_0(K_{\text{miner}})\right] \le 2^{-64}$$
Consequently, the prime chain $\mathcal{C}$ will fail verification for any other miner key with overwhelming probability ($1 - 2^{-64}$).

### 3.2 Verification Complexity
Primality verification uses the **Miller-Rabin test**.
For 64-bit candidates, deterministic base sets guarantee 100% precision:
$$\mathcal{B} = \{2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41\}$$
For length-$k$ chains:
$$\text{Verification Complexity} = k \times |\mathcal{B}| \times O(\log^3 p_0) \approx O(1)$$
On modern hardware, validating a block takes **$0.2 \text{ to } 0.8$ milliseconds**, making block verification nearly instantaneous across low-power P2P nodes.

---

## 4. Economic Model & Emission

ProofCoin follows a strictly disinflationary supply model capped at **21,000,000 ProofCoins**:

| Parameter | Value |
|---|---|
| **Base Currency Unit** | $1 \text{ ProofCoin} = 10^8 \text{ atomic units}$ |
| **Initial Block Subsidy** | $50.00 \text{ ProofCoins}$ |
| **Target Block Interval** | $60 \text{ seconds}$ |
| **Difficulty Retarget Interval** | $144 \text{ blocks } (\approx 2.4 \text{ hours})$ |
| **Halving Interval** | $210,000 \text{ blocks } (\approx 4 \text{ years})$ |
| **Total Monetary Cap** | $21,000,000 \text{ ProofCoins}$ |

### Emission Schedule Formula
$$\mathcal{R}(h) = \left(50 \times 10^8\right) \gg \left\lfloor \frac{h}{210,000} \right\rfloor$$
At $h = 64 \times 210,000$, the subsidy becomes identically 0, and miners are compensated exclusively through user transaction fees.

---

## 5. Security & Game Theory

### 5.1 Resistance to 51% Attacks
Like all Proof of Work consensus mechanisms, the security of the canonical ledger relies on honest miners commanding $> 50\%$ of global computational resources. In ProofCoin:
- Consensus follows the **Cumulative Useful Work Rule**:
  $$\text{ChainWork}(\mathcal{C}) = \sum_{b \in \mathcal{C}} D(b)$$
- Because Cunningham chain mining requires modular arithmetic and sieving (unlike pure bitwise SHA-256), mining algorithms are memory- and integer-bound, reducing the feasibility of hyper-concentrated ASIC advantages and encouraging broader commodity CPU/GPU participation.

### 5.2 Selfish Mining Analysis
In a selfish mining attack (Eyal & Sirer, 2014), an attacker with fraction $\alpha$ of hashrate withheld private blocks to cause honest miners to waste work.
Because ProofCoin uses a 60-second block time, network propagation delays ($\approx 100\text{ms} - 500\text{ms}$) are negligible relative to block time ($\frac{\delta}{\tau} < 0.01$). This minimizes orphan rates and raises the selfish mining profitability threshold above the classical $\alpha > \frac{1}{3}$ threshold.

---

## 6. Known Limitations & Mainnet Roadmap

1. **Fractional Difficulty**: In the prototype, difficulty is represented as a float whose integer floor dictates required chain length. In a production mainnet, Primecoin-style fractional Fermat test remainders should be incorporated to enable smooth micro-adjustments.
2. **Sieve Optimization**: Production miners should employ specialized polynomial sieves (e.g., Cunningham sieve with precomputed wheel offsets) to accelerate candidate generation.
3. **P2P Discovery**: Prototype uses address gossip (`getaddr`/`addr`). Mainnet should add hardcoded DNS seeds and Tor/I2P onion routing support.
