import React from "react";
import { 
  Cpu, 
  Layers, 
  Network, 
  Wallet, 
  Terminal, 
  FileCode, 
  ShieldCheck,
  Zap,
  TrendingUp
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  height: number;
  difficulty: number;
  cumulativeWork: number;
  isMining: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  height,
  difficulty,
  cumulativeWork,
  isMining,
}) => {
  const tabs = [
    { id: "consensus", label: "Consensus & PoUW Lab", icon: Cpu },
    { id: "explorer", label: "Blockchain Explorer", icon: Layers },
    { id: "network", label: "P2P Mesh (3-Node)", icon: Network },
    { id: "wallet", label: "Wallet & UTXO Studio", icon: Wallet },
    { id: "cli", label: "CLI Terminal", icon: Terminal },
    { id: "code", label: "Codebase & Tests", icon: FileCode },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-slate-100 sticky top-0 z-50 shadow-md">
      {/* Top Banner Stats */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between border-b border-slate-800/80 text-xs text-slate-400">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 font-medium text-emerald-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>Testnet v0.1.0 • P2P Active</span>
          </div>
          <span className="text-slate-600">|</span>
          <span className="font-mono text-slate-300">PoUW: Cunningham Prime Chains (1CC & 2CC)</span>
        </div>

        <div className="flex items-center space-x-4 mt-1 sm:mt-0 font-mono">
          <div className="flex items-center space-x-1 bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400">Height:</span>
            <span className="text-indigo-300 font-bold">#{height}</span>
          </div>

          <div className="flex items-center space-x-1 bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-400">Diff:</span>
            <span className="text-amber-300 font-bold">{difficulty.toFixed(1)}</span>
          </div>

          <div className="flex items-center space-x-1 bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
            <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Work:</span>
            <span className="text-cyan-300 font-bold">{cumulativeWork.toFixed(1)}</span>
          </div>

          {isMining && (
            <div className="flex items-center space-x-1 bg-amber-950/60 text-amber-300 px-2 py-0.5 rounded border border-amber-800 animate-pulse">
              <Cpu className="w-3.5 h-3.5 animate-spin" />
              <span>Mining Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-indigo-500/20 shadow-md">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-base tracking-tight bg-gradient-to-r from-white via-indigo-100 to-indigo-300 bg-clip-text text-transparent">
                ProofCoin
              </span>
              <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-cyan-400 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800">
                PoUW Core
              </span>
            </div>
          </div>

          {/* Nav Tabs */}
          <nav className="flex space-x-1 overflow-x-auto py-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/30"
                      : "text-slate-300 hover:text-white hover:bg-slate-800/80"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
};
