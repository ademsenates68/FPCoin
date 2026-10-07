# ProofCoin (PoUW) Prototype

> **Production-Grade Proof of Useful Work (PoUW) Cryptocurrency in Python 3.11**  
> Harnessing computational power for prime number research via Cunningham Chains.

---

## 🌟 Overview

ProofCoin is a decentralized, peer-to-peer cryptocurrency prototype engineered from first principles. Unlike conventional hash-inversion Proof of Work (e.g., Bitcoin SHA-256) where quintillions of computations are discarded as thermodynamic waste, ProofCoin utilizes **Proof of Useful Work (PoUW)**:
- **Consensus**: Search for **Cunningham prime chains** of the first ($p_{i+1} = 2p_i + 1$) and second ($p_{i+1} = 2p_i - 1$) kinds.
- **Scientific Utility**: Contributes to number theory, Sophie Germain prime discovery, and cryptographic parameter validation.
- **Verification Speed**: Millisecond verification via deterministic & probabilistic **Miller-Rabin primality testing**.
- **Anti-Theft Binding**: The candidate origin is cryptographically bound to `prev_hash`, `miner_pubkey`, `merkle_root`, and `nonce`. An adversary cannot front-run or reuse a discovered prime chain by substituting their own address.
- **UTXO Model**: Bitcoin-style unspent transaction output ledger with replay protection and segregated Ed25519 signatures.
- **Emission**: 50 ProofCoin initial block subsidy, halved every 210,000 blocks, capped at **21,000,000 ProofCoins**.
- **P2P Networking**: Asynchronous `asyncio` TCP mesh with handshake, inventory gossip, chain synchronization, and automated misbehavior scoring/banning.
- **Persistence**: High-performance SQLite with Write-Ahead Logging (WAL) and atomic transactions.
- **Wallet**: Ed25519 keys, Base58Check checksummed addresses (`P...`), and encrypted local keystore using `scrypt + AES-256-GCM`.

---

## 📂 Project Directory Structure

```
.
├── proofcoin/
│   ├── __init__.py              # Package entrypoint
│   ├── cli.py                   # Full command-line interface
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── keys.py              # Ed25519 key generation, sign, verify (RFC 8032)
│   │   ├── address.py           # Base58Check address encoding with 4-byte checksum
│   │   └── cipher.py            # scrypt (N=16384, r=8, p=1) + AES-256-GCM authenticated encryption
│   ├── consensus/
│   │   ├── __init__.py
│   │   ├── prime.py             # Small-prime pre-sieve & Miller-Rabin primality test
│   │   ├── cunningham.py        # Cunningham chains (1CC & 2CC), theft-proof origin derivation, mining
│   │   └── difficulty.py        # 144-block retarget epoch, 60s target time, 4x/0.25x clamping bounds
│   ├── core/
│   │   ├── __init__.py
│   │   ├── transaction.py       # UTXO TxInput/TxOutput, SegWit-style txids, Ed25519 verification
│   │   ├── block.py             # BlockHeader, Merkle root tree, MTP (11 blocks), future timestamp guard
│   │   ├── mempool.py           # Thread-safe mempool, fee prioritizing, double-spend eviction
│   │   ├── genesis.py           # Deterministic genesis block specification
│   │   └── chain.py             # Blockchain state, cumulative work, halving curve, atomic reorg
│   ├── storage/
│   │   ├── __init__.py
│   │   └── database.py          # SQLite WAL-mode atomic ledger storage & crash recovery
│   ├── network/
│   │   ├── __init__.py
│   │   ├── protocol.py          # Binary packet framing (PROF magic, checksum, 2MB size cap)
│   │   ├── peer.py              # Asyncio peer connection, rate limiter, misbehavior scoring
│   │   └── node.py              # P2P Node, gossip propagation, chain sync, background miner
│   └── wallet/
│       ├── __init__.py
│       └── wallet.py            # Wallet key management, coin selection, tx assembly & signing
├── tests/
│   ├── test_crypto.py           # Ed25519, Base58Check, scrypt+AES-GCM tests
│   ├── test_consensus.py        # Miller-Rabin, Cunningham chains, difficulty adjustment, anti-theft
│   ├── test_transaction.py      # UTXO validation, replay protection, double-spend, integer bounds
│   ├── test_block.py            # Merkle tree, MTP rule, timestamp drift, 21M emission halving
│   ├── test_chain_reorg.py      # Cumulative work reorgs, UTXO state rollback and application
│   ├── test_persistence.py      # SQLite atomic commit & crash recovery
│   ├── test_fuzz.py             # Fuzzing wire protocol, addresses, negative and overflow values
│   └── test_network.py          # 3-node asyncio P2P network simulation (gossip, sync, auto-ban)
├── docs/
│   ├── README.md                # This manual
│   ├── ARCHITECTURE.md          # In-depth architectural specification
│   ├── WHITEPAPER.md            # Mathematical PoUW whitepaper & economic model
│   └── SECURITY.md              # Threat analysis, security checklist & mainnet roadmap
```

---

## 🚀 Quickstart & Installation

### Requirements
- Python 3.10+ (Python 3.11 recommended)
- `cryptography` package
- `pytest` (for test suite)

### Setup
```bash
# Clone and enter workspace
git clone <repo-url> proofcoin
cd proofcoin

# Install dependencies (if not using system packages)
pip install cryptography pytest
```

---

## 🧪 Running the Test Suite

ProofCoin comes with an exhaustive 26-test verification suite covering 100% of functional requirements:

```bash
# Run all unit, consensus, fuzz, persistence, and network tests
python3 -m pytest tests/ -v
```

All 26 tests run in under 2 seconds.

---

## 💻 CLI Usage Guide

ProofCoin features an integrated CLI via `python3 -m proofcoin.cli` or `python3 proofcoin/cli.py`:

### 1. Create a New Encrypted Wallet
```bash
python3 proofcoin/cli.py create-wallet --wallet-file my_wallet.json --passphrase "SuperSecretPassword123!"
```
*Generates an Ed25519 keypair, derives a checksummed address (`P...`), and encrypts the keypair using `scrypt (N=16384, r=8, p=1)` and AES-256-GCM.*

### 2. Inspect Wallet
```bash
python3 proofcoin/cli.py load-wallet --wallet-file my_wallet.json --passphrase "SuperSecretPassword123!"
```

### 3. Check Ledger Status
```bash
python3 proofcoin/cli.py get-chain-info
```

### 4. Mine Blocks with PoUW
```bash
python3 proofcoin/cli.py start-mining --wallet-file my_wallet.json --passphrase "SuperSecretPassword123!" --blocks 3
```
*Discovers Cunningham prime chains and mints blocks, depositing the 50 ProofCoin block rewards to your address.*

### 5. Check Balance
```bash
python3 proofcoin/cli.py get-balance --wallet-file my_wallet.json --passphrase "SuperSecretPassword123!"
```

### 6. Run an Asynchronous P2P Node
```bash
python3 proofcoin/cli.py run-node --host 127.0.0.1 --port 9333
```
To connect a second node to the first:
```bash
python3 proofcoin/cli.py run-node --host 127.0.0.1 --port 9334 --peer 127.0.0.1:9333
```
