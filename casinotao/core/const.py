# The MIT License (MIT)
# Copyright © 2025 Casino TAO

# Constants for Casino TAO validator

# Casino TAO Contract on Bittensor EVM Testnet
# CASINOTAO_CONTRACT_ADDRESS = "0x074A77a378D6cA63286CD4A020CdBfc9696132a7"
# BITTENSOR_EVM_RPC = "https://test.chain.opentensor.ai"
# BITTENSOR_EVM_CHAIN_ID = 945

# Mainnet (uncomment when deploying to mainnet)
CASINOTAO_CONTRACT_ADDRESS = "0x1e0bA1BcF31feFf1a9dc16FE3E0A203E3439DB47"
BITTENSOR_EVM_RPC = "https://lite.chain.opentensor.ai"
BITTENSOR_EVM_CHAIN_ID = 964

# Time decay weights for 7 days (index 0 = today, index 6 = 6 days ago)
# Most recent activity gets highest weight
TIME_DECAY_WEIGHTS = [1.0, 0.85, 0.70, 0.55, 0.40, 0.25, 0.10]

# Volume check interval in seconds (5 minutes)
VOLUME_CHECK_INTERVAL = 300

# Weight commit interval in blocks (360 blocks = ~72 minutes)
WEIGHT_COMMIT_INTERVAL = 360

# Blocks per day (assuming 12 second blocks)
BLOCKS_PER_DAY = 7200

# Database path
DB_PATH = "validator_data.db"

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000
