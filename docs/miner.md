# ⛏️ Casino TAO Miner Guide

This guide explains how to participate as a miner in the Casino TAO subnet.

---

## Overview

In Casino TAO, **miners earn rewards by placing bets** on the TAO Casino smart contract deployed on Bittensor EVM. Unlike traditional subnets where miners run compute tasks, Casino TAO miners participate in a decentralized betting game.

### How Mining Works

```
┌────────────────────────────────────────────────────────────┐
│                    Miner Journey                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   1. Register    2. Link Wallet    3. Place Bets          │
│   ┌─────────┐    ┌─────────────┐   ┌─────────────┐        │
│   │ Subnet  │───▶│  Coldkey →  │──▶│ TAO Casino  │        │
│   │  UID    │    │  EVM Addr   │   │  Contract   │        │
│   └─────────┘    └─────────────┘   └─────────────┘        │
│                                            │               │
│   4. Earn Rewards  ◀───────────────────────┘              │
│   (Based on betting volume, time-decayed)                  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

1. **Register** on the Casino TAO subnet with your Bittensor wallet
2. **Link** your coldkey to an EVM address via signed message
3. **Place bets** on the TAO Casino smart contract
4. **Earn rewards** based on your betting volume (time-decayed over 7 days)

---

## Prerequisites

- Bittensor wallet (coldkey + hotkey)
- TAO for registration and betting
- EVM wallet (MetaMask or similar) with TAO on Bittensor EVM

---

## Step 1: Register on the Subnet

### Install Bittensor

```bash
pip install bittensor
```

### Create a Wallet (if you don't have one)

```bash
# Create coldkey
btcli wallet new_coldkey --wallet.name miner

# Create hotkey
btcli wallet new_hotkey --wallet.name miner --wallet.hotkey default
```

### Register on Casino TAO Subnet

```bash
btcli subnet register \
    --netuid <CASINOTAO_NETUID> \
    --wallet.name miner \
    --wallet.hotkey default \
    --subtensor.network finney
```

> **Note**: Registration requires TAO for the registration fee. Check current fee:
> ```bash
> btcli subnet info --netuid <CASINOTAO_NETUID>
> ```

### Verify Registration

```bash
btcli wallet overview --wallet.name miner --subtensor.network finney
```

You should see your UID in the Casino TAO subnet.

---

## Step 2: Link Coldkey to EVM Address

Validators need to know which EVM address belongs to which miner. You must link your Bittensor coldkey to your EVM address by signing a message.

### Option A: Using the Casino TAO Frontend (Recommended)

1. Visit the Casino TAO web interface
2. Connect your Bittensor wallet (via Polkadot.js extension)
3. Connect your EVM wallet (MetaMask)
4. Sign the linking message with your coldkey
5. The frontend will submit the mapping to validators

### Option B: Manual Mapping

If you need to register programmatically:

```python
from substrateinterface import Keypair
import requests

# Your details
COLDKEY_SS58 = "5..."  # Your coldkey address
EVM_ADDRESS = "0x..."   # Your EVM address
VALIDATOR_API = "http://validator-ip:8000"

# Create the message
timestamp = int(time.time() * 1000)
message_content = f"Link {COLDKEY_SS58} to {EVM_ADDRESS} at {timestamp}"
message = f"<Bytes>{message_content}</Bytes>"

# Sign with coldkey
keypair = Keypair.create_from_uri("//your/mnemonic")  # Or load from file
signature = keypair.sign(message).hex()

# Submit to validator
response = requests.post(
    f"{VALIDATOR_API}/api/wallet-mapping",
    json={
        "type": "wallet_mapping",
        "data": {
            "coldkey": COLDKEY_SS58,
            "evmAddress": EVM_ADDRESS,
            "signature": signature,
            "message": message,
            "timestamp": timestamp,
            "verified": True
        }
    }
)
print(response.json())
```

---

## Step 3: Get TAO on Bittensor EVM

To place bets, you need TAO in your EVM wallet on Bittensor EVM.

### Bridge TAO to EVM

1. Go to the Bittensor EVM bridge interface
2. Connect your native Bittensor wallet
3. Connect your EVM wallet
4. Bridge TAO from native to EVM

### Verify Balance

Add Bittensor EVM to MetaMask:
- **Network Name**: Bittensor EVM
- **RPC URL**: `https://lite.chain.opentensor.ai`
- **Chain ID**: `964`
- **Currency Symbol**: `TAO`

---

## Step 4: Place Bets on TAO Casino

### Understanding the Game

TAO Casino offers two game types:

| Game Type | How to Win | Strategy |
|-----------|------------|----------|
| **Classic** | Bet on the side with MORE money | Follow the crowd |
| **Underdog** | Bet on the side with LESS money | Contrarian play |

And two speeds:

| Speed | Betting Duration | Best For |
|-------|-----------------|----------|
| **Regular** | 105 minutes | Considered plays |
| **Rapid** | 10 minutes | Quick action |

### Betting via Web Interface

1. Visit the TAO Casino frontend
2. Connect your EVM wallet
3. Choose a game (Classic or Underdog)
4. Select a side (Red or Blue)
5. Enter bet amount
6. Confirm transaction

### Betting via Smart Contract (Advanced)

```javascript
// Using ethers.js
const { ethers } = require("ethers");

const CASINO_ADDRESS = "0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93";
const RPC_URL = "https://lite.chain.opentensor.ai";

const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

const casinoABI = [
    "function placeBet(uint256 _gameId, uint8 _side, string calldata _referralCode) external payable"
];

const casino = new ethers.Contract(CASINO_ADDRESS, casinoABI, wallet);

// Place bet: gameId=1, side=0 (Red), no referral
const tx = await casino.placeBet(1, 0, "", {
    value: ethers.parseEther("1.0")  // 1 TAO bet
});
await tx.wait();
console.log("Bet placed:", tx.hash);
```

### Dual-Position Betting

You can bet on BOTH sides in the same game! This lets you:
- Hedge your bets
- Capture rewards regardless of outcome
- Maximize volume for mining rewards

```javascript
// Bet on Red
await casino.placeBet(gameId, 0, "", { value: ethers.parseEther("5.0") });

// Bet on Blue in same game
await casino.placeBet(gameId, 1, "", { value: ethers.parseEther("3.0") });
```

---

## Step 5: Claim Winnings

After a game resolves, claim your winnings:

### Via Web Interface

1. Go to "My Bets" section
2. Find resolved games
3. Click "Claim" on winning bets

### Via Smart Contract

```javascript
const casinoABI = [
    "function claimWinnings(uint256 _gameId, uint8 _side) external",
    "function claimAllWinnings(uint256 _gameId) external"
];

// Claim from specific side
await casino.claimWinnings(gameId, 0);  // Claim Red side

// Or claim all sides at once
await casino.claimAllWinnings(gameId);
```

---

## Understanding Rewards

### Time-Decayed Volume

Your mining rewards are based on your **weighted betting volume** over the last 7 days:

| Day | Weight | Example (10 TAO bet) |
|-----|--------|---------------------|
| Today | 1.00 | 10.00 TAO weighted |
| Yesterday | 0.85 | 8.50 TAO weighted |
| 2 days ago | 0.70 | 7.00 TAO weighted |
| 3 days ago | 0.55 | 5.50 TAO weighted |
| 4 days ago | 0.40 | 4.00 TAO weighted |
| 5 days ago | 0.25 | 2.50 TAO weighted |
| 6 days ago | 0.10 | 1.00 TAO weighted |

**Key Insight**: Recent betting activity is worth more! A bet placed today counts 10x more than a bet placed 6 days ago.

### Reward Calculation

```
Your Reward Share = Your Weighted Volume / Total Weighted Volume
```

If you have 100 TAO weighted volume and the total is 1000 TAO, you get 10% of emissions.

### Maximizing Rewards

1. **Bet Consistently**: Regular betting maintains high weighted volume
2. **Recent Activity Matters**: Focus on recent bets rather than large old ones
3. **Use Dual Positions**: Betting on both sides maximizes volume
4. **Consider Underdog Bonus**: Lower fees when betting on smaller side

---

## Fee Structure

| Fee Type | Amount | Notes |
|----------|--------|-------|
| Platform Fee | 1.5% | Taken from bet amount |
| Underdog Bonus | -0.5% | When betting on side < 30% |
| Referral Share | 10% | Of fees, goes to referrer |

**Net fee with underdog bonus**: 1.0%

---

## Using Referrals

### Creating Your Referral Code

```javascript
const casinoABI = [
    "function createReferralCode(string calldata _code) external"
];

await casino.createReferralCode("MYCODE123");
```

### Using a Referral Code

When placing bets, include the referral code:

```javascript
await casino.placeBet(gameId, side, "REFERRER_CODE", {
    value: ethers.parseEther("1.0")
});
```

### Claiming Referral Rewards

```javascript
const casinoABI = [
    "function claimReferralRewards() external"
];

await casino.claimReferralRewards();
```

---

## Checking Your Status

### Via Validator API

```bash
# Get your miner score (replace with your UID)
curl http://validator-ip:8000/scores/42

# Get your volume details
curl http://validator-ip:8000/volumes/42

# Check leaderboard
curl http://validator-ip:8000/leaderboard
```

### Response Example

```json
{
    "uid": 42,
    "hotkey": "5F...",
    "coldkey": "5G...",
    "score": 0.0523,
    "evm_address": "0x...",
    "daily_volumes": [10.5, 8.2, 5.0, 3.0, 0, 0, 0],
    "weighted_volume": 22.85
}
```

---

## Troubleshooting

### "No wallet mapping found"

Your coldkey isn't linked to an EVM address. Complete Step 2.

### "Zero betting volume"

Possible causes:
- You haven't placed any bets in the last 7 days
- Your wallet mapping is incorrect
- Bets were placed from a different EVM address

### "Low reward share"

- Increase betting volume
- Bet more frequently (recent bets weight more)
- Check if other miners have higher volumes

### Transaction Fails

- Check TAO balance on EVM
- Verify you're connected to Bittensor EVM (Chain ID: 964)
- Check gas settings

---

## Best Practices

1. **Consistent Activity**: Bet regularly rather than in large bursts
2. **Track Your Volume**: Monitor your weighted volume via validator API
3. **Secure Your Keys**: Never share private keys or mnemonics
4. **Understand the Game**: Know when you're playing Classic vs Underdog
5. **Claim Winnings**: Don't forget to claim after games resolve

---

## FAQ

**Q: Do I need to run any software?**
A: No! Unlike traditional mining, you just place bets on the smart contract.

**Q: Can I lose my bet?**
A: Yes, betting involves risk. If you bet on the losing side, you lose your bet. Mining rewards are separate from betting outcomes.

**Q: What's the minimum bet?**
A: There's no minimum, but very small bets may not be cost-effective after gas fees.

**Q: How often are rewards distributed?**
A: Validators set weights every ~72 minutes. Your share of emissions depends on your relative weighted volume.

**Q: Can I be a miner and validator?**
A: Yes! You can run a validator and also place bets to earn miner rewards.

---

## Contract Addresses

| Network | Contract Address |
|---------|-----------------|
| Mainnet | `0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93` |
| Testnet | `0x074A77a378D6cA63286CD4A020CdBfc9696132a7` |

---

<p align="center">
  <b>Good luck and bet responsibly! 🎰</b>
</p>
