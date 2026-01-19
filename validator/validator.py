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
Casino TAO Validator

This is the main entry point for running a Casino TAO validator.
The validator:
1. Periodically checks betting volumes from the casinotao smart contract
2. Calculates time-decayed rewards (7 days, recent activity weighted higher)
3. Sets weights on the Bittensor network based on miner betting activity
4. Provides a REST API for querying validator state

Usage:
    python validator/validator.py --netuid <NETUID> --wallet.name <WALLET> --wallet.hotkey <HOTKEY>

API Endpoints (default port 8000):
    GET /health        - Validator health status
    GET /scores        - Current miner scores
    GET /volumes       - Current betting volumes
    GET /leaderboard   - Top miners by score
    GET /snapshots     - Historical weight snapshots
"""

import time
import bittensor as bt

# Import base validator class which takes care of most of the boilerplate
from casinotao.base.validator import BaseValidatorNeuron

# Import the forward function for volume checking
from casinotao.validator import forward


class Validator(BaseValidatorNeuron):
    """
    Casino TAO Validator Neuron.
    
    This validator rewards miners based on their betting activity on the
    casinotao smart contract deployed on Bittensor EVM.
    
    Features:
    - Time-decayed volume rewards (7-day window)
    - Automatic weight setting every 360 blocks (~72 min)
    - REST API for querying state
    - Snapshot storage for historical data
    
    The validator inherits from BaseValidatorNeuron which handles:
    - Database initialization
    - API server startup
    - Metagraph syncing
    - Weight setting with snapshot saving
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)

        bt.logging.info("Loading validator state...")
        try:
            self.load_state()
            bt.logging.info("Validator state loaded successfully")
        except Exception as e:
            bt.logging.warning(f"Could not load previous state: {e}")
            bt.logging.info("Starting with fresh state")

    async def forward(self):
        """
        Validator forward pass.
        
        This function is called periodically to:
        1. Query the casinotao contract for miner betting volumes
        2. Calculate time-decayed rewards
        3. Update miner scores
        
        The scores are then used to set weights on the network.
        """
        return await forward(self)


def main():
    """
    Main entry point for the Casino TAO validator.
    
    Runs the validator in an infinite loop that:
    - Checks betting volumes every 5 minutes
    - Sets weights every 360 blocks (~72 min)
    - Saves snapshots when weights are committed
    - Provides REST API on configured port (default 8000)
    """
    bt.logging.enable_info()
    bt.logging.info("=" * 60)
    bt.logging.info("Casino TAO Validator Starting")
    bt.logging.info("=" * 60)
    
    with Validator() as validator:
        bt.logging.info(f"Validator UID: {validator.uid}")
        bt.logging.info(f"Network: {validator.subtensor.chain_endpoint}")
        bt.logging.info(f"Netuid: {validator.config.netuid}")
        bt.logging.info(f"API Port: {getattr(validator.config.neuron, 'api_port', 8000)}")
        bt.logging.info("=" * 60)
        
        # Main loop - just keep alive, the validator handles everything
        step = 0
        last_block = 0
        while True:
            try:
                # Log heartbeat every minute
                if step % 60 == 0:
                    active_miners = sum(1 for s in validator.scores if s > 0)
                    total_volume = sum(validator.miner_volumes.values()) if validator.miner_volumes else 0
                    
                    # Cache block to avoid concurrent RPC calls
                    try:
                        last_block = validator.metagraph.block
                    except Exception:
                        pass  # Use cached value
                    
                    bt.logging.info(
                        f"Heartbeat | Block: {last_block} | "
                        f"Step: {validator.step} | "
                        f"Active miners: {active_miners} | "
                        f"Total volume: {total_volume:.4f} TAO"
                    )
                
                time.sleep(1)
                step += 1
                
            except KeyboardInterrupt:
                bt.logging.info("Keyboard interrupt received, shutting down...")
                break
            except Exception as e:
                bt.logging.warning(f"Error in main loop: {e}")
            time.sleep(1)
            step += 1


if __name__ == "__main__":
    main()
