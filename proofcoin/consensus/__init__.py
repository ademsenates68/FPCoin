"""
ProofCoin Consensus Engine.
"""

from .prime import is_prime, miller_rabin
from .cunningham import (
    CunninghamChain,
    ChainType,
    derive_candidate_origin,
    verify_cunningham_chain,
    mine_cunningham_chain,
)
from .difficulty import (
    calculate_next_difficulty,
    TARGET_BLOCK_TIME_SECONDS,
    DIFFICULTY_EPOCH_BLOCKS,
    MIN_DIFFICULTY,
)

__all__ = [
    "is_prime",
    "miller_rabin",
    "CunninghamChain",
    "ChainType",
    "derive_candidate_origin",
    "verify_cunningham_chain",
    "mine_cunningham_chain",
    "calculate_next_difficulty",
    "TARGET_BLOCK_TIME_SECONDS",
    "DIFFICULTY_EPOCH_BLOCKS",
    "MIN_DIFFICULTY",
]
