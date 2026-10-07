export interface CunninghamChainData {
  chain_type: "1CC" | "2CC";
  origin: string;
  length: number;
  primes: string[];
}

export interface BlockHeaderData {
  version: number;
  prev_hash: string;
  merkle_root: string;
  timestamp: number;
  difficulty: number;
  nonce: number;
  miner_pubkey: string;
  solution: CunninghamChainData;
}

export interface TxInputData {
  prev_txid: string;
  vout: number;
  signature: string;
  pubkey: string;
}

export interface TxOutputData {
  amount: number; // in atomic satoshis (10^8 = 1 ProofCoin)
  address: string;
}

export interface TransactionData {
  txid: string;
  version: number;
  inputs: TxInputData[];
  outputs: TxOutputData[];
  locktime: number;
  is_coinbase?: boolean;
}

export interface BlockData {
  hash: string;
  height: number;
  header: BlockHeaderData;
  transactions: TransactionData[];
  cumulative_work: number;
}

export interface UTXOItem {
  txid: string;
  vout: number;
  amount: number;
  address: string;
  block_height: number;
}

export interface PeerNodeInfo {
  id: string;
  name: string;
  host: string;
  port: number;
  height: number;
  peersCount: number;
  mempoolCount: number;
  bannedIps: string[];
  status: "active" | "mining" | "syncing";
}
