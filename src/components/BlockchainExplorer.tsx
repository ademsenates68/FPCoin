import React, { useState } from "react";
import { 
  Layers, 
  Search, 
  ArrowRight, 
  Hash, 
  Clock, 
  Cpu, 
  Coins, 
  CheckCircle2, 
  Database,
  ExternalLink,
  ShieldCheck,
  ChevronRight
} from "lucide-react";
import { BlockData, TransactionData } from "../types/blockchain";
import { formatCoins, formatHash } from "../utils/consensusHelper";

interface BlockchainExplorerProps {
  blocks: BlockData[];
}

export const BlockchainExplorer: React.FC<BlockchainExplorerProps> = ({ blocks }) => {
  const [selectedBlock, setSelectedBlock] = useState<BlockData>(blocks[blocks.length - 1] || blocks[0]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"blocks" | "utxo">("blocks");

  // Filter blocks
  const filteredBlocks = blocks.filter((b) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      b.height.toString() === q ||
      b.hash.toLowerCase().includes(q) ||
      b.header.merkle_root.toLowerCase().includes(q)
    );
  });

  // Collect all UTXOs from blocks
  const allUtxos: { txid: string; vout: number; amount: number; address: string; height: number }[] = [];
  const spentOutpoints = new Set<string>();

  // Collect spends
  for (const blk of blocks) {
    for (const tx of blk.transactions) {
      if (!tx.is_coinbase) {
        for (const inp of tx.inputs) {
          spentOutpoints.add(`${inp.prev_txid}:${inp.vout}`);
        }
      }
    }
  }

  // Collect active outputs
  for (const blk of blocks) {
    for (const tx of blk.transactions) {
      tx.outputs.forEach((out, vout) => {
        const key = `${tx.txid}:${vout}`;
        if (!spentOutpoints.has(key)) {
          allUtxos.push({
            txid: tx.txid,
            vout,
            amount: out.amount,
            address: out.address,
            height: blk.height,
          });
        }
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Search & Tabs Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveTab("blocks")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "blocks"
                ? "bg-indigo-600 text-white shadow"
                : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Blocks & Transactions ({blocks.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("utxo")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "utxo"
                ? "bg-indigo-600 text-white shadow"
                : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Active UTXO Ledger ({allUtxos.length})</span>
          </button>
        </div>

        <div className="relative max-w-sm w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search block height or hash..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {activeTab === "blocks" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Block List */}
          <div className="lg:col-span-5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
              Confirmed Blocks (Ordered by Height)
            </h3>

            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
              {filteredBlocks.map((blk) => {
                const isSelected = selectedBlock?.hash === blk.hash;
                return (
                  <div
                    key={blk.hash}
                    onClick={() => setSelectedBlock(blk)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? "bg-indigo-950/40 border-indigo-500/80 shadow-md shadow-indigo-500/10"
                        : "bg-slate-900 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-sm font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                          #{blk.height}
                        </span>
                        <span className="text-xs text-slate-400">
                          {blk.height === 0 ? "Genesis Block" : `${blk.transactions.length} txs`}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-900/60">
                        Diff: {blk.header.difficulty.toFixed(1)}
                      </span>
                    </div>

                    <div className="font-mono text-xs text-cyan-400 truncate mb-2">
                      {blk.hash}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
                      <span>PoUW: {blk.header.solution.chain_type} (k={blk.header.solution.length})</span>
                      <span>Nonce: {blk.header.nonce}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Selected Block Details */}
          <div className="lg:col-span-7 space-y-4">
            {selectedBlock ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                  <div>
                    <div className="text-xs text-indigo-400 font-semibold uppercase tracking-wider">
                      Block Inspector
                    </div>
                    <h3 className="text-xl font-bold text-white font-mono">
                      Block #{selectedBlock.height}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Cumulative Work</span>
                    <span className="font-mono text-sm font-bold text-cyan-400">
                      {selectedBlock.cumulative_work.toFixed(1)}
                    </span>
                  </div>
                </div>

                {/* Header Metadata Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block mb-1">Block Hash</span>
                    <span className="text-cyan-300 break-all">{selectedBlock.hash}</span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block mb-1">Previous Hash</span>
                    <span className="text-slate-300 break-all">{selectedBlock.header.prev_hash}</span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block mb-1">Merkle Root</span>
                    <span className="text-amber-300 break-all">{selectedBlock.header.merkle_root}</span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block mb-1">Timestamp & Nonce</span>
                    <span className="text-slate-200">
                      {new Date(selectedBlock.header.timestamp * 1000).toUTCString()} (Nonce: {selectedBlock.header.nonce})
                    </span>
                  </div>
                </div>

                {/* Cunningham PoUW Solution Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-indigo-400 flex items-center space-x-1.5">
                      <Cpu className="w-4 h-4" />
                      <span>Cunningham Proof of Useful Work Proof</span>
                    </span>
                    <span className="font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-900/60">
                      Verified {selectedBlock.header.solution.chain_type} Chain
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs font-mono">
                    <div className="text-slate-400 text-[11px]">
                      Origin Prime p_0: <span className="text-emerald-400 font-bold">{selectedBlock.header.solution.origin}</span>
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {selectedBlock.header.solution.primes.map((prime, idx) => (
                        <span
                          key={idx}
                          className="bg-slate-900 border border-slate-800 px-2.5 py-1 rounded text-cyan-300 text-[11px]"
                        >
                          p_{idx}: {prime}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Transactions in Block */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Transactions ({selectedBlock.transactions.length})</span>
                    <span className="text-emerald-400">All Signatures Validated</span>
                  </h4>

                  <div className="space-y-3">
                    {selectedBlock.transactions.map((tx) => (
                      <div
                        key={tx.txid}
                        className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-3 text-xs font-mono"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800/80 pb-2 gap-1">
                          <span className="text-cyan-400 truncate max-w-sm">TxID: {tx.txid}</span>
                          <span className="text-[11px] text-amber-400 bg-amber-950/50 px-2 py-0.5 rounded border border-amber-900/50">
                            {tx.is_coinbase ? "Coinbase (New Emission + Fees)" : "Standard UTXO Transfer"}
                          </span>
                        </div>

                        {/* Inputs & Outputs Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
                          {/* Inputs */}
                          <div className="space-y-1">
                            <span className="text-slate-400 font-semibold block">Inputs:</span>
                            {tx.inputs.map((inp, idx) => (
                              <div key={idx} className="bg-slate-900 p-2 rounded text-slate-300">
                                {tx.is_coinbase ? (
                                  <span className="text-slate-500">Coinbase Subsidy (Height {selectedBlock.height})</span>
                                ) : (
                                  <div>
                                    <span className="text-indigo-400">Outpoint:</span> {formatHash(inp.prev_txid, 6)}:{inp.vout}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Outputs */}
                          <div className="space-y-1">
                            <span className="text-slate-400 font-semibold block">Outputs:</span>
                            {tx.outputs.map((out, idx) => (
                              <div key={idx} className="bg-slate-900 p-2 rounded flex justify-between items-center text-slate-300">
                                <span className="text-slate-400 truncate max-w-[140px]">{out.address}</span>
                                <span className="text-emerald-400 font-bold">
                                  {formatCoins(out.amount)} PC
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        /* UTXO Ledger Tab */
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-bold text-white">Active UTXO Ledger View</h3>
              <p className="text-xs text-slate-400">All unspent coin outputs currently valid for transaction spending.</p>
            </div>
            <div className="text-right font-mono text-xs">
              <span className="text-slate-400">Circulating Supply: </span>
              <span className="text-emerald-400 font-bold">
                {formatCoins(allUtxos.reduce((acc, u) => acc + u.amount, 0))} ProofCoins
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                  <th className="py-2.5 px-3">Block</th>
                  <th className="py-2.5 px-3">Transaction ID</th>
                  <th className="py-2.5 px-3">Vout</th>
                  <th className="py-2.5 px-3">Owner Address</th>
                  <th className="py-2.5 px-3 text-right">Amount (PC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {allUtxos.map((utxo, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 px-3 text-indigo-400 font-bold">#{utxo.height}</td>
                    <td className="py-2.5 px-3 text-cyan-400">{formatHash(utxo.txid, 8)}</td>
                    <td className="py-2.5 px-3 text-slate-400">{utxo.vout}</td>
                    <td className="py-2.5 px-3 text-slate-300">{utxo.address}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                      {formatCoins(utxo.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
