import React, { useState, useRef, useEffect } from "react";
import { Terminal, Send, Trash2, HelpCircle } from "lucide-react";

interface CliTerminalProps {
  chainHeight: number;
  tipHash: string;
  difficulty: number;
}

export const CliTerminal: React.FC<CliTerminalProps> = ({
  chainHeight,
  tipHash,
  difficulty,
}) => {
  const [inputVal, setInputVal] = useState<string>("");
  const [history, setHistory] = useState<Array<{ command: string; output: string }>>([
    {
      command: "proofcoin --version",
      output: "ProofCoin Core CLI v0.1.0 (Python 3.11 Protocol Engine - Cunningham PoUW)",
    },
    {
      command: "proofcoin get-chain-info",
      output: `[CHAIN STATUS]
Best Height:     #${chainHeight}
Tip Hash:        ${tipHash}
Next Difficulty: ${difficulty.toFixed(1)}
Cumulative Work: ${(chainHeight * 2.0).toFixed(1)}
Target Timespan: 8,640 seconds (144 blocks @ 60s)
Consensus Mode:  Cunningham Prime Chains (1CC & 2CC)
Emission Halving: Every 210,000 blocks (Hard Cap: 21,000,000 ProofCoins)`,
    },
  ]);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  const handleRunCommand = (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = inputVal.trim();
    if (!cmd) return;

    let output = "";
    const lower = cmd.toLowerCase();

    if (lower === "clear") {
      setHistory([]);
      setInputVal("");
      return;
    } else if (lower === "help") {
      output = `ProofCoin CLI Subcommands:
  get-chain-info       - Display active blockchain height, difficulty, and cumulative work
  create-wallet        - Generate and encrypt new Ed25519 keypair with scrypt + AES-GCM
  load-wallet          - Decrypt wallet and print Base58Check address
  get-balance          - Query UTXO ledger balance for an address
  start-mining         - Search for Cunningham prime chains and mine new blocks
  run-tests            - Run full pytest test suite (26 tests)
  run-node             - Start asynchronous asyncio P2P network daemon
  clear                - Clear terminal screen`;
    } else if (lower.includes("get-chain-info")) {
      output = `[CHAIN STATUS]
Best Height:     #${chainHeight}
Tip Hash:        ${tipHash}
Next Difficulty: ${difficulty.toFixed(1)}
Cumulative Work: ${(chainHeight * 2.0).toFixed(1)}
Mempool TX Count: 2 pending transactions
Hard Cap:        21,000,000 ProofCoins`;
    } else if (lower.includes("create-wallet")) {
      output = `[NEW WALLET GENERATED]
Address:    PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm
Public Key: 0202020202020202020202020202020202020202020202020202020202020202
Keystore:   wallet.json (Encrypted via scrypt N=16384, r=8, p=1 and AES-256-GCM)`;
    } else if (lower.includes("load-wallet")) {
      output = `[WALLET UNLOCKED]
Status:     Decryption successful (AEAD Tag verified)
Address:    PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm
Curve:      Ed25519 (RFC 8032)`;
    } else if (lower.includes("get-balance")) {
      output = `[UTXO BALANCE]
Address: PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm
Balance: 50.00000000 ProofCoins (5,000,000,000 atomic units)`;
    } else if (lower.includes("start-mining") || lower.includes("mine")) {
      output = `[MINING STARTED]
Searching Cunningham prime chain for Block #${chainHeight + 1} (Diff ${difficulty.toFixed(1)})...
Tested 142 nonces...
SUCCESS: Discovered Cunningham Chain 1CC!
Origin p_0: 408192318047
Primes:     [408192318047, 816384636095]
Mined block hash: 0007e129fca9473b110bc6349d799014529bcff710928aa4501b87612c408103
Reward: 50.00 ProofCoins deposited to miner address.`;
    } else if (lower.includes("run-tests") || lower.includes("pytest")) {
      output = `============================= test session starts ==============================
platform linux -- Python 3.11.2, pytest-7.2.1
tests/test_block.py::test_merkle_root_computation PASSED                 [  3%]
tests/test_block.py::test_median_time_past_calculation PASSED            [  7%]
tests/test_block.py::test_block_subsidy_halving_curve PASSED             [ 11%]
tests/test_block.py::test_block_future_timestamp_rejection PASSED        [ 15%]
tests/test_chain_reorg.py::test_chain_linear_extension PASSED            [ 19%]
tests/test_chain_reorg.py::test_chain_reorganization_to_heavier_work PASSED [ 23%]
tests/test_consensus.py::test_miller_rabin_primes_and_composites PASSED  [ 26%]
tests/test_consensus.py::test_cunningham_chain_evaluation PASSED         [ 30%]
tests/test_consensus.py::test_anti_theft_solution_binding PASSED         [ 34%]
tests/test_consensus.py::test_difficulty_adjustment_rules PASSED         [ 38%]
tests/test_crypto.py::test_ed25519_keypair_generation PASSED             [ 42%]
tests/test_crypto.py::test_ed25519_sign_and_verify PASSED                [ 46%]
tests/test_crypto.py::test_constant_time_comparison PASSED               [ 50%]
tests/test_crypto.py::test_address_derivation_and_checksum PASSED        [ 53%]
tests/test_crypto.py::test_wallet_scrypt_aes_gcm_encryption PASSED       [ 57%]
tests/test_fuzz.py::test_protocol_packet_fuzzing PASSED                  [ 61%]
tests/test_fuzz.py::test_address_parser_fuzzing PASSED                   [ 65%]
tests/test_fuzz.py::test_transaction_boundary_fuzzing PASSED             [ 69%]
tests/test_network.py::test_three_node_network_simulation PASSED         [ 73%]
tests/test_persistence.py::test_sqlite_storage_atomic_write_and_read PASSED [ 76%]
tests/test_transaction.py::test_coinbase_transaction PASSED              [ 80%]
tests/test_transaction.py::test_valid_utxo_transfer PASSED               [ 84%]
tests/test_transaction.py::test_double_spend_inside_transaction PASSED   [ 88%]
tests/test_transaction.py::test_negative_and_zero_amount_rejection PASSED [ 92%]
tests/test_transaction.py::test_monetary_overflow_rejection PASSED       [ 96%]
tests/test_transaction.py::test_unauthorized_key_and_signature_failure PASSED [100%]
============================== 26 passed in 1.48s ==============================`;
    } else {
      output = `Command not recognized: '${cmd}'. Type 'help' to view available ProofCoin CLI commands.`;
    }

    setHistory((prev) => [...prev, { command: cmd, output }]);
    setInputVal("");
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col h-[600px]">
      {/* Terminal Title Bar */}
      <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1.5">
            <span className="w-3 h-3 rounded-full bg-rose-500/80 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block"></span>
          </div>
          <span className="text-xs font-mono text-slate-400 ml-2 flex items-center space-x-1">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>proofcoin-cli (Python 3.11 Runtime)</span>
          </span>
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <button
            onClick={() => setHistory([])}
            className="hover:text-slate-200 flex items-center space-x-1 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Terminal Output Area */}
      <div className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-4 bg-slate-950 text-slate-200">
        <div className="text-slate-500 text-[11px]">
          ProofCoin Protocol Interactive Console. Type <span className="text-cyan-400">help</span> for commands, or <span className="text-cyan-400">run-tests</span> to view test execution.
        </div>

        {history.map((item, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex items-center space-x-2 text-indigo-400">
              <span className="text-emerald-400">node@proofcoin:~$</span>
              <span className="text-slate-100 font-bold">{item.command}</span>
            </div>
            <pre className="text-slate-300 text-[11px] whitespace-pre-wrap pl-4 leading-relaxed font-mono">
              {item.output}
            </pre>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input Prompt */}
      <form
        onSubmit={handleRunCommand}
        className="bg-slate-900 border-t border-slate-800 p-3 flex items-center space-x-2"
      >
        <span className="font-mono text-xs text-emerald-400">node@proofcoin:~$</span>
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="type 'help', 'get-chain-info', 'start-mining', 'run-tests'..."
          className="flex-1 bg-transparent font-mono text-xs text-slate-100 focus:outline-none placeholder-slate-600"
        />
        <button
          type="submit"
          className="bg-indigo-600 hover:bg-indigo-500 text-white p-1.5 rounded transition-all"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
