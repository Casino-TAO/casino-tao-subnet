# 🧪 Running on Testnet

This guide covers testing Casino TAO on Bittensor testnet before mainnet deployment.

---

## Network Information

| Property | Value |
|----------|-------|
| **Network** | Bittensor Testnet |
| **EVM RPC** | `https://test.chain.opentensor.ai` |
| **EVM Chain ID** | `945` |
| **Contract Address** | `0x074A77a378D6cA63286CD4A020CdBfc9696132a7` |

---

## Why Test First?

Testing on testnet allows you to:

- ✅ Verify your setup works correctly
- ✅ Test wallet linking flow
- ✅ Practice betting without risking real TAO
- ✅ Debug any issues before mainnet
- ✅ Familiarize yourself with the system

---

## Getting Testnet TAO

### Option 1: Testnet Faucet

Visit the Bittensor testnet faucet to get free testnet TAO:

```bash
# Request from Discord or faucet website
# Testnet TAO has no real value
```

### Option 2: Community

Ask in the Bittensor Discord testnet channels for testnet TAO.

---

## Configuration for Testnet

### Update Constants

When testing, use testnet configuration in `taocasino/core/const.py`:

```python
# Testnet configuration
CASINOTAO_CONTRACT_ADDRESS = "0x074A77a378D6cA63286CD4A020CdBfc9696132a7"
BITTENSOR_EVM_RPC = "https://test.chain.opentensor.ai"
BITTENSOR_EVM_CHAIN_ID = 945

# Comment out mainnet settings
# CASINOTAO_CONTRACT_ADDRESS = "0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93"
# BITTENSOR_EVM_RPC = "https://lite.chain.opentensor.ai"
# BITTENSOR_EVM_CHAIN_ID = 964
```

---

## Validator Testing

### 1. Create Testnet Wallet

```bash
btcli wallet new_coldkey --wallet.name validator_test
btcli wallet new_hotkey --wallet.name validator_test --wallet.hotkey default
```

### 2. Register on Testnet

```bash
btcli subnet register \
    --netuid <TESTNET_NETUID> \
    --wallet.name validator_test \
    --wallet.hotkey default \
    --subtensor.network test
```

### 3. Run Validator

```bash
cd casinotao
source venv/bin/activate

python validator/validator.py \
    --netuid <TESTNET_NETUID> \
    --wallet.name validator_test \
    --wallet.hotkey default \
    --subtensor.network test \
    --logging.debug
```

### 4. Verify It's Working

```bash
# Check API
curl http://localhost:8000/health

# Check logs for volume queries
# You should see:
# "Forward step X: Checking betting volumes..."
# "Querying volumes for N miners..."
```

---

## Miner Testing

### 1. Create Test Wallet

```bash
btcli wallet new_coldkey --wallet.name miner_test
btcli wallet new_hotkey --wallet.name miner_test --wallet.hotkey default
```

### 2. Register on Testnet

```bash
btcli subnet register \
    --netuid <TESTNET_NETUID> \
    --wallet.name miner_test \
    --wallet.hotkey default \
    --subtensor.network test
```

### 3. Setup EVM Wallet

Add Bittensor Testnet to MetaMask:

| Setting | Value |
|---------|-------|
| Network Name | Bittensor Testnet |
| RPC URL | `https://test.chain.opentensor.ai` |
| Chain ID | `945` |
| Currency Symbol | `TAO` |

### 4. Bridge Testnet TAO to EVM

Use the testnet bridge to move TAO to your EVM wallet.

### 5. Link Wallet

Register your coldkey-to-EVM mapping via the testnet frontend or API.

### 6. Place Test Bets

Interact with the testnet contract:

```javascript
const TESTNET_CONTRACT = "0x074A77a378D6cA63286CD4A020CdBfc9696132a7";
const TESTNET_RPC = "https://test.chain.opentensor.ai";

// Place a test bet
const tx = await casino.placeBet(gameId, 0, "", {
    value: ethers.parseEther("0.1")
});
```

### 7. Verify Volume Tracking

Check with a validator:

```bash
curl http://localhost:8000/volumes/<YOUR_UID>
```

---

## Testing Checklist

### Validator Tests

- [ ] Validator starts without errors
- [ ] API is accessible at configured port
- [ ] `/health` endpoint returns healthy status
- [ ] Volume queries complete without errors
- [ ] Weight setting succeeds
- [ ] Snapshots are saved to database

### Miner Tests

- [ ] Registration on subnet succeeds
- [ ] Wallet linking via API works
- [ ] Bets are placed successfully on contract
- [ ] Betting volume shows up in validator API
- [ ] Winnings can be claimed after game resolution

### Integration Tests

- [ ] Multiple miners show correct relative volumes
- [ ] Time decay is applied correctly
- [ ] Weights reflect betting activity
- [ ] API leaderboard updates appropriately

---

## Common Testnet Issues

### "Cannot connect to testnet"

```bash
# Verify testnet is accessible
curl -X POST https://test.chain.opentensor.ai \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### "Contract call failed"

Ensure you're using the testnet contract address:
`0x074A77a378D6cA63286CD4A020CdBfc9696132a7`

### "Insufficient funds"

Get more testnet TAO from the faucet or community.

### "Registration failed"

Check if the testnet subnet is active and has available slots:

```bash
btcli subnet info --netuid <TESTNET_NETUID> --subtensor.network test
```

---

## Local Development

For faster iteration, you can run a local subnet:

### 1. Start Local Subtensor

```bash
# Clone subtensor
git clone https://github.com/opentensor/subtensor.git
cd subtensor

# Run local node
./scripts/localnet.sh
```

### 2. Deploy Contract Locally

```bash
cd casinotao/contracts/contracts

# Install dependencies
npm install

# Deploy to local network
npx hardhat run scripts/deploy.js --network localhost
```

### 3. Update Configuration

Point to local endpoints in `const.py`:

```python
BITTENSOR_EVM_RPC = "http://localhost:8545"
CASINOTAO_CONTRACT_ADDRESS = "<DEPLOYED_ADDRESS>"
```

---

## Switching from Testnet to Mainnet

When ready for mainnet:

1. **Update Configuration**

```python
# In taocasino/core/const.py
CASINOTAO_CONTRACT_ADDRESS = "0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93"
BITTENSOR_EVM_RPC = "https://lite.chain.opentensor.ai"
BITTENSOR_EVM_CHAIN_ID = 964
```

2. **Create Mainnet Wallets**

```bash
btcli wallet new_coldkey --wallet.name validator_main
btcli wallet new_hotkey --wallet.name validator_main --wallet.hotkey default
```

3. **Fund with Real TAO**

Transfer real TAO for registration and operations.

4. **Register on Mainnet**

```bash
btcli subnet register \
    --netuid <MAINNET_NETUID> \
    --wallet.name validator_main \
    --wallet.hotkey default \
    --subtensor.network finney
```

5. **Deploy to Production**

See [Running on Mainnet](running_on_mainnet.md) for production deployment.

---

## Test Script

Create a test script to verify everything works:

```bash
#!/bin/bash
# test_setup.sh

echo "=== Casino TAO Testnet Verification ==="

# Check Python installation
echo -n "Python version: "
python --version

# Check Bittensor
echo -n "Bittensor version: "
python -c "import bittensor; print(bittensor.__version__)"

# Check Web3
echo -n "Web3 version: "
python -c "import web3; print(web3.__version__)"

# Check testnet RPC
echo -n "Testnet RPC: "
curl -s -X POST https://test.chain.opentensor.ai \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | \
  python -c "import sys,json; print('Block', int(json.load(sys.stdin)['result'], 16))"

# Check contract
echo -n "Contract code exists: "
curl -s -X POST https://test.chain.opentensor.ai \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getCode","params":["0x074A77a378D6cA63286CD4A020CdBfc9696132a7","latest"],"id":1}' | \
  python -c "import sys,json; r=json.load(sys.stdin)['result']; print('Yes' if len(r) > 4 else 'No')"

echo "=== Verification Complete ==="
```

Run with:

```bash
chmod +x test_setup.sh
./test_setup.sh
```

---

## Next Steps

After successful testnet testing:

1. ✅ Review [Running on Mainnet](running_on_mainnet.md)
2. ✅ Set up production server
3. ✅ Configure monitoring
4. ✅ Plan stake amount
5. ✅ Deploy to mainnet!

---

<p align="center">
  <b>Happy Testing! 🧪</b>
</p>
