"""
ProofCoin Difficulty Adjustment Module.

Algorithm:
- Retarget Epoch: Every 144 blocks
- Target Block Time: 60 seconds (8,640 seconds per 144 blocks)
- Clamping Bounds: Max 4x increase, Min 0.25x decrease to prevent sudden hashrate swing instability
- Proof of Useful Work target: Integer floor represents required Cunningham chain length,
  with fractional remainder reflecting fine-grained hashwork.
"""

from typing import Tuple

TARGET_BLOCK_TIME_SECONDS: int = 60
DIFFICULTY_EPOCH_BLOCKS: int = 144
MIN_DIFFICULTY: float = 2.0
MAX_DIFFICULTY: float = 12.0
TARGET_TIMESPAN_SECONDS: int = DIFFICULTY_EPOCH_BLOCKS * TARGET_BLOCK_TIME_SECONDS  # 8,640 seconds


def calculate_next_difficulty(
    current_height: int,
    current_difficulty: float,
    epoch_start_timestamp: int,
    epoch_end_timestamp: int,
    epoch_blocks: int = DIFFICULTY_EPOCH_BLOCKS,
    target_block_time: int = TARGET_BLOCK_TIME_SECONDS,
) -> float:
    """
    Calculate difficulty for the next block.

    If current_height + 1 is NOT an epoch boundary, returns current_difficulty unmodified.
    If at an epoch boundary (e.g. height % epoch_blocks == 0):
      1. Computes actual_timespan = epoch_end_timestamp - epoch_start_timestamp.
      2. Clamps timespan within [TARGET_TIMESPAN / 4, TARGET_TIMESPAN * 4].
      3. Scales difficulty proportionally:
         adjustment_factor = target_timespan / clamped_timespan
         new_difficulty = current_difficulty * adjustment_factor
      4. Clamps resulting difficulty within [MIN_DIFFICULTY, MAX_DIFFICULTY].
    """
    next_height = current_height + 1
    if next_height % epoch_blocks != 0 or current_height == 0:
        return current_difficulty

    target_timespan = epoch_blocks * target_block_time
    actual_timespan = epoch_end_timestamp - epoch_start_timestamp

    # Prevent zero or negative timespans from clock skew
    if actual_timespan <= 0:
        actual_timespan = 1

    # Clamp actual timespan to [0.25x, 4.0x]
    min_timespan = target_timespan // 4
    max_timespan = target_timespan * 4

    clamped_timespan = max(min_timespan, min(max_timespan, actual_timespan))

    # Adjustment factor: if mining was fast (actual < target), difficulty increases
    adjustment_factor = target_timespan / clamped_timespan
    new_difficulty = current_difficulty * adjustment_factor

    # Bound within protocol limits and round to 4 decimal places
    bounded_diff = max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, new_difficulty))
    return round(bounded_diff, 4)
