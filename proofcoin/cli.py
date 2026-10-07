"""
ProofCoin Command-Line Interface (CLI).

Subcommands:
- create-wallet: Generate and encrypt new Ed25519 wallet
- load-wallet: Display address and public key of encrypted wallet
- get-balance: Check UTXO balance for an address
- send: Create, sign, and broadcast an atomic UTXO transaction
- start-mining: Search for Cunningham prime chains and mine blocks
- get-chain-info: Display blockchain height, difficulty, and UTXO statistics
- run-node: Run an asynchronous P2P daemon node
"""

import sys
import os

# Ensure package root is importable when executed directly as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import asyncio
import json
import logging
from typing import Optional

from proofcoin.core.transaction import COIN, create_coinbase_tx
from proofcoin.core.block import BlockHeader, Block, calculate_merkle_root
from proofcoin.core.chain import Blockchain, BlockValidationResult, calculate_block_subsidy
from proofcoin.consensus.cunningham import mine_cunningham_chain
from proofcoin.storage.database import BlockchainDB
from proofcoin.wallet.wallet import Wallet
from proofcoin.network.node import P2PNode

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")


def cmd_create_wallet(args: argparse.Namespace) -> None:
    wallet = Wallet.create()
    passphrase = args.passphrase
    if not passphrase:
        import getpass
        passphrase = getpass.getpass("Enter passphrase to encrypt wallet: ")

    wallet.save_to_encrypted_file(args.wallet_file, passphrase)
    print("\n✅ New Wallet Successfully Created!")
    print(f"📁 File:       {args.wallet_file}")
    print(f"🔑 Address:    {wallet.address}")
    print(f"🔒 Public Key: {wallet.keypair.public_key_hex}\n")


def cmd_load_wallet(args: argparse.Namespace) -> None:
    passphrase = args.passphrase
    if not passphrase:
        import getpass
        passphrase = getpass.getpass("Enter wallet passphrase: ")

    try:
        wallet = Wallet.load_from_encrypted_file(args.wallet_file, passphrase)
        print("\n🔓 Wallet Decrypted Successfully:")
        print(f"🔑 Address:    {wallet.address}")
        print(f"🔒 Public Key: {wallet.keypair.public_key_hex}\n")
    except Exception as e:
        print(f"\n❌ Failed to decrypt wallet: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_get_balance(args: argparse.Namespace) -> None:
    db = BlockchainDB(args.db_file)
    utxos = db.get_all_utxos()

    target_address = args.address
    if not target_address and args.wallet_file:
        import getpass
        passphrase = args.passphrase or getpass.getpass("Enter wallet passphrase: ")
        wallet = Wallet.load_from_encrypted_file(args.wallet_file, passphrase)
        target_address = wallet.address

    if not target_address:
        print("❌ Please specify either --address or --wallet-file", file=sys.stderr)
        sys.exit(1)

    balance_atomic = sum(out.amount for out in utxos.values() if out.address == target_address)
    print(f"\n💰 Address: {target_address}")
    print(f"💵 Balance: {balance_atomic / COIN:.8f} ProofCoins ({balance_atomic} atomic units)\n")


def cmd_get_chain_info(args: argparse.Namespace) -> None:
    chain = Blockchain()
    print("\n📊 ProofCoin Ledger Status:")
    print(f"⛓️  Best Height:     {chain.height}")
    print(f"🏷️  Tip Hash:        {chain.tip_block.block_hash}")
    print(f"🎯 Next Difficulty: {chain.get_expected_difficulty(chain.tip_block.block_hash)}")
    print(f"⚡ Cumulative Work: {chain.cumulative_work}")
    print(f"📦 UTXO Count:      {len(chain.utxo_set)}")
    total_supply = sum(out.amount for out in chain.utxo_set.values())
    print(f"🪙 Circulating:     {total_supply / COIN:.8f} ProofCoins\n")


def cmd_start_mining(args: argparse.Namespace) -> None:
    import time
    chain = Blockchain()
    reward_addr = args.reward_address
    miner_pubkey = args.miner_pubkey

    if args.wallet_file:
        import getpass
        passphrase = args.passphrase or getpass.getpass("Enter wallet passphrase: ")
        wallet = Wallet.load_from_encrypted_file(args.wallet_file, passphrase)
        reward_addr = wallet.address
        miner_pubkey = wallet.keypair.public_key_hex

    if not reward_addr or not miner_pubkey:
        print("❌ Error: Need --reward-address and --miner-pubkey (or --wallet-file)", file=sys.stderr)
        sys.exit(1)

    print(f"\n⛏️  Starting Proof of Useful Work (PoUW) Miner...")
    print(f"Recipient: {reward_addr}")
    print(f"Miner Key: {miner_pubkey[:16]}...")
    target_blocks = args.blocks or 1

    mined_count = 0
    while mined_count < target_blocks:
        prev_block = chain.tip_block
        height = chain.height + 1
        diff = chain.get_expected_difficulty(prev_block.block_hash)
        subsidy = calculate_block_subsidy(height)

        coinbase = create_coinbase_tx(reward_addr, subsidy, 0, height)
        merkle_root = calculate_merkle_root([coinbase.txid])

        print(f"Searching Cunningham prime chain for Block #{height} (Diff {diff})...")
        t0 = time.time()
        res = mine_cunningham_chain(
            prev_hash=prev_block.block_hash,
            miner_pubkey=miner_pubkey,
            merkle_root=merkle_root,
            target_difficulty=diff,
            max_iterations=200000,
        )

        if res:
            nonce, chain_sol = res
            t_elapsed = time.time() - t0
            header = BlockHeader(
                version=1,
                prev_hash=prev_block.block_hash,
                merkle_root=merkle_root,
                timestamp=max(int(time.time()), prev_block.header.timestamp + 1),
                difficulty=diff,
                nonce=nonce,
                miner_pubkey=miner_pubkey,
                solution=chain_sol,
            )
            blk = Block(header=header, transactions=[coinbase])
            val_res, reason = chain.validate_and_add_block(blk)
            if val_res == BlockValidationResult.VALID:
                print(f"🎉 Block #{height} mined in {t_elapsed:.3f}s!")
                print(f"   Hash:      {blk.block_hash}")
                print(f"   PoUW Type: {chain_sol.chain_type.value}")
                print(f"   Primes:    {chain_sol.primes}")
                mined_count += 1
            else:
                print(f"⚠️ Validation failed: {reason}")
        else:
            print("Iteration limit reached, retrying...")


def cmd_run_node(args: argparse.Namespace) -> None:
    async def _async_main():
        node = P2PNode(host=args.host, port=args.port)
        await node.start()

        if args.peer:
            p_host, p_port = args.peer.split(":")
            await node.connect_to_peer(p_host, int(p_port))

        print(f"🚀 Node running on {args.host}:{args.port}. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await node.stop()

    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\nNode terminated gracefully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ProofCoin Core Protocol & Wallet CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-wallet
    p_create = subparsers.add_parser("create-wallet", help="Create encrypted wallet")
    p_create.add_argument("--wallet-file", default="wallet.json", help="Path to wallet output file")
    p_create.add_argument("--passphrase", default=None, help="Encryption passphrase")

    # load-wallet
    p_load = subparsers.add_parser("load-wallet", help="View address and public key")
    p_load.add_argument("--wallet-file", default="wallet.json", help="Path to wallet file")
    p_load.add_argument("--passphrase", default=None, help="Encryption passphrase")

    # get-balance
    p_bal = subparsers.add_parser("get-balance", help="Inspect spendable UTXO balance")
    p_bal.add_argument("--address", default=None, help="ProofCoin address")
    p_bal.add_argument("--wallet-file", default=None, help="Path to wallet file")
    p_bal.add_argument("--passphrase", default=None, help="Encryption passphrase")
    p_bal.add_argument("--db-file", default="proofcoin_data.db", help="Path to SQLite database")

    # get-chain-info
    subparsers.add_parser("get-chain-info", help="Inspect blockchain state")

    # start-mining
    p_mine = subparsers.add_parser("start-mining", help="Mine Cunningham prime chains")
    p_mine.add_argument("--reward-address", default=None, help="Mining reward address")
    p_mine.add_argument("--miner-pubkey", default=None, help="Miner Ed25519 public key")
    p_mine.add_argument("--wallet-file", default=None, help="Wallet file to mine to")
    p_mine.add_argument("--passphrase", default=None, help="Wallet passphrase")
    p_mine.add_argument("--blocks", type=int, default=1, help="Number of blocks to mine")

    # run-node
    p_node = subparsers.add_parser("run-node", help="Run P2P node daemon")
    p_node.add_argument("--host", default="127.0.0.1", help="P2P listen host")
    p_node.add_argument("--port", type=int, default=9333, help="P2P listen port")
    p_node.add_argument("--peer", default=None, help="Initial peer to connect (host:port)")

    args = parser.parse_args()

    cmd_map = {
        "create-wallet": cmd_create_wallet,
        "load-wallet": cmd_load_wallet,
        "get-balance": cmd_get_balance,
        "get-chain-info": cmd_get_chain_info,
        "start-mining": cmd_start_mining,
        "run-node": cmd_run_node,
    }

    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
