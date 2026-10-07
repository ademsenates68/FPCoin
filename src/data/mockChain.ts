import { BlockData, PeerNodeInfo } from "../types/blockchain";

export const INITIAL_BLOCKS: BlockData[] = [
  {
    hash: "0004f810a9c2409b307d4b476495b452d3a39e7829beff38b9d7ef710a379102",
    height: 0,
    cumulative_work: 2.0,
    header: {
      version: 1,
      prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
      merkle_root: "9d368e5e8e815e9e0d1645e0fbba086ba9741e974e62ebad503d40a2bbce03e7",
      timestamp: 1700000000,
      difficulty: 2.0,
      nonce: 58,
      miner_pubkey: "0202020202020202020202020202020202020202020202020202020202020202",
      solution: {
        chain_type: "2CC",
        origin: "606419199499",
        length: 2,
        primes: ["606419199499", "1212838398997"],
      },
    },
    transactions: [
      {
        txid: "9d368e5e8e815e9e0d1645e0fbba086ba9741e974e62ebad503d40a2bbce03e7",
        version: 1,
        is_coinbase: true,
        locktime: 0,
        inputs: [
          {
            prev_txid: "0000000000000000000000000000000000000000000000000000000000000000",
            vout: 4294967295,
            signature: "coinbase_genesis_h0",
            pubkey: "",
          },
        ],
        outputs: [
          {
            amount: 5000000000, // 50.0 ProofCoins
            address: "PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm",
          },
        ],
      },
    ],
  },
  {
    hash: "0007e129fca9473b110bc6349d799014529bcff710928aa4501b87612c408103",
    height: 1,
    cumulative_work: 4.0,
    header: {
      version: 1,
      prev_hash: "0004f810a9c2409b307d4b476495b452d3a39e7829beff38b9d7ef710a379102",
      merkle_root: "6148a209b55f19087ea7f71ba5e56e0772d1a3a4c0429f63503f5ad6a81b2390",
      timestamp: 1700000060,
      difficulty: 2.0,
      nonce: 142,
      miner_pubkey: "a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
      solution: {
        chain_type: "1CC",
        origin: "408192318047",
        length: 2,
        primes: ["408192318047", "816384636095"],
      },
    },
    transactions: [
      {
        txid: "6148a209b55f19087ea7f71ba5e56e0772d1a3a4c0429f63503f5ad6a81b2390",
        version: 1,
        is_coinbase: true,
        locktime: 0,
        inputs: [
          {
            prev_txid: "0000000000000000000000000000000000000000000000000000000000000000",
            vout: 4294967295,
            signature: "coinbase_h_1",
            pubkey: "",
          },
        ],
        outputs: [
          {
            amount: 5000000000,
            address: "PNakamm68p13xWkY8aBqR3cTqB9xV9u22a",
          },
        ],
      },
    ],
  },
  {
    hash: "0009c9104bc1298ef91823bb4109726ea89104fae10986bc411082348c201994",
    height: 2,
    cumulative_work: 6.0,
    header: {
      version: 1,
      prev_hash: "0007e129fca9473b110bc6349d799014529bcff710928aa4501b87612c408103",
      merkle_root: "f928e190471b802a99e82937016abef9120938b81920cae91823091bbff10293",
      timestamp: 1700000122,
      difficulty: 2.0,
      nonce: 319,
      miner_pubkey: "b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2",
      solution: {
        chain_type: "1CC",
        origin: "112839102919",
        length: 3,
        primes: ["112839102919", "225678205839", "451356411679"],
      },
    },
    transactions: [
      {
        txid: "c18293b019827361908236109283719082736192837162938172639182736192",
        version: 1,
        is_coinbase: true,
        locktime: 0,
        inputs: [
          {
            prev_txid: "0000000000000000000000000000000000000000000000000000000000000000",
            vout: 4294967295,
            signature: "coinbase_h_2",
            pubkey: "",
          },
        ],
        outputs: [
          {
            amount: 5005000000,
            address: "PEulerPrimesFoundation2026Crypto192",
          },
        ],
      },
      {
        txid: "d819273610928371928371629381726391827361928371629381726391827361",
        version: 1,
        is_coinbase: false,
        locktime: 0,
        inputs: [
          {
            prev_txid: "9d368e5e8e815e9e0d1645e0fbba086ba9741e974e62ebad503d40a2bbce03e7",
            vout: 0,
            signature: "ed25519_sig_valid_verified_729183019283",
            pubkey: "0202020202020202020202020202020202020202020202020202020202020202",
          },
        ],
        outputs: [
          {
            amount: 1500000000,
            address: "PBobResearchCryptoLabAddress9128",
          },
          {
            amount: 3495000000,
            address: "PDehrMDtUFpJMwsVjYC3aGoKQPcrwwQZUm",
          },
        ],
      },
    ],
  },
];

export const INITIAL_PEERS: PeerNodeInfo[] = [
  {
    id: "node-1",
    name: "ProofCoin-Seed-Node-1 (Frankfurt)",
    host: "127.0.0.1",
    port: 9333,
    height: 2,
    peersCount: 8,
    mempoolCount: 2,
    bannedIps: [],
    status: "active",
  },
  {
    id: "node-2",
    name: "ProofCoin-Miner-Rig-Alpha (Reykjavik)",
    host: "127.0.0.1",
    port: 9334,
    height: 2,
    peersCount: 12,
    mempoolCount: 2,
    bannedIps: ["203.0.113.44"],
    status: "mining",
  },
  {
    id: "node-3",
    name: "ProofCoin-FullNode-Archive (Tokyo)",
    host: "127.0.0.1",
    port: 9335,
    height: 2,
    peersCount: 6,
    mempoolCount: 2,
    bannedIps: [],
    status: "syncing",
  },
];
