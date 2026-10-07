# ProofCoin Security Audit Checklist & Threat Analysis

This document details the security posture, threat model, cryptographic mitigations, and pre-mainnet production checklist for the ProofCoin protocol.

---

## 1. Threat Model & Vulnerability Analysis

### 1.1 Double-Spending & UTXO Exhaustion
- **Threat**: An adversary attempts to spend the same UTXO in two distinct transactions or simultaneously in two blocks.
- **Mitigation**:
  1. *Internal tx verification*: Transactions cannot contain duplicate `(prev_txid, vout)` entries (`validate_transaction_basics`).
  2. *Mempool tracking*: The mempool maintains an in-memory reverse lookup `_spent_outpoints[(prev_txid, vout)] -> txid`. Any conflicting transaction is immediately rejected with DoS scoring.
  3. *Stateful ledger application*: The UTXO set deletes spent inputs atomically during block evaluation. If any input is already missing, block application reverts completely.

### 1.2 Integer Overflow & Negative Amount Exploits
- **Threat**: Attackers pass negative numbers or $2^{64}$ values to artificially inflate coin supplies or steal funds (similar to Bitcoin's 2010 integer overflow incident).
- **Mitigation**:
  1. Strict type checking: Every `output.amount` must be a positive integer (`isinstance(out.amount, int)`).
  2. Strict bounds check: `0 < output.amount <= MAX_MONEY` ($2,100,000,000,000,000$ satoshis).
  3. Summation bounds check: `sum(output.amount) <= MAX_MONEY`.

### 1.3 Signature Malleability (Third-Party TxID Modification)
- **Threat**: In classical Bitcoin before Segregated Witness (BIP 141), an observer could modify signature encoding bytes without invalidating the signature, altering the txid and breaking unconfirmed transaction chains.
- **Mitigation**:
  - In ProofCoin, `tx.get_signing_digest()` and `calculate_tx_hash()` compute the hash exclusively over inputs' referenced outpoints `(prev_txid, vout)` and output descriptors. The `signature` is segregated from the txid computation, eliminating third-party malleability vectors.

### 1.4 Solution Hijacking (Front-Running Miner Blocks)
- **Threat**: A node broadcasts a mined block over P2P. A malicious relay peer replaces the coinbase output with their own address and re-broadcasts the block.
- **Mitigation**:
  - The prime candidate origin $p_0$ is deterministically derived from:
    $$\text{SHA-256}(\text{prev\_hash} \parallel \text{miner\_pubkey} \parallel \text{merkle\_root} \parallel \text{nonce})$$
  - Replacing the coinbase address modifies `miner_pubkey` and `merkle_root`, which scrambles the candidate origin $p_0$. The prime chain is no longer valid, causing all nodes on the network to reject the hijacked block.

### 1.5 Timing Attacks & Side-Channel Leaks
- **Threat**: Sub-millisecond timing differentials in cryptographic string or byte comparisons could expose sensitive key or checksum material.
- **Mitigation**:
  - Checksum validation and sensitive byte checks utilize `hmac.compare_digest` for constant-time evaluation.

### 1.6 Network Denial of Service (DoS) & Peer Sybil Flooding
- **Threat**: Flooding nodes with garbage packets, oversized blocks, or massive mempool transactions to crash or stall the daemon.
- **Mitigation**:
  1. *Packet Framing Guard*: Hard 2 MB maximum frame size limit in wire protocol. Packets declaring $> 2\text{MB}$ payload trigger immediate socket close and ban.
  2. *Misbehavior Scoring*: Every peer tracks cumulative penalty points:
     - Invalid block: $+100$ (Immediate 24-hr ban)
     - Duplicate mempool spend: $+40$
     - Rate limit violation: $+20$
     - Threshold: $\ge 100 \implies$ disconnect & IP blacklisting.
  3. *Rate Limiting*: 50 messages/second token bucket per socket connection.

---

## 2. 51% Attack & Selfish Mining Deep Dive

### 51% Majority Attack
- **Vector**: A single mining entity commands $> 50\%$ of prime chain search capacity, allowing them to secretly mine a private branch with higher cumulative difficulty and perform deep reorganizations to reverse finalized payments.
- **Risk Evaluation**:
  - In the early stages of any proof-of-work blockchain, low cumulative network hashrate presents a vulnerability window.
  - Unlike SHA-256 where specialized ASICs are privately developed, Cunningham chain mining is dominated by memory-bandwidth-bound and modular arithmetic operations (sieving), lowering barrier-to-entry disparities between participants.
- **Economic Defenses**:
  - Exchanges and merchant software should enforce a **confirmation depth parameter** ($N_{\text{conf}} \ge 60 \text{ blocks}$) during initial network bootstrapping.

### Selfish Mining (Block Withholding)
- **Vector**: An attacker holding minority share $\alpha < 0.5$ withholds newly discovered blocks, waiting for honest miners to discover a block before publishing their private branch to invalidate honest effort.
- **ProofCoin Characteristics**:
  - Target block interval of $\tau = 60 \text{ seconds}$ ensures network propagation delay $\delta \approx 200\text{ms}$ is orders of magnitude lower than mining time ($\delta / \tau \approx 0.003$).
  - Low orphan rates elevate the selfish mining profitability threshold towards the theoretical $\alpha \approx 33.3\%$ ceiling.

---

## 3. Pre-Mainnet Production Checklist

Before launching a public production mainnet with real economic value, the following components must be implemented and audited:

- [ ] **Native C/Rust Mining Core**: Implement Cunningham sieve and Miller-Rabin routines in Rust (or C++ via GMP/FLINT) with SIMD / AVX-512 extensions for optimal sieving efficiency.
- [ ] **Fractional Difficulty Mechanism**: Implement Primecoin-style Fermat remainder formula for smooth continuously variable difficulty target adjustments.
- [ ] **DNS Seed Nodes & Static Bootstrap Peer List**: Configure resilient multi-region DNS seeds and fallback static IPs to prevent initial network partitioning.
- [ ] **Tor & I2P Onion Routing**: Native SOCKS5 proxy support to shield miners and full nodes from network-layer IP deanonymization.
- [ ] **External Security Audit**: Comprehensive code and cryptographic audit by independent third-party blockchain auditing firms (e.g., Trail of Bits, OpenZeppelin).
- [ ] **Formal Verification of State Transitions**: TLA+ or Coq specification proving deadlock-freedom and invariant preservation across concurrent reorg scenarios.
- [ ] **Coinbase Maturity Rule**: Enforce standard 100-block lockup period before newly mined coinbase outputs can be spent, preventing reorg-induced cascade invalidations.
