# 🔍 Casino TAO Validator Guide

This guide explains how to set up and run a Casino TAO validator.

---

## Overview

Casino TAO validators are responsible for:

1. **Querying Betting Volumes**: Periodically checking the TAO Casino smart contract for miner betting activity
2. **Calculating Rewards**: Computing time-decayed rewards based on 7-day betting volume
3. **Setting Weights**: Updating weights on the Bittensor network every ~72 minutes
4. **Serving API**: Providing a REST API for querying validator state

```
┌────────────────────────────────────────────────────────────┐
│                    Validator Lifecycle                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│   │   Query     │───▶│  Calculate  │───▶│    Set      │   │
│   │   Volumes   │    │   Rewards   │    │   Weights   │   │
│   └─────────────┘    └─────────────┘    └─────────────┘   │
│         │                                      │          │
│         │              Every 5 min             │          │
│         └──────────────────────────────────────┘          │
│                                                            │
│         Weight commits happen every 360 blocks            │
│                      (~72 minutes)                         │
└────────────────────────────────────────────────────────────┘
```

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB SSD | 50+ GB SSD |
| Network | 10 Mbps | 100+ Mbps |
| OS | Ubuntu 20.04+ | Ubuntu 22.04 |

---

## Prerequisites

- Python 3.9 or higher
- A registered Bittensor wallet with sufficient stake
- Access to the Bittensor network (finney for mainnet)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/casinotao/casinotao.git
cd casinotao
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Verify Installation

```bash
python -c "import bittensor; import casinotao; print('Installation successful!')"
```

---

## Configuration

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--netuid` | Subnet UID to validate on | Required |
| `--wallet.name` | Coldkey wallet name | Required |
| `--wallet.hotkey` | Hotkey name | Required |
| `--subtensor.network` | Network (finney/test/local) | `finney` |
| `--neuron.api_port` | REST API port | `8000` |
| `--neuron.disable_api` | Disable REST API | `false` |
| `--logging.debug` | Enable debug logging | `false` |

### Constants (taocasino/core/const.py)

```python
# Contract address (mainnet)
CASINOTAO_CONTRACT_ADDRESS = "0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93"

# RPC endpoint
BITTENSOR_EVM_RPC = "https://lite.chain.opentensor.ai"

# Time decay weights [today, yesterday, ..., 6 days ago]
TIME_DECAY_WEIGHTS = [1.0, 0.85, 0.70, 0.55, 0.40, 0.25, 0.10]

# Volume check interval (seconds)
VOLUME_CHECK_INTERVAL = 300  # 5 minutes

# Weight commit interval (blocks)
WEIGHT_COMMIT_INTERVAL = 360  # ~72 minutes
```

---

## Running the Validator

### Basic Command

```bash
python validator/validator.py \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME> \
    --subtensor.network finney
```

### With Custom API Port

```bash
python validator/validator.py \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME> \
    --subtensor.network finney \
    --neuron.api_port 9000
```

### Using the Console Script

After installation, you can also run:

```bash
casinotao-validator \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME>
```

### Running with PM2 (Recommended for Production)

```bash
# Install PM2
npm install -g pm2

# Start validator
pm2 start validator/validator.py --name casinotao-validator --interpreter python -- \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME> \
    --subtensor.network finney

# Monitor
pm2 logs casinotao-validator

# Auto-restart on reboot
pm2 startup
pm2 save
```

### Running with systemd

Create `/etc/systemd/system/casinotao-validator.service`:

```ini
[Unit]
Description=Casino TAO Validator
After=network.target

[Service]
Type=simple
User=<YOUR_USER>
WorkingDirectory=/path/to/casinotao
Environment="PATH=/path/to/casinotao/venv/bin"
ExecStart=/path/to/casinotao/venv/bin/python validator/validator.py \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME> \
    --subtensor.network finney
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable casinotao-validator
sudo systemctl start casinotao-validator
sudo journalctl -u casinotao-validator -f
```

---

## REST API Reference

The validator serves a REST API on the configured port (default: 8000).

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service status |
| `/health` | GET | Validator health with block/step info |
| `/info` | GET | Detailed validator information |

### Scores & Volumes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scores` | GET | All miner scores |
| `/scores/{uid}` | GET | Specific miner's score and details |
| `/volumes` | GET | Current betting volumes |
| `/volumes/{uid}` | GET | Specific miner's volume breakdown |

### Leaderboard & Stats

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/leaderboard` | GET | Top miners ranked by score |
| `/stats` | GET | Overall subnet statistics |
| `/miners` | GET | All miners with data |

### Snapshots

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/snapshots` | GET | List historical snapshots |
| `/snapshots/latest` | GET | Most recent snapshot |
| `/snapshots/{block}` | GET | Snapshot at specific block |

### Wallet Mapping

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/wallet-mapping` | POST | Register coldkey-to-EVM mapping |
| `/api/wallet-mapping/{coldkey}` | GET | Get mapping for coldkey |
| `/api/wallet-mappings` | GET | List all mappings |

### Example API Calls

```bash
# Check health
curl http://localhost:8000/health

# Get leaderboard
curl http://localhost:8000/leaderboard?limit=10

# Get specific miner's volume
curl http://localhost:8000/volumes/42

# Get latest snapshot
curl http://localhost:8000/snapshots/latest
```

API documentation with interactive testing is available at:
`http://localhost:8000/docs`

---

## Database

The validator stores data in SQLite (`validator_data.db`):

### Tables

- **snapshots**: Historical weight snapshots with scores and volumes
- **miner_data**: Cached miner information and EVM addresses
- **wallet_mappings**: Coldkey-to-EVM address mappings
- **bet_events**: Cached bet events from the contract

### Viewing Data

```bash
sqlite3 validator_data.db

# List tables
.tables

# View recent snapshots
SELECT block_number, timestamp FROM snapshots ORDER BY block_number DESC LIMIT 10;

# View active miners
SELECT uid, hotkey, weighted_volume FROM miner_data WHERE weighted_volume > 0;
```

---

## Monitoring

### Log Output

The validator logs important events:

```
Casino TAO Validator Starting
Validator UID: 42
Network: wss://entrypoint-finney.opentensor.ai:443
Netuid: <NETUID>
API Port: 8000
API server started at http://0.0.0.0:8000
Forward step 1: Checking betting volumes...
Querying volumes for 256 miners...
Volume check complete: 15/256 miners with betting activity
Heartbeat | Block: 1234567 | Step: 10 | Active miners: 15 | Total volume: 125.5000 TAO
set_weights on chain successfully!
Snapshot saved at block 1234567
```

### Key Metrics to Monitor

1. **Active Miners**: Number of miners with betting activity
2. **Total Volume**: Sum of weighted betting volumes
3. **Weight Commits**: Successful weight setting operations
4. **API Health**: API server responsiveness

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo "Validator is healthy"
    exit 0
else
    echo "Validator health check failed"
    exit 1
fi
```

---

## Troubleshooting

### Common Issues

#### "Not connected to Bittensor EVM RPC"

The validator can't reach the EVM RPC endpoint. Check:
- Network connectivity
- RPC endpoint availability
- Firewall rules

```bash
# Test RPC connection
curl -X POST https://lite.chain.opentensor.ai \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

#### "Contract module not available"

Web3 is not installed. Install with:

```bash
pip install web3>=6.0.0
```

#### "Failed to set weights"

Common causes:
- Insufficient stake
- Rate limiting (too frequent weight commits)
- Network issues

Check your stake:

```bash
btcli wallet balance --wallet.name <WALLET_NAME>
```

#### API Not Starting

Check if port is in use:

```bash
lsof -i :8000
```

Use a different port:

```bash
--neuron.api_port 9000
```

### Debug Mode

Enable debug logging for more details:

```bash
python validator/validator.py \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME> \
    --logging.debug
```

---

## Security Considerations

1. **Protect Your Keys**: Keep wallet files secure with proper permissions
2. **Firewall**: Restrict API access to trusted IPs in production
3. **Updates**: Keep dependencies updated for security patches
4. **Monitoring**: Set up alerts for validator downtime

```bash
# Secure wallet directory
chmod 700 ~/.bittensor/wallets
chmod 600 ~/.bittensor/wallets/*/coldkey
```

---

## Updating

```bash
cd casinotao
git pull origin main
pip install -e .

# Restart validator
pm2 restart casinotao-validator
# or
sudo systemctl restart casinotao-validator
```

---

## Support

- Check the [main README](../README.md) for overview
- Join the Bittensor Discord for community support
- Open an issue on GitHub for bugs

---

<p align="center">
  <b>Happy Validating! 🎰</b>
</p>
