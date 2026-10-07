"""
Unit Tests for ProofCoin SQLite Storage Engine and Persistence.
"""

import os
import tempfile
import pytest
from proofcoin.core.genesis import get_genesis_block
from proofcoin.core.transaction import TxOutput, COIN
from proofcoin.storage.database import BlockchainDB


def test_sqlite_storage_atomic_write_and_read():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = BlockchainDB(db_path)
        genesis = get_genesis_block()

        # Save Genesis Block into database
        new_utxos = [
            (genesis.transactions[0].txid, 0, genesis.transactions[0].outputs[0])
        ]
        db.save_block_atomic(
            block=genesis,
            height=0,
            spent_outpoints=[],
            new_utxos=new_utxos,
            cumulative_work=2.0,
        )

        # Retrieve block
        loaded_block = db.get_block(genesis.block_hash)
        assert loaded_block is not None
        assert loaded_block.block_hash == genesis.block_hash
        assert loaded_block.header.timestamp == genesis.header.timestamp

        # Retrieve block by height
        loaded_by_h = db.get_block_by_height(0)
        assert loaded_by_h is not None
        assert loaded_by_h.block_hash == genesis.block_hash

        # Verify UTXO persistence
        utxos = db.get_all_utxos()
        assert len(utxos) == 1
        outpoint = (genesis.transactions[0].txid, 0)
        assert outpoint in utxos
        assert utxos[outpoint].amount == 50 * COIN

        # Verify Metadata
        assert db.get_metadata("best_hash") == genesis.block_hash
        assert db.get_metadata("best_height") == "0"
        assert db.get_metadata("cumulative_work") == "2.0"

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
