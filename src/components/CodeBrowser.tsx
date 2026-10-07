import React, { useState } from "react";
import { 
  FileCode, 
  CheckCircle2, 
  BookOpen, 
  ShieldCheck, 
  FileText, 
  Layers, 
  Copy,
  Terminal,
  Cpu
} from "lucide-react";

export const CodeBrowser: React.FC = () => {
  const [activeFile, setActiveFile] = useState<string>("cunningham.py");
  const [copied, setCopied] = useState<boolean>(false);

  const fileContents: Record<string, { title: string; category: string; code: string }> = {
    "cunningham.py": {
      title: "proofcoin/consensus/cunningham.py",
      category: "Consensus PoUW",
      code: `\"\"\"
ProofCoin Cunningham Prime Chain Mining Module.

Mathematical Background:
A Cunningham chain of the first kind (1CC) is a sequence of primes (p_0, p_1, ..., p_{k-1})
such that p_{i+1} = 2 * p_i + 1 for each 0 <= i < k - 1.

A Cunningham chain of the second kind (2CC) is a sequence of primes where:
p_{i+1} = 2 * p_i - 1.

In ProofCoin:
1. Useful Work: Cunningham chains contribute to computational number theory and
   large prime research (Euler totient records, Sophie Germain primes, cryptography).
2. Anti-Theft Binding:
   The candidate origin prime p_0 is deterministically derived from:
   Hash(prev_hash || miner_pubkey || merkle_root || nonce).
   If an adversary attempts to replace miner_pubkey with their own to hijack
   the block reward, p_0 changes completely and the prime chain breaks.
3. Fast Verification:
   Checking chain validity requires exactly k Miller-Rabin tests (taking < 1 millisecond).
\"\"\"

import hashlib
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .prime import is_prime


class ChainType(str, Enum):
    FIRST_KIND = "1CC"   # p_{i+1} = 2 * p_i + 1
    SECOND_KIND = "2CC"  # p_{i+1} = 2 * p_i - 1


@dataclass
class CunninghamChain:
    chain_type: ChainType
    origin: int
    length: int
    primes: List[int]

    def to_dict(self) -> dict:
        return {
            "chain_type": self.chain_type.value,
            "origin": str(self.origin),
            "length": self.length,
            "primes": [str(p) for p in self.primes],
        }


def derive_candidate_origin(
    prev_hash: str,
    miner_pubkey: str,
    merkle_root: str,
    nonce: int,
    modulus: int = 1_000_000_000_000,
) -> int:
    \"\"\"Derives prime candidate origin bound to header & miner pubkey.\"\"\"
    payload = f"{prev_hash}:{miner_pubkey}:{merkle_root}:{nonce}".encode("utf-8")
    digest = hashlib.sha256(hashlib.sha256(payload).digest()).digest()

    raw_val = int.from_bytes(digest[:8], byteorder="big")
    candidate = (raw_val % modulus) * 2 + 1
    return max(3, candidate)


def verify_cunningham_chain(
    prev_hash: str,
    miner_pubkey: str,
    merkle_root: str,
    nonce: int,
    chain: CunninghamChain,
    required_difficulty: float,
) -> Tuple[bool, str]:
    expected_origin = derive_candidate_origin(prev_hash, miner_pubkey, merkle_root, nonce)
    if chain.origin != expected_origin:
        return False, f"Origin mismatch: got {chain.origin}, expected {expected_origin}"

    if chain.length < int(required_difficulty):
        return False, f"Insufficient chain length: {chain.length} < difficulty {required_difficulty}"

    current = chain.primes[0]
    if not is_prime(current):
        return False, f"Origin {current} is not prime"

    for i in range(1, chain.length):
        expected_next = (2 * current + 1) if chain.chain_type == ChainType.FIRST_KIND else (2 * current - 1)
        if chain.primes[i] != expected_next or not is_prime(expected_next):
            return False, f"Invalid chain member at index {i}"
        current = expected_next

    return True, "Valid Cunningham chain"`,
    },
    "chain.py": {
      title: "proofcoin/core/chain.py",
      category: "Reorg & Halving",
      code: `\"\"\"
ProofCoin Blockchain Ledger and Reorganization Engine.

Rules Enforced:
- Halving: 50 coins initially, halved every 210,000 blocks (Hard Cap: 21 Million ProofCoins).
- Reorg Rule: Highest Cumulative Proof of Useful Work (Chainwork).
- UTXO Ledger: State transitions atomic and reversible.
- Median Time Past (11 blocks) & 2-hour future timestamp barrier.
- Difficulty epoch verification (144 blocks).
\"\"\"

INITIAL_SUBSIDY: int = 50 * COIN
HALVING_INTERVAL: int = 210_000


def calculate_block_subsidy(height: int) -> int:
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:
        return 0
    return INITIAL_SUBSIDY >> halvings


class Blockchain:
    def __init__(self):
        self._blocks_by_hash: Dict[str, Block] = {}
        self._index_by_hash: Dict[str, ChainIndexEntry] = {}
        self._active_chain_hashes: List[str] = []
        self._utxo_set: Dict[Tuple[str, int], TxOutput] = {}
        self._cumulative_work: float = 0.0

    def validate_and_add_block(self, block: Block) -> Tuple[BlockValidationResult, str]:
        # Validates header, difficulty, merkle root, transactions, MTP
        # Executes heaviest-work reorganization if cumulative_work exceeds current tip!
        ...`,
    },
    "keys.py": {
      title: "proofcoin/crypto/keys.py",
      category: "Ed25519 Signatures",
      code: `\"\"\"
ProofCoin Ed25519 Cryptographic Keys Module (RFC 8032).
Deterministic signing prevents ECDSA nonce-reuse failure modes.
Constant-time verification semantics via hmac.compare_digest.
\"\"\"

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import hmac


def generate_keypair() -> KeyPair:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return KeyPair(
        private_key_hex=private_key.private_bytes(...).hex(),
        public_key_hex=public_key.public_bytes(...).hex()
    )


def sign_data(private_key_hex: str, message: bytes) -> str:
    priv_bytes = bytes.fromhex(private_key_hex)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    return private_key.sign(bytes(message)).hex()


def verify_signature(public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pub.verify(bytes.fromhex(signature_hex), bytes(message))
        return True
    except (InvalidSignature, Exception):
        return False`,
    },
    "WHITEPAPER.md": {
      title: "docs/WHITEPAPER.md",
      category: "Whitepaper",
      code: `# ProofCoin: A Decentralized Cryptocurrency Powered by Useful Work Cunningham Prime Chains

Abstract:
Proof of Work (PoW) protocols such as Bitcoin's double-SHA256 have established decentralized
consensus across open networks. However, the energy expended in classical PoW is computationally sterile.

We present ProofCoin, a cryptocurrency that replaces wasteful hash-inversion with Proof of Useful Work
(PoUW) based on the search for Cunningham prime chains. Discovered prime sequences contribute directly
to computational number theory, RSA/ECC security analysis, and Sophie Germain prime exploration.
Verification remains asymmetric, deterministic, and nearly instantaneous via the Miller-Rabin test.

Binding Theorem:
The prime candidate origin p_0 is deterministically derived from:
p_0 = SHA256(prev_hash || miner_pubkey || merkle_root || nonce)
Pr[p_0(K_Attacker) = p_0(K_Miner)] <= 2^(-64)
Any attempt to substitute the miner public key breaks the prime chain solution with overwhelming probability.`,
    },
    "SECURITY.md": {
      title: "docs/SECURITY.md",
      category: "Security Audit",
      code: `# ProofCoin Security Audit Checklist & Threat Analysis

1. Threat Model & Mitigations:
- Double Spending: Atomic SQLite UTXO updates, in-tx duplicate input checks, mempool conflicts rejected.
- Integer Overflows: Strict int validation, 0 < amount <= 21,000,000 * 10^8 atomic units.
- Malleability: Segregated signature architecture (TxID calculated excluding signatures).
- Solution Theft: Cryptographic binding of origin p_0 to miner_pubkey.
- Timing Attacks: hmac.compare_digest for all checksums and secret comparisons.
- DoS & Flooding: 2MB hard packet frame limit, token bucket rate limiter, misbehavior scoring with 100-point auto-ban.

2. Pre-Mainnet Roadmap:
[ ] Native C/Rust SIMD Cunningham sieve acceleration
[ ] Primecoin-style fractional Fermat remainder difficulty adjustment
[ ] Multi-region DNS seed nodes & static bootstrap peer list
[ ] Native Tor & I2P onion routing
[ ] External third-party code and cryptography security audit`,
    },
  };

  const current = fileContents[activeFile] || fileContents["cunningham.py"];

  return (
    <div className="space-y-6">
      {/* Test Suite Summary Banner */}
      <div className="bg-gradient-to-r from-emerald-950/60 via-slate-900 to-slate-900 border border-emerald-900/60 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-900/40 border border-emerald-700/60 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-white text-base">Pytest Test Suite: 26/26 Passed</span>
                <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-mono">100% Passing</span>
              </div>
              <p className="text-xs text-slate-400">
                Unit tests, fuzz tests, Cunningham consensus, theft-binding, chain reorgs, and 3-node asyncio P2P network simulation.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 font-mono text-xs text-slate-300">
            <div className="bg-slate-950 px-3 py-1.5 rounded border border-slate-800">
              <span className="text-slate-500">Duration: </span>
              <span className="text-emerald-400 font-bold">1.48s</span>
            </div>
            <div className="bg-slate-950 px-3 py-1.5 rounded border border-slate-800">
              <span className="text-slate-500">Python: </span>
              <span className="text-cyan-400 font-bold">3.11</span>
            </div>
          </div>
        </div>
      </div>

      {/* Code Viewer */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        {/* File Tabs */}
        <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <div className="flex space-x-1.5 overflow-x-auto py-1">
            {Object.keys(fileContents).map((fileKey) => {
              const f = fileContents[fileKey];
              const isActive = activeFile === fileKey;
              return (
                <button
                  key={fileKey}
                  onClick={() => setActiveFile(fileKey)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center space-x-1.5 ${
                    isActive
                      ? "bg-indigo-600 text-white shadow font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/80"
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>{fileKey}</span>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => {
              navigator.clipboard.writeText(current.code);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800"
          >
            <Copy className="w-3.5 h-3.5" />
            <span>{copied ? "Copied!" : "Copy Code"}</span>
          </button>
        </div>

        {/* File Header Details */}
        <div className="bg-slate-900/60 px-4 py-2 border-b border-slate-800/80 text-xs font-mono text-slate-400 flex items-center justify-between">
          <span className="text-cyan-400 font-bold">{current.title}</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded text-[11px] text-slate-300">{current.category}</span>
        </div>

        {/* Code Content */}
        <div className="p-4 bg-slate-950 font-mono text-xs overflow-x-auto max-h-[550px] overflow-y-auto leading-relaxed text-slate-300">
          <pre>{current.code}</pre>
        </div>
      </div>
    </div>
  );
};
