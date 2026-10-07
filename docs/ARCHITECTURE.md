# ProofCoin System Architecture

This document details the internal architecture, mathematical formulations, data schemas, and state transition pipelines of ProofCoin.

---

## 1. Consensus Architecture: Proof of Useful Work (PoUW)

### 1.1 The Cunningham Chain Problem
Proof of Useful Work replaces useless SHA-256 hash inversion with computational discovery of prime chains:
- **Cunningham Chain of the First Kind (1CC)**:
  $$p_{i+1} = 2 \cdot p_i + 1 \quad \forall \, 0 \le i < k - 1$$
  Every number $p_0, p_1, \dots, p_{k-1}$ is prime.
- **Cunningham Chain of the Second Kind (2CC)**:
  $$p_{i+1} = 2 \cdot p_i - 1 \quad \forall \, 0 \le i < k - 1$$
  Every number $p_0, p_1, \dots, p_{k-1}$ is prime.

### 1.2 Anti-Theft Solution Binding
In standard Proof of Work, an eavesdropping peer could attempt to steal a miner's solution by stripping the miner's address and submitting the block under their own key.
ProofCoin prevents this through **deterministic candidate binding**:
$$\text{seed} = \text{SHA-256}\big(\text{SHA-256}(\text{prev\_hash} \parallel \text{miner\_pubkey} \parallel \text{merkle\_root} \parallel \text{nonce})\big)$$
$$p_0 = \text{DeriveOrigin}(\text{seed})$$

If an adversary alters `miner_pubkey` to their own public key, $p_0$ changes completely due to avalanche diffusion in SHA-256. The primes in the chain no longer match, instantly invalidating the block during verification.

### 1.3 Asymmetric Verification (Miller-Rabin)
- **Mining Effort**: Exploring $O(10^4 - 10^7)$ candidate seeds using pre-sieve trial division and modular exponentiation.
- **Verification Cost**: Exactly $k$ primality tests (where $k \approx 3 \text{ to } 7$). Miller-Rabin verifies the full chain in $< 0.5$ milliseconds.

### 1.4 Difficulty Retargeting & Clamping
- **Epoch Window**: 144 blocks (corresponds to ~2.4 hours at 60s target time).
- **Target Time**: $\tau = 60 \text{ seconds}$.
- **Expected Timespan**: $T_{\text{target}} = 144 \times 60 = 8,640 \text{ seconds}$.
- **Actual Timespan**: $T_{\text{actual}} = t_{N} - t_{N - 144}$.
- **Clamping Filter**:
  $$T_{\text{clamped}} = \max\left(\frac{T_{\text{target}}}{4}, \min\left(4 \cdot T_{\text{target}}, T_{\text{actual}}\right)\right)$$
- **Difficulty Recalculation**:
  $$D_{\text{new}} = D_{\text{current}} \times \frac{T_{\text{target}}}{T_{\text{clamped}}}$$
  Bounded within $[\text{MIN\_DIFFICULTY} = 2.0, \text{MAX\_DIFFICULTY} = 12.0]$.

---

## 2. Block and Transaction Ledger

### 2.1 Block Structure
Each block consists of a **Header** and an **Ordered Transaction Array**:
```
+--------------------------------------------------------------------+
| BlockHeader                                                        |
| - version (uint32)                                                 |
| - prev_hash (32 bytes hex)                                         |
| - merkle_root (32 bytes hex)                                       |
| - timestamp (uint64)                                               |
| - difficulty (float64)                                             |
| - nonce (uint64)                                                   |
| - miner_pubkey (32 bytes hex)                                      |
| - solution: { chain_type, origin, length, primes[] }               |
+--------------------------------------------------------------------+
| Transactions [ Tx_0 (Coinbase), Tx_1, Tx_2, ... ]                  |
+--------------------------------------------------------------------+
```

### 2.2 Consensus Validation Rules
1. **Timestamp Rules**:
   - **MTP Barrier**: $t_{\text{block}} > \text{Median}(t_{n-1}, t_{n-2}, \dots, t_{n-11})$.
   - **Future Limit**: $t_{\text{block}} \le t_{\text{local}} + 7200 \text{ seconds}$.
2. **Merkle Root**: Double-SHA256 balanced binary tree. If a level is odd, the last node is duplicated.
3. **Subsidy & Fees**:
   $$\text{coinbase\_output\_amount} \le \text{subsidy}(h) + \sum_{i=1}^m \text{fee}(Tx_i)$$
   $$\text{subsidy}(h) = \left(50 \times 10^8\right) \gg \left\lfloor \frac{h}{210,000} \right\rfloor$$

### 2.3 UTXO Model and Segregated Signatures
Transactions follow Bitcoin's UTXO design:
- `TxInput`: references `(prev_txid, vout)` and includes `signature` and `pubkey`.
- `TxOutput`: contains atomic integer `amount` and recipient `address`.
- **Malleability Immunity**: `txid` is computed over inputs (excluding signatures) and outputs. Third parties cannot alter signatures to change the transaction hash.
- **Double Spend Prevention**:
  1. Internal check: No transaction may spend the same `(prev_txid, vout)` twice in its input list.
  2. UTXO set check: An input is only valid if `(prev_txid, vout)` exists in the unspent set. Upon spend, it is pruned immediately.

---

## 3. Asynchronous P2P Protocol (asyncio)

### 3.1 Packet Framing
Binary envelope over raw TCP streams:
```
+--------------------+----------------------+--------------------+--------------------+-----------------------+
| Magic (4 bytes)    | Command (12 bytes)   | Length (4 bytes)   | Checksum (4 bytes) | Payload (JSON bytes)  |
| 0x50524F46 ("PROF")| ASCII, null-padded   | uint32 (max 2MB)   | dSHA256[:4]        | UTF-8 string          |
+--------------------+----------------------+--------------------+--------------------+-----------------------+
```

### 3.2 Network Message Types
| Command | Direction | Description |
|---|---|---|
| `version` | Outbound | Initial handshake containing client version and blockchain height |
| `verack` | Bidirectional | Acknowledges version handshake |
| `ping` / `pong` | Bidirectional | Keepalive heartbeat |
| `getaddr` / `addr` | Bidirectional | Peer discovery addresses |
| `inv` | Broadcast | Inventory notification of new block or transaction |
| `getdata` | Inbound | Requests complete block or transaction by hash |
| `block` | Broadcast | Full block transmission |
| `tx` | Broadcast | Unconfirmed transaction transmission |
| `getblocks` | Outbound | Requests range of historical blocks during Initial Block Download |
| `blocks` | Inbound | Batch of historical blocks for chain synchronization |

### 3.3 Peer Scoring & DoS Defense
Each peer maintains an integer `misbehavior_score`:
- Sending invalid block: $+100$ (Immediate disconnect and IP ban for 24 hours).
- Double-spending transaction: $+40$.
- Exceeding message rate limit ($> 50 \text{ msg/sec}$): $+20$.
- Malformed packet or payload $> 2\text{MB}$: $+50$.
- **Ban Threshold**: When score reaches $\ge 100$, the connection is severed and incoming connections from that IP are blocked.

---

## 4. Chain Reorganization Engine (Reorg)

ProofCoin enforces the **Heaviest Cumulative Work Rule**:
$$\mathcal{W}_{\text{cumulative}} = \sum_{b \in \mathcal{C}} D(b)$$

When a fork block arrives:
```
           [B1] --- [B2_A] (Work: 4.0)
             \
              --- [B2_B] --- [B3_B] (Work: 6.0) -> Reorganization Winner!
```
1. **Find Fork Point**: Traverse backwards from the candidate tip until encountering a block in the active chain ($\text{common\_ancestor}$).
2. **Prepare Rollback**: Clone current UTXO set. Roll back blocks from active tip down to ancestor, restoring historical spent outputs and removing created outputs.
3. **Forward Execution**: Apply blocks from ancestor to new candidate tip, verifying all signatures and balance constraints.
4. **Atomic Commit**: If valid, replace active tip pointer with candidate branch. Re-queue disconnected non-coinbase transactions into the mempool. If any block fails, discard candidate branch and maintain existing canonical tip.

---

## 5. Storage and Crash Recovery

- **SQLite Engine**: Configured in Write-Ahead Logging (`WAL`) mode with synchronous level `NORMAL`.
- **Atomic Batch Mutation**: Block record, UTXO deletions, UTXO insertions, and chain tip metadata update are executed in a single atomic SQLite transaction (`BEGIN IMMEDIATE ... COMMIT`).
- **Crash Recovery**: On startup, `BlockchainDB` reads `best_hash` from metadata. If inconsistent with block headers, it reconciles the tip by walking backwards from the highest validated block.
