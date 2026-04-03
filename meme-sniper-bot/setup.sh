#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Meme Sniper Bot Setup ==="
echo ""

# Install Python dependencies
echo "[1/3] Installing Python dependencies..."
pip install -r requirements.txt

# Create directories
echo "[2/3] Creating directories..."
mkdir -p db wallet

# Generate wallet if not exists
echo "[3/3] Checking wallet..."
if [ ! -f wallet/keypair.json ]; then
    echo "Generating new Solana wallet..."
    python3 -c "
from src.wallet import WalletManager
import yaml

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

wm = WalletManager(cfg)
pubkey = wm.generate_keypair()
print(f'')
print(f'========================================')
print(f'  NEW WALLET GENERATED')
print(f'  Public Key: {pubkey}')
print(f'  Keypair saved to: wallet/keypair.json')
print(f'========================================')
print(f'')
print(f'  Fund this wallet with ~\$35 of SOL')
print(f'  (\$30 capital + \$5 for gas fees)')
print(f'')
"
else
    python3 -c "
from src.wallet import WalletManager
import yaml

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

wm = WalletManager(cfg)
wm.load_keypair()
print(f'Wallet already exists: {wm.public_key}')
"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in config.yaml (Telegram API credentials, etc.)"
echo "  2. Fund your wallet with SOL"
echo "  3. Run: python main.py"
