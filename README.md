<p align="center">
  <h1 align="center">🎰 Casino TAO</h1>
  <h3 align="center">P2P Betting on Bittensor EVM with Validator Incentives</h3>
</p>

<p align="center">
  <a href="https://github.com/casinotao/casinotao/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  </a>
  <a href="https://bittensor.com">
    <img src="https://img.shields.io/badge/Bittensor-Subnet-green.svg" alt="Bittensor Subnet">
  </a>
  <img src="https://img.shields.io/badge/Python-3.9+-yellow.svg" alt="Python 3.9+">
</p>

---

## 📖 Overview

**Casino TAO** is a Bittensor subnet that incentivizes participation in a decentralized P2P betting protocol deployed on Bittensor EVM. Miners earn rewards by placing bets on the TAO Casino smart contract, with rewards distributed based on time-decayed betting volume over a 7-day window.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      Casino TAO Subnet                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐         ┌─────────────┐         ┌─────────────┐  │
│   │  Miner  │ ──bet──▶│ TAO Casino  │◀──query─│  Validator  │  │
│   │         │         │  Contract   │         │             │  │
│   └─────────┘         │  (EVM)      │         └──────┬──────┘  │
│        │              └─────────────┘                │         │
│        │                                             │         │
│        └──────────── rewards ◀───────────────────────┘         │
│                    (based on betting volume)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

1. **Miners** place bets on the TAO Casino smart contract using native TAO
2. **Validators** query the smart contract for each miner's betting volume
3. **Rewards** are distributed based on time-decayed betting activity (recent bets weighted higher)
4. **Weights** are set on the Bittensor network every ~72 minutes

---

## ✨ Key Features

### 🎲 TAO Casino Smart Contract
- **Dual-Position Betting**: Bet on Red, Blue, or both sides simultaneously
- **Game Modes**: Classic (majority wins) and Underdog (minority wins)
- **Game Speeds**: Regular (105 min) and Rapid (10 min)
- **Referral System**: Earn 10% of platform fees from referrals
- **Underdog Bonus**: Reduced fees when betting on the smaller side
- **Leaderboard**: Track top winners on-chain

### ⚡ Validator Features
- **Time-Decayed Rewards**: 7-day window with exponential decay (recent activity weighted higher)
- **REST API**: Query validator state, scores, volumes, and leaderboards
- **Snapshot Storage**: Historical weight data stored in SQLite
- **Automatic Weight Setting**: Every 360 blocks (~72 minutes)

### 🔗 Bittensor Integration
- Native TAO betting on Bittensor EVM
- Coldkey-to-EVM wallet mapping with cryptographic verification
- Seamless integration with Bittensor metagraph

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Validator Guide](docs/validator.md) | How to run a Casino TAO validator |
| [Miner Guide](docs/miner.md) | How to participate as a miner |
| [Running on Mainnet](docs/running_on_mainnet.md) | Production deployment guide |
| [Running on Testnet](docs/running_on_testnet.md) | Testing and development guide |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Bittensor wallet
- TAO for betting (miners) or staking (validators)

### Installation

```bash
# Clone the repository
git clone https://github.com/casinotao/casinotao.git
cd casinotao

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
```

### Running a Validator

```bash
python validator/validator.py \
    --netuid <NETUID> \
    --wallet.name <WALLET_NAME> \
    --wallet.hotkey <HOTKEY_NAME> \
    --subtensor.network finney
```

### Becoming a Miner

1. Register on the subnet with your Bittensor wallet
2. Link your coldkey to an EVM address via the Casino TAO frontend
3. Place bets on the TAO Casino smart contract
4. Earn rewards based on your betting volume!

See the [Miner Guide](docs/miner.md) for detailed instructions.

---

## 🏗️ Architecture

```
casinotao/
├── contracts/              # Solidity smart contracts
│   └── TAO_Casino.sol      # Main betting contract
├── taocasino/              # Python package
│   ├── base/               # Base neuron classes
│   ├── core/               # Constants and configuration
│   ├── utils/              # Utility functions
│   └── validator/          # Validator logic
│       ├── api.py          # REST API endpoints
│       ├── contract.py     # EVM contract interaction
│       ├── database.py     # SQLite storage
│       ├── forward.py      # Volume checking logic
│       └── reward.py       # Reward calculation
├── validator/              # Validator entry point
│   └── validator.py
├── docs/                   # Documentation
└── requirements.txt
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BITTENSOR_EVM_RPC` | Bittensor EVM RPC endpoint | `https://lite.chain.opentensor.ai` |
| `API_PORT` | Validator API port | `8000` |

### Time Decay Weights

Betting volume is weighted based on recency:

| Day | Weight |
|-----|--------|
| Today | 1.00 |
| Yesterday | 0.85 |
| 2 days ago | 0.70 |
| 3 days ago | 0.55 |
| 4 days ago | 0.40 |
| 5 days ago | 0.25 |
| 6 days ago | 0.10 |

---

## 📊 Validator API

The validator exposes a REST API for querying state:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Validator health status |
| `GET /scores` | Current miner scores |
| `GET /volumes` | Current betting volumes |
| `GET /leaderboard` | Top miners by score |
| `GET /snapshots` | Historical weight snapshots |
| `POST /api/wallet-mapping` | Register coldkey-to-EVM mapping |

API documentation available at `http://localhost:8000/docs`

---

## 🔐 Security

- **Signature Verification**: Wallet mappings require cryptographic proof of coldkey ownership
- **Reentrancy Protection**: Smart contract uses OpenZeppelin's ReentrancyGuard
- **Access Control**: Admin functions protected by Ownable pattern

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Bittensor**: [https://bittensor.com](https://bittensor.com)
- **Bittensor Discord**: [https://discord.gg/bittensor](https://discord.gg/bittensor)

---

<p align="center">
  <b>Built on Bittensor 🧠</b>
</p>
