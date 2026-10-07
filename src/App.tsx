import React, { useState } from "react";
import { Navbar } from "./components/Navbar";
import { ConsensusLab } from "./components/ConsensusLab";
import { BlockchainExplorer } from "./components/BlockchainExplorer";
import { NetworkVisualizer } from "./components/NetworkVisualizer";
import { WalletStudio } from "./components/WalletStudio";
import { CliTerminal } from "./components/CliTerminal";
import { CodeBrowser } from "./components/CodeBrowser";
import { INITIAL_BLOCKS } from "./data/mockChain";
import { BlockData } from "./types/blockchain";
import { sha256Hex } from "./utils/consensusHelper";

export default function App() {
  const [activeTab, setActiveTab] = useState<string>("consensus");
  const [blocks, setBlocks] = useState<BlockData[]>(INITIAL_BLOCKS);
  const [difficulty, setDifficulty] = useState<number>(2.0);

  const tipBlock = blocks[blocks.length - 1];
  const tipHash = tipBlock.hash;
  const currentHeight = blocks.length - 1;
  const cumulativeWork = blocks.reduce((acc, b) => acc + b.header.difficulty, 0);

  // When a block is mined from the ConsensusLab
  const handleBlockMined = async (foundSolution: any) => {
    const newHeight = currentHeight + 1;
    const timeNow = Math.floor(Date.now() / 1000);
    const prevHash = tipHash;
    const minerPubkey = foundSolution.minerPubkey;
    const merkleRoot = "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef";

    const headerPayload = `${prevHash}:${merkleRoot}:${timeNow}:${difficulty}:${foundSolution.nonce}`;
    const newHash = await sha256Hex(headerPayload);

    const newBlock: BlockData = {
      hash: newHash,
      height: newHeight,
      cumulative_work: cumulativeWork + difficulty,
      header: {
        version: 1,
        prev_hash: prevHash,
        merkle_root: merkleRoot,
        timestamp: timeNow,
        difficulty,
        nonce: foundSolution.nonce,
        miner_pubkey: minerPubkey,
        solution: {
          chain_type: foundSolution.chainKind,
          origin: foundSolution.origin.toString(),
          length: foundSolution.length,
          primes: foundSolution.primes.map((p: any) => p.toString()),
        },
      },
      transactions: [
        {
          txid: "cb_" + newHash.slice(0, 32),
          version: 1,
          is_coinbase: true,
          locktime: 0,
          inputs: [
            {
              prev_txid: "0000000000000000000000000000000000000000000000000000000000000000",
              vout: 4294967295,
              signature: `coinbase_h_${newHeight}`,
              pubkey: "",
            },
          ],
          outputs: [
            {
              amount: 5000000000, // 50 ProofCoins
              address: "PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm",
            },
          ],
        },
      ],
    };

    setBlocks((prev) => [...prev, newBlock]);
  };

  // When a transaction is sent from the Wallet Studio
  const handleSendTx = (txData: any) => {
    // Add transaction to tip block
    setBlocks((prev) => {
      const updated = [...prev];
      const last = { ...updated[updated.length - 1] };
      const newTx = {
        txid: txData.txid,
        version: 1,
        is_coinbase: false,
        locktime: 0,
        inputs: [
          {
            prev_txid: "9d368e5e8e815e9e0d1645e0fbba086ba9741e974e62ebad503d40a2bbce03e7",
            vout: 0,
            signature: "ed25519_signed_in_browser",
            pubkey: "0202020202020202020202020202020202020202020202020202020202020202",
          },
        ],
        outputs: [
          {
            amount: txData.amount,
            address: txData.to,
          },
        ],
      };
      last.transactions = [...last.transactions, newTx];
      updated[updated.length - 1] = last;
      return updated;
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-600 selection:text-white">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        height={currentHeight}
        difficulty={difficulty}
        cumulativeWork={cumulativeWork}
        isMining={false}
      />

      {/* Main Tab View */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "consensus" && (
          <ConsensusLab
            onBlockMined={handleBlockMined}
            currentHeight={currentHeight}
            tipHash={tipHash}
          />
        )}

        {activeTab === "explorer" && <BlockchainExplorer blocks={blocks} />}

        {activeTab === "network" && <NetworkVisualizer />}

        {activeTab === "wallet" && <WalletStudio onSendTx={handleSendTx} />}

        {activeTab === "cli" && (
          <CliTerminal
            chainHeight={currentHeight}
            tipHash={tipHash}
            difficulty={difficulty}
          />
        )}

        {activeTab === "code" && <CodeBrowser />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500 font-mono">
        ProofCoin Prototype v0.1.0 • Proof of Useful Work (Cunningham Prime Chains) • Python 3.11 Protocol Core • Ed25519 Cryptography
      </footer>
    </div>
  );
}
