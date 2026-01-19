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
Forward module for Casino TAO validator.
Periodically checks betting volumes from the casinotao smart contract
and updates miner scores based on time-decayed activity.
"""

import time
from typing import Dict, Optional
import numpy as np
import bittensor as bt

from casinotao.core.const import VOLUME_CHECK_INTERVAL
from casinotao.validator.reward import calculate_volume_rewards
from casinotao.validator.database import update_miner_data, cleanup_old_events, get_evm_address_for_coldkey

# Import contract client with error handling
try:
    from casinotao.validator.contract import (
        get_contract_client,
        get_miner_volume,
        ContractClient,
    )
    CONTRACT_AVAILABLE = True
except ImportError as e:
    CONTRACT_AVAILABLE = False
    bt.logging.warning(f"Contract module not available: {e}")


def _get_miner_evm_address(coldkey: str) -> Optional[str]:
    """
    Get the EVM address for a miner's coldkey.
    
    This queries the database for wallet mappings that were registered
    via the POST /api/wallet-mapping endpoint. Miners use the frontend UI
    to sign a message with their coldkey and link it to their EVM address.
    
    Args:
        coldkey: Bittensor coldkey (SS58 format)
        
    Returns:
        EVM address or None if not mapped
    """
    try:
        evm_address = get_evm_address_for_coldkey(coldkey)
        if evm_address:
            bt.logging.debug(f"Found EVM mapping for {coldkey[:10]}...: {evm_address[:10]}...")
        return evm_address
    except Exception as e:
        bt.logging.warning(f"Error getting EVM address for {coldkey[:10]}...: {e}")
        return None


async def forward(self):
    """
    The forward function is called by the validator every time step.
    
    It queries the casinotao smart contract for each miner's betting
    volume over the last 7 days, applies time decay weighting, and
    updates miner scores accordingly.
    
    The scores are later used to set weights on the Bittensor network.
    """
    bt.logging.info(f"Forward step {self.step}: Checking betting volumes...")
    
    # Initialize volume tracking if not present
    if not hasattr(self, 'miner_volumes'):
        self.miner_volumes = {}
    if not hasattr(self, 'miner_daily_volumes'):
        self.miner_daily_volumes = {}
    if not hasattr(self, 'miner_evm_addresses'):
        self.miner_evm_addresses = {}
    
    # Check if contract client is available
    if not CONTRACT_AVAILABLE:
        bt.logging.warning("Contract module not available, skipping volume check")
        time.sleep(VOLUME_CHECK_INTERVAL)
        return
    
    try:
        client = get_contract_client()
        
        if not client.is_connected():
            bt.logging.warning("Not connected to Bittensor EVM RPC")
            time.sleep(VOLUME_CHECK_INTERVAL)
            return
            
    except Exception as e:
        bt.logging.error(f"Failed to initialize contract client: {e}")
        time.sleep(VOLUME_CHECK_INTERVAL)
        return
    
    # Query volumes for all miners
    volumes = {}
    daily_volumes = {}
    active_count = 0
    
    bt.logging.info(f"Querying volumes for {self.metagraph.n} miners...")
    
    for uid in range(self.metagraph.n):
        coldkey = self.metagraph.coldkeys[uid]
        hotkey = self.metagraph.hotkeys[uid]
        
        # Get EVM address for this miner
        evm_address = self.miner_evm_addresses.get(uid) or _get_miner_evm_address(coldkey)
        
        if evm_address:
            self.miner_evm_addresses[uid] = evm_address
            
            # Query betting volume from contract
            weighted_vol, daily_vols = get_miner_volume(client, evm_address)
            
            volumes[uid] = weighted_vol
            daily_volumes[uid] = daily_vols
            
            if weighted_vol > 0:
                active_count += 1
                bt.logging.debug(
                    f"UID {uid}: {weighted_vol:.4f} TAO weighted volume "
                    f"(daily: {[f'{v:.2f}' for v in daily_vols]})"
                )
            
            # Update database
            update_miner_data(
                uid=uid,
                hotkey=hotkey,
                coldkey=coldkey,
                evm_address=evm_address,
                daily_volumes=daily_vols,
                weighted_volume=weighted_vol,
                score=float(self.scores[uid]) if uid < len(self.scores) else 0.0
            )
        else:
            volumes[uid] = 0.0
            daily_volumes[uid] = [0.0] * 7
    
    # Store volumes for API access
    self.miner_volumes = volumes
    self.miner_daily_volumes = daily_volumes
    
    bt.logging.info(
        f"Volume check complete: {active_count}/{self.metagraph.n} miners "
        f"with betting activity"
    )
    
    # Calculate rewards based on volumes
    if active_count > 0:
        rewards = calculate_volume_rewards(volumes, daily_volumes)
        
        # Get UIDs in order
        uids = list(range(self.metagraph.n))
        
        # Create rewards array aligned with all UIDs
        reward_array = np.zeros(self.metagraph.n, dtype=np.float32)
        sorted_uids = sorted(volumes.keys())
        
        # Ensure rewards is a 1D array (handles edge cases with single element)
        rewards = np.atleast_1d(rewards)
        
        for i, uid in enumerate(sorted_uids):
            if i < len(rewards):
                reward_array[uid] = float(rewards[i])
        
        bt.logging.info(
            f"Updating scores for {len(uids)} miners, "
            f"{active_count} with rewards, max reward: {reward_array.max():.4f}"
        )
        self.update_scores(reward_array.tolist(), uids)
    else:
        bt.logging.info("No miners with betting volume - scores unchanged")
    
    # Periodic cleanup of old cached events
    if self.step % 100 == 0:
        cleanup_old_events(days=14)
    
    # Sleep before next check
    bt.logging.debug(f"Sleeping {VOLUME_CHECK_INTERVAL}s before next volume check")
    time.sleep(VOLUME_CHECK_INTERVAL)


async def forward_with_evm_mapping(self, evm_mapping: Dict[str, str]):
    """
    Alternative forward function that accepts an explicit EVM address mapping.
    
    Use this if you have a separate system for tracking miner EVM addresses.
    
    Args:
        evm_mapping: Dict mapping coldkey (SS58) -> EVM address
    """
    # Update the cached EVM addresses
    for uid in range(self.metagraph.n):
        coldkey = self.metagraph.coldkeys[uid]
        if coldkey in evm_mapping:
            self.miner_evm_addresses[uid] = evm_mapping[coldkey]
    
    # Run regular forward
    await forward(self)
