# 🚀 Running on Mainnet

This guide covers deploying and running Casino TAO on Bittensor mainnet (Finney).

---

## Network Information

| Property | Value |
|----------|-------|
| **Network** | Bittensor Finney (Mainnet) |
| **Subnet UID** | TBD |
| **EVM RPC** | `https://lite.chain.opentensor.ai` |
| **EVM Chain ID** | `964` |
| **Contract Address** | `0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93` |

---

## Prerequisites

Before deploying to mainnet:

1. ✅ Tested thoroughly on testnet
2. ✅ Sufficient TAO for registration and operations
3. ✅ Reliable server with high uptime
4. ✅ Secure key management in place
5. ✅ Monitoring and alerting configured

---

## Validator Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.10 python3.10-venv python3-pip git -y

# Install Node.js (for PM2)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2
sudo npm install -g pm2
```

### 2. Clone and Install

```bash
# Clone repository
git clone https://github.com/casinotao/casinotao.git
cd casinotao

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install package
pip install -e .
```

### 3. Wallet Setup

```bash
# Create wallet (if new)
btcli wallet new_coldkey --wallet.name validator_main
btcli wallet new_hotkey --wallet.name validator_main --wallet.hotkey default

# Or restore existing wallet
btcli wallet regen_coldkey --wallet.name validator_main
```

> ⚠️ **Security**: Store your mnemonic securely offline. Never share it.

### 4. Register as Validator

```bash
btcli subnet register \
    --netuid <CASINOTAO_NETUID> \
    --wallet.name validator_main \
    --wallet.hotkey default \
    --subtensor.network finney
```

### 5. Stake TAO

Validators need stake to have weight in the network:

```bash
btcli stake add \
    --wallet.name validator_main \
    --wallet.hotkey default \
    --amount <AMOUNT> \
    --subtensor.network finney
```

### 6. Start Validator

```bash
# Using PM2 (recommended)
pm2 start validator/validator.py \
    --name casinotao-validator \
    --interpreter /path/to/casinotao/venv/bin/python \
    -- \
    --netuid <CASINOTAO_NETUID> \
    --wallet.name validator_main \
    --wallet.hotkey default \
    --subtensor.network finney \
    --neuron.api_port 8000

# Save PM2 config
pm2 save

# Setup auto-restart on reboot
pm2 startup
```

### 7. Verify Deployment

```bash
# Check PM2 status
pm2 status

# View logs
pm2 logs casinotao-validator

# Check API
curl http://localhost:8000/health
```

---

## Miner Deployment

### 1. Register on Subnet

```bash
btcli subnet register \
    --netuid <CASINOTAO_NETUID> \
    --wallet.name miner_main \
    --wallet.hotkey default \
    --subtensor.network finney
```

### 2. Link Wallet

Connect your coldkey to your EVM address via the Casino TAO frontend or API.

### 3. Bridge TAO to EVM

Transfer TAO to your EVM wallet on Bittensor EVM mainnet:
- Chain ID: 964
- RPC: `https://lite.chain.opentensor.ai`

### 4. Start Betting

Place bets on the TAO Casino contract at:
`0x3b68322FC1Cb27A2c82477E86cbDde2E4850eE93`

---

## Production Configuration

### Environment Variables

Create `.env` file:

```bash
# Bittensor
SUBTENSOR_NETWORK=finney
NETUID=<CASINOTAO_NETUID>
WALLET_NAME=validator_main
WALLET_HOTKEY=default

# API
API_PORT=8000
API_HOST=0.0.0.0

# Logging
LOG_LEVEL=info
```

### Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22

# Allow Bittensor P2P (if serving axon)
sudo ufw allow 8091

# Allow API (restrict to trusted IPs in production)
sudo ufw allow from <TRUSTED_IP> to any port 8000

# Enable firewall
sudo ufw enable
```

### Nginx Reverse Proxy (Optional)

For SSL termination and rate limiting:

```nginx
server {
    listen 443 ssl;
    server_name api.casinotao.example.com;

    ssl_certificate /etc/letsencrypt/live/api.casinotao.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.casinotao.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
}
```

---

## Monitoring

### PM2 Monitoring

```bash
# Status
pm2 status

# Logs
pm2 logs casinotao-validator --lines 100

# Metrics
pm2 monit
```

### Health Check Script

Create `/usr/local/bin/casinotao-health.sh`:

```bash
#!/bin/bash

HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$HEALTH" != "200" ]; then
    echo "Health check failed: $HEALTH"
    # Send alert (e.g., via webhook, email, etc.)
    curl -X POST "https://hooks.slack.com/services/..." \
        -H "Content-Type: application/json" \
        -d '{"text":"⚠️ Casino TAO Validator health check failed!"}'
    exit 1
fi

echo "Health check passed"
exit 0
```

Add to crontab:

```bash
*/5 * * * * /usr/local/bin/casinotao-health.sh >> /var/log/casinotao-health.log 2>&1
```

### Prometheus Metrics (Advanced)

Add a metrics endpoint to collect:
- Active miners count
- Total weighted volume
- Weight commit success rate
- API latency

---

## Backup and Recovery

### Backup Wallet

```bash
# Backup wallet files
tar -czvf wallet-backup.tar.gz ~/.bittensor/wallets/validator_main/

# Store securely offline
```

### Backup Database

```bash
# Backup validator database
cp validator_data.db validator_data.db.backup.$(date +%Y%m%d)

# Or setup automated backups
0 */6 * * * cp /path/to/casinotao/validator_data.db /backups/validator_data.db.$(date +\%Y\%m\%d\%H\%M)
```

### Recovery

```bash
# Restore wallet
tar -xzvf wallet-backup.tar.gz -C ~/

# Restore database
cp validator_data.db.backup validator_data.db

# Restart validator
pm2 restart casinotao-validator
```

---

## Updating

### Standard Update

```bash
cd casinotao

# Pull latest changes
git pull origin main

# Activate environment
source venv/bin/activate

# Update dependencies
pip install -e .

# Restart
pm2 restart casinotao-validator
```

### Zero-Downtime Update (Advanced)

For critical updates, consider running two validators temporarily:

1. Deploy new version to secondary server
2. Verify it's working
3. Update primary server
4. Decommission secondary

---

## Troubleshooting

### Validator Not Setting Weights

Check:
1. Sufficient stake
2. Correct netuid
3. Network connectivity
4. Rate limiting (min 360 blocks between commits)

```bash
# Check stake
btcli wallet overview --wallet.name validator_main

# Check logs
pm2 logs casinotao-validator | grep -i weight
```

### High Memory Usage

If memory grows over time:

```bash
# Check memory
pm2 monit

# Restart if needed
pm2 restart casinotao-validator

# Consider adding memory limit
pm2 start ... --max-memory-restart 2G
```

### Database Corruption

If database becomes corrupted:

```bash
# Stop validator
pm2 stop casinotao-validator

# Remove corrupted database (validator will recreate)
rm validator_data.db

# Restart
pm2 start casinotao-validator
```

---

## Security Checklist

- [ ] Wallet files have restricted permissions (`chmod 600`)
- [ ] Server has firewall enabled
- [ ] SSH uses key-based auth (no passwords)
- [ ] API access restricted to trusted IPs
- [ ] Regular security updates applied
- [ ] Wallet mnemonic stored offline
- [ ] Monitoring and alerts configured
- [ ] Backups tested and working

---

## Cost Estimation

| Item | Estimated Cost |
|------|----------------|
| Server (4 CPU, 8GB RAM) | $40-80/month |
| Registration Fee | ~0.1 TAO |
| Validator Stake | Variable (more stake = more influence) |
| Miner Betting Capital | As desired |

---

## Support

- **GitHub Issues**: Report bugs and feature requests
- **Discord**: Community support and discussions
- **Documentation**: Check other guides in `/docs`

---

<p align="center">
  <b>Welcome to Mainnet! 🎰</b>
</p>
