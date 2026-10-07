"""
ProofCoin Full Node and P2P Gossip Engine.

Coordinates:
- Asynchronous TCP Server & Peer Management
- Dynamic Peer Discovery & Handshake
- Block & Transaction Gossip Diffusion (inv/getdata/block/tx)
- Initial Block Download (IBD) / Chain Synchronization
- Background PoUW Cunningham Chain Mining Engine
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Tuple
from proofcoin.consensus.cunningham import mine_cunningham_chain
from proofcoin.core.transaction import (
    Transaction,
    TxOutput,
    create_coinbase_tx,
    COIN,
)
from proofcoin.core.block import BlockHeader, Block, calculate_merkle_root
from proofcoin.core.chain import Blockchain, BlockValidationResult, calculate_block_subsidy
from proofcoin.core.mempool import Mempool
from proofcoin.storage.database import BlockchainDB
from .protocol import MessageType, NetworkMessage
from .peer import PeerConnection

logger = logging.getLogger("proofcoin.node")


class P2PNode:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9333,
        blockchain: Optional[Blockchain] = None,
        db: Optional[BlockchainDB] = None,
    ):
        self.host = host
        self.port = port
        self.blockchain = blockchain or Blockchain()
        self.mempool = Mempool()
        self.db = db

        self.server: Optional[asyncio.Server] = None
        self.peers: Dict[str, PeerConnection] = {}
        self.banned_ips: Set[str] = set()
        self.known_peer_addrs: Set[Tuple[str, int]] = set()

        self._running = False
        self._mining_active = False
        self._miner_task: Optional[asyncio.Task] = None
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start P2P server."""
        self._running = True
        self.server = await asyncio.start_server(self._handle_incoming_peer, self.host, self.port)
        logger.info(f"ProofCoin node listening on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Gracefully stop node, miner, and disconnect all peers."""
        self._running = False
        self.stop_mining()

        for peer in list(self.peers.values()):
            peer.disconnect()
        self.peers.clear()

        for t in self._tasks:
            t.cancel()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def connect_to_peer(self, peer_host: str, peer_port: int) -> bool:
        """Connect to an outbound peer and initiate handshake."""
        if (peer_host, peer_port) in [(self.host, self.port)]:
            return False

        peer_key = f"{peer_host}:{peer_port}"
        if peer_key in self.peers or peer_host in self.banned_ips:
            return False

        try:
            reader, writer = await asyncio.open_connection(peer_host, peer_port)
            peer = PeerConnection(reader, writer, peer_key, is_inbound=False)
            self.peers[peer_key] = peer
            self.known_peer_addrs.add((peer_host, peer_port))

            # Send version handshake
            await peer.send_message(
                MessageType.VERSION,
                {
                    "version": 1,
                    "height": self.blockchain.height,
                    "port": self.port,
                },
            )

            # Start message loop
            task = asyncio.create_task(self._peer_message_loop(peer))
            self._tasks.append(task)
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to peer {peer_key}: {e}")
            return False

    async def _handle_incoming_peer(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming inbound socket."""
        peer_addr = writer.get_extra_info("peername")
        peer_ip = peer_addr[0]
        peer_key = f"{peer_addr[0]}:{peer_addr[1]}"

        if peer_ip in self.banned_ips:
            writer.close()
            return

        peer = PeerConnection(reader, writer, peer_key, is_inbound=True)
        self.peers[peer_key] = peer

        task = asyncio.create_task(self._peer_message_loop(peer))
        self._tasks.append(task)

    async def _peer_message_loop(self, peer: PeerConnection) -> None:
        """Continuous event loop for a connected peer."""
        try:
            while self._running and peer.is_connected:
                msg_type, payload, status = await peer.read_message(timeout=30.0)
                if not msg_type:
                    if status != "Socket read timeout":
                        break
                    continue

                if not peer.check_rate_limit():
                    continue

                await self._process_message(peer, msg_type, payload)
        except Exception as e:
            logger.debug(f"Peer loop terminated: {e}")
        finally:
            peer.disconnect()
            self.peers.pop(peer.peer_id, None)

    async def _process_message(self, peer: PeerConnection, msg_type: MessageType, payload: dict) -> None:
        """Route and execute network protocol commands."""
        if msg_type == MessageType.VERSION:
            peer.best_height = payload.get("height", 0)
            peer.version_acknowledged = True
            await peer.send_message(MessageType.VERACK, {})

            # If peer has higher height, request blocks for synchronization
            if peer.best_height > self.blockchain.height:
                await peer.send_message(
                    MessageType.GETBLOCKS,
                    {"start_height": self.blockchain.height + 1},
                )

        elif msg_type == MessageType.VERACK:
            peer.version_acknowledged = True

        elif msg_type == MessageType.PING:
            await peer.send_message(MessageType.PONG, {"nonce": payload.get("nonce", 0)})

        elif msg_type == MessageType.PONG:
            pass

        elif msg_type == MessageType.GETBLOCKS:
            start_h = payload.get("start_height", 0)
            blocks_to_send = []
            for h in range(start_h, min(start_h + 100, self.blockchain.height + 1)):
                b = self.blockchain.get_block_by_height(h)
                if b:
                    blocks_to_send.append(b.to_dict())
            if blocks_to_send:
                await peer.send_message(MessageType.BLOCKS, {"blocks": blocks_to_send})

        elif msg_type == MessageType.BLOCKS:
            blocks_data = payload.get("blocks", [])
            for b_data in blocks_data:
                try:
                    block = Block.from_dict(b_data)
                    res, reason = self.blockchain.validate_and_add_block(block)
                    if res == BlockValidationResult.VALID:
                        # Prune mempool
                        self.mempool.remove_transactions([tx.txid for tx in block.transactions])
                    elif res not in (BlockValidationResult.ALREADY_EXISTS, BlockValidationResult.MISSING_PARENT):
                        peer.add_misbehavior_score(100, f"Sent invalid block during sync: {reason}")
                        self.banned_ips.add(peer.peer_id.split(":")[0])
                        break
                except Exception as e:
                    peer.add_misbehavior_score(50, f"Malformed block: {e}")
                    break

        elif msg_type == MessageType.BLOCK:
            try:
                block = Block.from_dict(payload["block"])
                res, reason = self.blockchain.validate_and_add_block(block)
                if res == BlockValidationResult.VALID:
                    self.mempool.remove_transactions([tx.txid for tx in block.transactions])
                    # Relay to all other peers
                    await self.broadcast_block(block, exclude_peer_id=peer.peer_id)
                elif res not in (BlockValidationResult.ALREADY_EXISTS, BlockValidationResult.MISSING_PARENT):
                    peer.add_misbehavior_score(100, f"Sent invalid block: {reason}")
                    self.banned_ips.add(peer.peer_id.split(":")[0])
            except Exception as e:
                peer.add_misbehavior_score(50, f"Malformed block payload: {e}")

        elif msg_type == MessageType.TX:
            try:
                tx = Transaction.from_dict(payload["tx"])
                ok, reason = self.mempool.add_transaction(tx, self.blockchain.utxo_set)
                if ok:
                    # Relay tx to other peers
                    await self.broadcast_tx(tx, exclude_peer_id=peer.peer_id)
            except Exception as e:
                peer.add_misbehavior_score(20, f"Malformed tx: {e}")

    async def broadcast_block(self, block: Block, exclude_peer_id: Optional[str] = None) -> None:
        """Gossip newly confirmed block across all connected peers."""
        payload = {"block": block.to_dict()}
        for pid, peer in list(self.peers.items()):
            if pid != exclude_peer_id and peer.is_connected:
                await peer.send_message(MessageType.BLOCK, payload)

    async def broadcast_tx(self, tx: Transaction, exclude_peer_id: Optional[str] = None) -> None:
        """Gossip unconfirmed transaction across peer mesh."""
        payload = {"tx": tx.to_dict()}
        for pid, peer in list(self.peers.items()):
            if pid != exclude_peer_id and peer.is_connected:
                await peer.send_message(MessageType.TX, payload)

    def start_mining(self, miner_pubkey: str, reward_address: str) -> None:
        """Start background asynchronous mining loop."""
        if self._mining_active:
            return
        self._mining_active = True
        self._miner_task = asyncio.create_task(self._mining_loop(miner_pubkey, reward_address))

    def stop_mining(self) -> None:
        """Halt mining task."""
        self._mining_active = False
        if self._miner_task:
            self._miner_task.cancel()
            self._miner_task = None

    async def _mining_loop(self, miner_pubkey: str, reward_address: str) -> None:
        """Mining loop searching for Cunningham chains."""
        import time
        logger.info(f"PoUW miner started for address {reward_address}")

        while self._mining_active and self._running:
            prev_block = self.blockchain.tip_block
            prev_hash = prev_block.block_hash
            height = self.blockchain.height + 1
            difficulty = self.blockchain.get_expected_difficulty(prev_hash)

            # Assemble transactions from mempool
            txs = self.mempool.get_candidate_transactions(max_count=200)

            # Calculate total fees
            utxo_view = self.blockchain.utxo_set
            total_fees = 0
            for tx in txs:
                in_amt = sum(utxo_view[(i.prev_txid, i.vout)].amount for i in tx.inputs if (i.prev_txid, i.vout) in utxo_view)
                out_amt = sum(o.amount for o in tx.outputs)
                total_fees += max(0, in_amt - out_amt)

            subsidy = calculate_block_subsidy(height)
            coinbase = create_coinbase_tx(reward_address, subsidy, total_fees, height)
            all_txs = [coinbase] + txs

            merkle_root = calculate_merkle_root([t.txid for t in all_txs])

            # Search for Cunningham chain solution
            result = await asyncio.to_thread(
                mine_cunningham_chain,
                prev_hash=prev_hash,
                miner_pubkey=miner_pubkey,
                merkle_root=merkle_root,
                target_difficulty=difficulty,
                start_nonce=0,
                max_iterations=50000,
            )

            if result and self._mining_active:
                nonce, solution = result
                timestamp = max(int(time.time()), prev_block.header.timestamp + 1)

                header = BlockHeader(
                    version=1,
                    prev_hash=prev_hash,
                    merkle_root=merkle_root,
                    timestamp=timestamp,
                    difficulty=difficulty,
                    nonce=nonce,
                    miner_pubkey=miner_pubkey,
                    solution=solution,
                )
                new_block = Block(header=header, transactions=all_txs)

                res, reason = self.blockchain.validate_and_add_block(new_block)
                if res == BlockValidationResult.VALID:
                    logger.info(f"Successfully mined block #{height} (hash: {new_block.block_hash[:8]})!")
                    self.mempool.remove_transactions([t.txid for t in all_txs])
                    await self.broadcast_block(new_block)

            await asyncio.sleep(0.5)
