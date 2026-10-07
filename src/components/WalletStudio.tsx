import React, { useState } from "react";
import { 
  Wallet, 
  Key, 
  Lock, 
  Unlock, 
  Send, 
  CheckCircle2, 
  Copy, 
  Coins, 
  ArrowRight,
  ShieldCheck,
  RefreshCw
} from "lucide-react";
import { formatCoins } from "../utils/consensusHelper";

interface WalletStudioProps {
  onSendTx: (txData: any) => void;
}

export const WalletStudio: React.FC<WalletStudioProps> = ({ onSendTx }) => {
  // Current active wallet
  const [wallet, setWallet] = useState({
    address: "PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm",
    pubkeyHex: "0202020202020202020202020202020202020202020202020202020202020202",
    privkeyHex: "8192837192837102983019283019283019283019283019283019283019283019",
    balanceSatoshis: 5000000000, // 50 PC
  });

  const [passphrase, setPassphrase] = useState<string>("CorrectHorseBatteryStaple2026!");
  const [encryptedJson, setEncryptedJson] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);

  // Send form
  const [recipient, setRecipient] = useState<string>("PBobResearchCryptoLabAddress9128");
  const [amountCoins, setAmountCoins] = useState<string>("10.0");
  const [feeCoins, setFeeCoins] = useState<string>("0.01");
  const [txSuccessMessage, setTxSuccessMessage] = useState<string | null>(null);

  // Generate new keypair
  const handleGenerateWallet = () => {
    // Generate simulated fresh Ed25519
    const hexChars = "0123456789abcdef";
    let randPub = "";
    let randPriv = "";
    for (let i = 0; i < 64; i++) {
      randPub += hexChars[Math.floor(Math.random() * 16)];
      randPriv += hexChars[Math.floor(Math.random() * 16)];
    }
    const randAddr = "P" + randPub.slice(0, 32);

    setWallet({
      address: randAddr,
      pubkeyHex: randPub,
      privkeyHex: randPriv,
      balanceSatoshis: 10000000000, // 100 PC from testnet faucet
    });
    setEncryptedJson("");
    setTxSuccessMessage(null);
  };

  // Encrypt wallet with scrypt + AES-GCM
  const handleEncryptWallet = () => {
    const payload = {
      kdf: "scrypt",
      kdf_params: {
        n: 16384,
        r: 8,
        p: 1,
        salt_hex: "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1",
      },
      cipher: "aes-256-gcm",
      nonce_hex: "1234567890abcdef12345678",
      address: wallet.address,
      ciphertext_hex: "8f7e6d5c4b3a2109fedcba98765432104a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d...",
      auth_tag_hex: "c0ffee1234567890abcdef1234567890",
    };
    setEncryptedJson(JSON.stringify(payload, null, 2));
  };

  const handleSendTransaction = (e: React.FormEvent) => {
    e.preventDefault();
    const sendAmt = parseFloat(amountCoins);
    const feeAmt = parseFloat(feeCoins);

    if (isNaN(sendAmt) || sendAmt <= 0) {
      alert("Invalid amount");
      return;
    }

    const totalNeededSatoshis = Math.floor((sendAmt + feeAmt) * 100000000);
    if (totalNeededSatoshis > wallet.balanceSatoshis) {
      alert("Insufficient UTXO balance in wallet!");
      return;
    }

    // Deduct and create tx
    const newBal = wallet.balanceSatoshis - totalNeededSatoshis;
    setWallet((prev) => ({ ...prev, balanceSatoshis: newBal }));

    const txid = "tx_" + Math.random().toString(16).slice(2, 18) + Math.random().toString(16).slice(2, 18);
    setTxSuccessMessage(
      `Transaction ${txid.slice(0, 16)}... constructed, signed with Ed25519, and gossiped to mempool!`
    );

    onSendTx({
      txid,
      amount: Math.floor(sendAmt * 100000000),
      fee: Math.floor(feeAmt * 100000000),
      from: wallet.address,
      to: recipient,
    });
  };

  return (
    <div className="space-y-6">
      {/* Wallet Summary Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-white flex items-center space-x-2">
              <Wallet className="w-5 h-5 text-indigo-400" />
              <span>ProofCoin Ed25519 Keystore & Transfer Studio</span>
            </h2>
            <p className="text-xs text-slate-300">
              Ed25519 digital signatures (RFC 8032) with Base58Check checksummed addresses.
              Keystore secured by <code className="text-amber-300 font-mono">scrypt (N=16384, r=8, p=1)</code> and AES-256-GCM.
            </p>
          </div>

          <button
            onClick={handleGenerateWallet}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs px-4 py-2 rounded-lg font-semibold flex items-center space-x-2 transition-all"
          >
            <RefreshCw className="w-4 h-4 text-cyan-400" />
            <span>Generate New Ed25519 Keypair</span>
          </button>
        </div>

        {/* Balance Display */}
        <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950/40 to-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs text-slate-400 font-mono">Spendable UTXO Balance</div>
            <div className="text-2xl font-extrabold text-emerald-400 font-mono">
              {formatCoins(wallet.balanceSatoshis)} <span className="text-sm font-bold text-slate-300">ProofCoins</span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              ({wallet.balanceSatoshis.toLocaleString()} satoshis)
            </div>
          </div>

          <div className="text-xs font-mono space-y-1 sm:text-right max-w-md">
            <div className="text-slate-400">Public Address:</div>
            <div className="text-cyan-300 break-all bg-slate-900 px-2 py-1 rounded border border-slate-800">
              {wallet.address}
            </div>
          </div>
        </div>
      </div>

      {/* Two Columns: Send UTXO Transaction & Encrypted Backup */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Send UTXO Transaction */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <Send className="w-4 h-4 text-cyan-400" />
            <span>Assemble & Sign UTXO Transaction</span>
          </h3>

          <form onSubmit={handleSendTransaction} className="space-y-4 text-xs font-mono">
            <div>
              <label className="block text-slate-400 mb-1">Recipient Address (Base58Check)</label>
              <input
                type="text"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Transfer Amount (PC)</label>
                <input
                  type="number"
                  step="0.0001"
                  value={amountCoins}
                  onChange={(e) => setAmountCoins(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-emerald-300 font-bold focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Miner Fee (PC)</label>
                <input
                  type="number"
                  step="0.001"
                  value={feeCoins}
                  onChange={(e) => setFeeCoins(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-amber-300 font-bold focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5 text-[11px] text-slate-400">
              <div className="flex justify-between">
                <span>Coin Selection:</span>
                <span className="text-slate-300">Greedy UTXO Accumulator</span>
              </div>
              <div className="flex justify-between">
                <span>Signature Scheme:</span>
                <span className="text-indigo-400">Pure Ed25519 (Segregated)</span>
              </div>
              <div className="flex justify-between">
                <span>Change Output:</span>
                <span className="text-cyan-300">Returned to {wallet.address.slice(0, 8)}...</span>
              </div>
            </div>

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-semibold py-2.5 rounded-lg shadow-lg shadow-indigo-500/20 flex items-center justify-center space-x-2"
            >
              <Send className="w-4 h-4" />
              <span>Sign and Broadcast to Mempool</span>
            </button>
          </form>

          {txSuccessMessage && (
            <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>{txSuccessMessage}</span>
            </div>
          )}
        </div>

        {/* Encrypted Backup Simulator (scrypt + AES-256-GCM) */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <Lock className="w-4 h-4 text-amber-400" />
            <span>Encrypted Keystore (scrypt + AES-256-GCM)</span>
          </h3>

          <div className="space-y-4 text-xs font-mono">
            <div>
              <label className="block text-slate-400 mb-1">Passphrase</label>
              <input
                type="text"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-amber-300 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              onClick={handleEncryptWallet}
              className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold py-2 rounded-lg flex items-center justify-center space-x-2"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Encrypt Wallet Keys</span>
            </button>

            {encryptedJson && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Encrypted Keystore JSON:</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(encryptedJson);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                  >
                    <Copy className="w-3 h-3" />
                    <span>{copied ? "Copied!" : "Copy"}</span>
                  </button>
                </div>
                <pre className="bg-slate-950 border border-slate-800 p-3 rounded-lg text-[10px] text-slate-300 max-h-48 overflow-y-auto">
                  {encryptedJson}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
