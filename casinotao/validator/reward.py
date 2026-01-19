# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2025 Casino TAO

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

"""
Reward calculation module for Casino TAO validator.
Calculates miner rewards based on time-decayed betting volumes.
"""

import numpy as np
from typing import Dict, List
import bittensor as bt

from casinotao.core.const import TIME_DECAY_WEIGHTS


def calculate_volume_rewards(
    volumes: Dict[int, float],
    daily_volumes: Dict[int, List[float]] = None
) -> np.ndarray:
    """
    Calculate rewards based on time-decayed betting volumes.
    
    Miners with more recent and higher betting activity get higher rewards.
    The reward for each miner is proportional to their share of total volume.
    
    Args:
        volumes: Dict mapping UID -> weighted volume (already time-decayed)
        daily_volumes: Optional dict mapping UID -> list of daily volumes

    Returns:
        np.ndarray: Array of rewards for each UID
    """
    if not volumes:
        bt.logging.warning("No volumes provided for reward calculation")
        return np.array([])
    
    uids = sorted(volumes.keys())
    raw_volumes = np.array([volumes[uid] for uid in uids], dtype=np.float32)
    
    total_volume = raw_volumes.sum()
    
    if total_volume == 0:
        bt.logging.info("Total betting volume is zero - no rewards to distribute")
        return np.zeros(len(uids), dtype=np.float32)
    
    # Reward proportional to volume share
    rewards = raw_volumes / total_volume
    
    # Log summary
    active_miners = (raw_volumes > 0).sum()
    bt.logging.info(
        f"Reward calculation: {active_miners} miners with volume, "
        f"total volume: {total_volume:.4f} TAO (weighted)"
    )
    
    return rewards


def get_rewards_for_uids(
    volumes: Dict[int, float],
    uids: List[int]
) -> np.ndarray:
    """
    Get reward array for a specific list of UIDs.
    
    Args:
        volumes: Dict mapping UID -> weighted volume
        uids: List of UIDs to get rewards for
        
    Returns:
        np.ndarray: Rewards array aligned with the uids list
    """
    if not uids:
        return np.array([])
    
    # Get volumes for specified UIDs
    uid_volumes = {uid: volumes.get(uid, 0.0) for uid in uids}
    
    raw_volumes = np.array([uid_volumes[uid] for uid in uids], dtype=np.float32)
    total_volume = raw_volumes.sum()
    
    if total_volume == 0:
        return np.zeros(len(uids), dtype=np.float32)
    
    return raw_volumes / total_volume


def apply_time_decay(daily_volumes: List[float], weights: List[float] = None) -> float:
    """
    Apply time decay weights to daily volumes.
    
    Args:
        daily_volumes: List of volumes [today, yesterday, ..., 6 days ago]
        weights: Optional custom weights (default: TIME_DECAY_WEIGHTS)
        
    Returns:
        Weighted sum of volumes
    """
    weights = weights or TIME_DECAY_WEIGHTS
    
    # Ensure we have enough data
    if len(daily_volumes) < len(weights):
        daily_volumes = daily_volumes + [0.0] * (len(weights) - len(daily_volumes))
    
    weighted_sum = sum(
        vol * weight 
        for vol, weight in zip(daily_volumes[:len(weights)], weights)
    )
    
    return weighted_sum


def normalize_rewards(rewards: np.ndarray) -> np.ndarray:
    """
    Normalize rewards to sum to 1.
    
    Args:
        rewards: Raw reward array
        
    Returns:
        Normalized reward array
    """
    total = rewards.sum()
    
    if total == 0:
        return rewards
    
    return rewards / total


def calculate_incentive_distribution(
    scores: np.ndarray,
    stake: np.ndarray = None
) -> np.ndarray:
    """
    Calculate the final incentive distribution.
    This considers both scores and optionally stake.

    Args:
        scores: Miner scores array
        stake: Optional stake array for weighting

    Returns:
        Incentive distribution array
    """
    if stake is not None and len(stake) == len(scores):
        # Could incorporate stake into distribution
        # For now, just use scores
        pass
    
    return normalize_rewards(scores)


# Legacy compatibility - kept for reference
def reward(query: int, response: int) -> float:
    """
    Legacy reward function (not used in Casino TAO).
    Kept for template compatibility.
    """
    return 1.0 if response == query * 2 else 0


def get_rewards(self, query: int, responses: List[float]) -> np.ndarray:
    """
    Legacy get_rewards function (not used in Casino TAO).
    Kept for template compatibility.
    """
    return np.array([reward(query, response) for response in responses])
