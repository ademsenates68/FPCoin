"""
ProofCoin Mempool (Memory Pool) Module.

Features:
- Thread-safe transaction holding
- In-memory double-spend rejection across unconfirmed transactions
- Fee-prioritized transaction selection for block assembly
- DoS protection with memory capacity limits
"""

import threading
from typing import Dict, List, Set, Tuple, Optional
from proofcoin.core.transaction import (
    Transaction,
    TxOutput,
    validate_transaction_basics,
    verify_transaction_signatures,
)

MAX_MEMPOOL_TRANSACTIONS: int = 5000


class Mempool:
    def __init__(self, max_size: int = MAX_MEMPOOL_TRANSACTIONS):
        self.max_size = max_size
        self._txs: Dict[str, Transaction] = {}
        self._spent_outpoints: Dict[Tuple[str, int], str] = {}  # (prev_txid, vout) -> spending txid
        self._fees: Dict[str, int] = {}
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._txs)

    def contains(self, txid: str) -> bool:
        with self._lock:
            return txid in self._txs

    def add_transaction(
        self,
        tx: Transaction,
        utxo_view: Dict[Tuple[str, int], TxOutput],
    ) -> Tuple[bool, str]:
        """
        Validate and insert transaction into memory pool.
        """
        with self._lock:
            if tx.is_coinbase:
                return False, "Coinbase transactions cannot be added to mempool"

            if tx.txid in self._txs:
                return False, "Transaction already in mempool"

            if len(self._txs) >= self.max_size:
                return False, "Mempool is full (DoS limit reached)"

            # Basic stateless checks
            valid_basics, reason = validate_transaction_basics(tx)
            if not valid_basics:
                return False, f"Basic check failed: {reason}"

            # Check if any input is already claimed by another tx in mempool
            for inp in tx.inputs:
                outpoint = (inp.prev_txid, inp.vout)
                if outpoint in self._spent_outpoints:
                    conflicting_txid = self._spent_outpoints[outpoint]
                    return False, f"Double spend in mempool: outpoint {outpoint} already spent by {conflicting_txid}"

            # Verify signatures and UTXO availability
            valid_sigs, reason = verify_transaction_signatures(tx, utxo_view)
            if not valid_sigs:
                return False, f"Signature or UTXO verification failed: {reason}"

            # Calculate transaction fee
            input_sum = sum(utxo_view[(inp.prev_txid, inp.vout)].amount for inp in tx.inputs)
            output_sum = sum(out.amount for out in tx.outputs)
            fee = input_sum - output_sum

            # Register in mempool
            self._txs[tx.txid] = tx
            self._fees[tx.txid] = fee
            for inp in tx.inputs:
                self._spent_outpoints[(inp.prev_txid, inp.vout)] = tx.txid

            return True, f"Accepted into mempool (fee: {fee})"

    def get_transaction(self, txid: str) -> Optional[Transaction]:
        with self._lock:
            return self._txs.get(txid)

    def remove_transaction(self, txid: str) -> None:
        with self._lock:
            tx = self._txs.pop(txid, None)
            self._fees.pop(txid, None)
            if tx:
                for inp in tx.inputs:
                    self._spent_outpoints.pop((inp.prev_txid, inp.vout), None)

    def remove_transactions(self, txids: List[str]) -> None:
        with self._lock:
            for txid in txids:
                self.remove_transaction(txid)

    def get_candidate_transactions(self, max_count: int = 500) -> List[Transaction]:
        """
        Return transactions prioritized by highest fee.
        """
        with self._lock:
            sorted_txids = sorted(
                self._fees.keys(),
                key=lambda tid: self._fees[tid],
                reverse=True,
            )
            return [self._txs[tid] for tid in sorted_txids[:max_count]]

    def clear(self) -> None:
        with self._lock:
            self._txs.clear()
            self._spent_outpoints.clear()
            self._fees.clear()
