"""
Integration Tests for 3-Node Asyncio P2P Network Simulation.
"""

import asyncio
from proofcoin.crypto.keys import generate_keypair, sign_data
from proofcoin.crypto.address import pubkey_to_address
from proofcoin.core.transaction import COIN, Transaction, TxInput, TxOutput
from proofcoin.core.block import BlockHeader, Block
from proofcoin.consensus.cunningham import CunninghamChain, ChainType
from proofcoin.network.node import P2PNode
from proofcoin.network.protocol import MessageType


def test_three_node_network_simulation():
    """
    Spawns 3 local P2P nodes (Node A, Node B, Node C).
    - Node A connects to Node B
    - Node B connects to Node C
    - Node A gossips transaction -> propagates to Node B
    - Tests peer banning on malicious block transmission
    """
    async def _run():
        node_a = P2PNode(host="127.0.0.1", port=9441)
        node_b = P2PNode(host="127.0.0.1", port=9442)
        node_c = P2PNode(host="127.0.0.1", port=9443)

        try:
            # 1. Start servers
            await node_a.start()
            await node_b.start()
            await node_c.start()

            # 2. Establish connections: A -> B, B -> C
            connected_ab = await node_a.connect_to_peer("127.0.0.1", 9442)
            assert connected_ab is True

            connected_bc = await node_b.connect_to_peer("127.0.0.1", 9443)
            assert connected_bc is True

            # Allow handshakes (VERSION/VERACK) to settle
            await asyncio.sleep(0.3)

            assert len(node_a.peers) >= 1
            assert len(node_b.peers) >= 1

            # 3. Create a valid transaction and broadcast from Node A
            alice_kp = generate_keypair()
            alice_addr = pubkey_to_address(alice_kp.public_key_hex)
            bob_kp = generate_keypair()
            bob_addr = pubkey_to_address(bob_kp.public_key_hex)

            # Seed UTXO into node A and node B blockchain state for test
            test_txid = "ee" * 32
            node_a.blockchain._utxo_set[(test_txid, 0)] = TxOutput(amount=10 * COIN, address=alice_addr)
            node_b.blockchain._utxo_set[(test_txid, 0)] = TxOutput(amount=10 * COIN, address=alice_addr)

            tx = Transaction(
                version=1,
                inputs=[TxInput(prev_txid=test_txid, vout=0, signature="", pubkey=alice_kp.public_key_hex)],
                outputs=[TxOutput(amount=9 * COIN, address=bob_addr)],
            )
            digest = tx.get_signing_digest()
            tx.inputs[0].signature = sign_data(alice_kp.private_key_hex, digest)

            # Node A adds to its mempool and gossips to Node B
            ok, _ = node_a.mempool.add_transaction(tx, node_a.blockchain.utxo_set)
            assert ok is True
            await node_a.broadcast_tx(tx)

            # Wait for gossip transmission
            await asyncio.sleep(0.3)

            # Node B should have received and accepted the transaction into its mempool!
            assert node_b.mempool.contains(tx.txid) is True

            # 4. Test Peer Misbehavior & Ban Mechanism
            # Node A sends a fake, invalid block to Node B
            fake_header = BlockHeader(
                version=1,
                prev_hash=node_b.blockchain.tip_block.block_hash,
                merkle_root="00" * 32,
                timestamp=1700000000,
                difficulty=99.0,
                nonce=1,
                miner_pubkey="02" * 32,
                solution=CunninghamChain(ChainType.FIRST_KIND, 3, 2, [3, 7]),
            )
            fake_block = Block(header=fake_header, transactions=[])

            # Send fake block from Node A to Node B
            peer_to_b = list(node_a.peers.values())[0]
            await peer_to_b.send_message(MessageType.BLOCK, {"block": fake_block.to_dict()})

            # Wait for Node B to inspect and reject
            await asyncio.sleep(0.3)

            # Node B should increase ban score and ban the peer
            assert "127.0.0.1" in node_b.banned_ips

        finally:
            # Gracefully shut down all nodes
            await node_a.stop()
            await node_b.stop()
            await node_c.stop()

    asyncio.run(_run())
