import React, { useState } from "react";
import { 
  Network, 
  Server, 
  ShieldAlert, 
  ShieldCheck, 
  Radio, 
  Activity, 
  Send, 
  CheckCircle2, 
  AlertTriangle,
  ArrowRightLeft
} from "lucide-react";
import { PeerNodeInfo } from "../types/blockchain";
import { INITIAL_PEERS } from "../data/mockChain";

export const NetworkVisualizer: React.FC = () => {
  const [peers, setPeers] = useState<PeerNodeInfo[]>(INITIAL_PEERS);
  const [gossipLogs, setGossipLogs] = useState<Array<{
    id: string;
    timestamp: string;
    type: "block" | "tx" | "handshake" | "ban";
    source: string;
    target: string;
    payload: string;
  }>>([
    {
      id: "1",
      timestamp: "12:00:01",
      type: "handshake",
      source: "Node-1 (9333)",
      target: "Node-2 (9334)",
      payload: "VERSION handshake (Best Height: 2, Magic: PROF)",
    },
    {
      id: "2",
      timestamp: "12:00:02",
      type: "handshake",
      source: "Node-2 (9334)",
      target: "Node-1 (9333)",
      payload: "VERACK accepted, socket established",
    },
    {
      id: "3",
      timestamp: "12:00:15",
      type: "tx",
      source: "Node-1 (9333)",
      target: "Node-2 (9334)",
      payload: "Gossip TX: d8192736... (Fee: 0.05 PC)",
    },
    {
      id: "4",
      timestamp: "12:00:22",
      type: "block",
      source: "Node-2 (9334)",
      target: "Node-1 & Node-3",
      payload: "Gossip Block #2: 0009c910... (1CC Chain k=3)",
    },
  ]);

  const [simulatedAttackerScore, setSimulatedAttackerScore] = useState<number>(0);

  const handleSimulateGossip = (type: "block" | "tx") => {
    const time = new Date().toLocaleTimeString();
    const newLog = {
      id: Math.random().toString(),
      timestamp: time,
      type,
      source: "Node-1 (Frankfurt)",
      target: "Node-2 & Node-3",
      payload: type === "block" 
        ? "Broadcast newly verified PoUW block across mesh (2MB limit checked)"
        : "Gossip unconfirmed UTXO transaction to peer mempools",
    };
    setGossipLogs((prev) => [newLog, ...prev.slice(0, 15)]);
  };

  const handleSimulateMaliciousAttack = () => {
    const newScore = simulatedAttackerScore + 100;
    setSimulatedAttackerScore(newScore);

    const time = new Date().toLocaleTimeString();
    const attackLog = {
      id: Math.random().toString(),
      timestamp: time,
      type: "ban" as const,
      source: "Rogue-Peer (203.0.113.88)",
      target: "Node-1",
      payload: "Sent corrupted block with fake Cunningham chain -> Misbehavior score +100 -> AUTO-BANNED (24-hour quarantine)",
    };
    setGossipLogs((prev) => [attackLog, ...prev.slice(0, 15)]);

    // Update Node-1 banned list
    setPeers((prev) =>
      prev.map((p) =>
        p.id === "node-1"
          ? { ...p, bannedIps: [...p.bannedIps, "203.0.113.88"] }
          : p
      )
    );
  };

  return (
    <div className="space-y-6">
      {/* Network Overview Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-white flex items-center space-x-2">
              <Network className="w-5 h-5 text-indigo-400" />
              <span>3-Node Asyncio P2P Mesh Topology</span>
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl">
              Fully asynchronous TCP network engine using Python's <code className="text-cyan-300">asyncio</code>.
              Features Bitcoin-style binary framing (<code className="text-amber-300">PROF</code> magic, 2MB size limit),
              inventory gossip, and automated peer scoring to eliminate DoS attacks.
            </p>
          </div>

          <div className="flex space-x-2">
            <button
              onClick={() => handleSimulateGossip("tx")}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs px-3 py-2 rounded-lg font-medium flex items-center space-x-1.5 transition-all"
            >
              <Send className="w-3.5 h-3.5 text-cyan-400" />
              <span>Gossip TX</span>
            </button>
            <button
              onClick={() => handleSimulateGossip("block")}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-2 rounded-lg font-medium flex items-center space-x-1.5 shadow transition-all"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Gossip Block</span>
            </button>
            <button
              onClick={handleSimulateMaliciousAttack}
              className="bg-rose-950/80 hover:bg-rose-900/80 text-rose-300 border border-rose-800 text-xs px-3 py-2 rounded-lg font-medium flex items-center space-x-1.5 transition-all"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Trigger Peer Ban Test</span>
            </button>
          </div>
        </div>
      </div>

      {/* Nodes Mesh Topology Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {peers.map((node) => (
          <div
            key={node.id}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 hover:border-slate-700 transition-all shadow-md"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="h-8 w-8 rounded-lg bg-indigo-950 flex items-center justify-center border border-indigo-800/60 text-indigo-400">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white">{node.name}</h4>
                  <span className="text-[11px] font-mono text-slate-400">
                    {node.host}:{node.port}
                  </span>
                </div>
              </div>
              <span className="text-[10px] font-mono uppercase bg-emerald-950/80 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full flex items-center space-x-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>{node.status}</span>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-slate-800">
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <span className="text-slate-500 text-[10px] block">Ledger Height</span>
                <span className="text-indigo-300 font-bold">#{node.height}</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <span className="text-slate-500 text-[10px] block">Connected Peers</span>
                <span className="text-cyan-300 font-bold">{node.peersCount} nodes</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <span className="text-slate-500 text-[10px] block">Mempool Txs</span>
                <span className="text-amber-300 font-bold">{node.mempoolCount} pending</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <span className="text-slate-500 text-[10px] block">Banned IPs</span>
                <span className={`font-bold ${node.bannedIps.length > 0 ? "text-rose-400" : "text-slate-400"}`}>
                  {node.bannedIps.length} blocked
                </span>
              </div>
            </div>

            {node.bannedIps.length > 0 && (
              <div className="text-[11px] font-mono text-rose-300 bg-rose-950/30 p-2 rounded border border-rose-900/40">
                Blocked IPs: {node.bannedIps.join(", ")}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Real-time Gossip Activity Log */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center justify-between">
          <span className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            <span>P2P Gossip Traffic & Wire Protocol Log</span>
          </span>
          <span className="text-xs text-slate-400 font-mono">Frame Magic: 0x50524F46 (PROF)</span>
        </h3>

        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs space-y-2 max-h-72 overflow-y-auto">
          {gossipLogs.map((log) => {
            const isBan = log.type === "ban";
            return (
              <div
                key={log.id}
                className={`p-2 rounded border flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] ${
                  isBan
                    ? "bg-rose-950/30 border-rose-900/60 text-rose-300"
                    : "bg-slate-900/60 border-slate-800 text-slate-300"
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className="text-slate-500">[{log.timestamp}]</span>
                  <span className={`uppercase font-bold text-[10px] px-1.5 py-0.2 rounded ${
                    isBan ? "bg-rose-900 text-rose-200" : "bg-slate-800 text-cyan-300"
                  }`}>
                    {log.type}
                  </span>
                  <span className="text-slate-200">{log.payload}</span>
                </div>
                <div className="text-slate-500 text-[10px]">
                  {log.source} ➔ {log.target}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
