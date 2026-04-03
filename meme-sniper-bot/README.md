# 🎯 Meme Token Sniper Bot

Automated Telegram signal → Solana swap bot with LLM-powered post classification and configurable take-profit ladders.

## How It Works

1. **Listens** to a Telegram group (via Telethon userbot)
2. **Classifies** each post: fresh buy signal vs update/noise (LLM + regex)
3. **Buys** automatically via Jupiter Aggregator when a fresh call is detected
4. **Monitors** prices via DexScreener and executes take-profit sells at configurable tiers
5. **Tracks** everything in SQLite with full trade history

## TP Ladder (per $3 position)

| Trigger | Action | Example |
|---------|--------|---------|
| 2x | Sell 2/3 | Take $4.00, ride $2.00 |
| 4x | Sell 20% of remaining | Take $0.40, ride $1.60 |
| 8x | Sell 20% of remaining | Take $0.32, ride $1.28 |
| 15x | Sell 20% of remaining | Take $0.26, ride $1.02 |
| 25x | Sell 20% of remaining | Take $0.20, ride $0.82 |
| 100x | Sell 20% of remaining | Take $0.16, moonbag $0.66 |

## Setup

### 1. Get Telegram API Credentials

Go to [my.telegram.org](https://my.telegram.org):
- Log in with your phone number
- Go to "API development tools"
- Create an app → note the `api_id` and `api_hash`

### 2. Install Dependencies

```bash
cd meme-sniper-bot
chmod +x setup.sh
./setup.sh
```

This installs Python packages and generates a new Solana wallet.

### 3. Fund Your Wallet

The setup script prints your wallet address. Send it:
- ~$30 worth of SOL (trading capital)
- ~$5 extra SOL for gas fees
- Total: ~$35 of SOL

### 4. Configure

Edit `config.yaml`:

```yaml
telegram:
  api_id: "YOUR_API_ID"
  api_hash: "YOUR_API_HASH"
  phone: "+1234567890"
  group: "inside_calls"

trading:
  dry_run: true  # Start with dry run!

classifier:
  api_key: "sk-ant-..."  # Anthropic API key
```

### 5. First Run (Dry Mode)

```bash
python main.py
```

First time, Telethon will ask for your phone code. After that, the session is saved.

Dry run mode logs everything but doesn't execute swaps. Watch the logs to verify the classifier is working correctly.

### 6. Go Live

Once you're confident the classifier is accurate:

```yaml
trading:
  dry_run: false
```

## Usage

### Check Positions
```bash
python -m src.position_manager positions
```

### Portfolio Summary
```bash
python -m src.position_manager summary
```

### Export to CSV
```bash
python -m src.position_manager export [filename.csv]
```

## Architecture

```
main.py
 ├── TelegramListener (Telethon userbot)
 │    └── PostClassifier (Anthropic Claude + regex fallback)
 │         └── Trader.buy_token() → Jupiter V6 API
 │              └── PositionManager.open_position() → SQLite
 │
 └── PriceMonitor (background async loop)
      └── DexScreener API → check_tp_ladder()
           └── Trader.sell_token() → Jupiter V6 API
                └── PositionManager.execute_tp() → SQLite
```

## Files

| File | Purpose |
|------|---------|
| `config.yaml` | All configuration |
| `main.py` | Entry point |
| `src/listener.py` | Telegram group listener |
| `src/classifier.py` | LLM post classifier |
| `src/trader.py` | Jupiter swap execution |
| `src/position_manager.py` | SQLite position tracking |
| `src/price_monitor.py` | Price polling + TP triggers |
| `src/wallet.py` | Solana wallet management |
| `src/utils.py` | Shared utilities + regex patterns |
| `wallet/keypair.json` | Your wallet (DO NOT SHARE) |
| `db/sniper.db` | Position database |

## Security Notes

- **wallet/keypair.json** contains your private key. Never share it.
- The `.gitignore` excludes wallet/ and db/ directories.
- Telethon session file (`sniper_session.session`) also contains auth — don't share.
- Consider using a separate Telegram account for the bot.

## Troubleshooting

**"No CA found" on valid posts**: The regex looks for base58 strings 32-44 chars. If the CA is in a URL only, make sure the DexScreener/Birdeye pattern matches.

**"Jupiter quote error"**: The token might not have enough liquidity. Check DexScreener directly.

**"Insufficient capital"**: All $30 is deployed. Wait for TP sells to free up capital or add more SOL.

**Telethon flood wait**: Telegram rate limiting. The bot will wait automatically.

**RPC errors**: The free Solana RPC has rate limits. Consider using a paid RPC (Helius, QuickNode) for production:
```yaml
solana:
  rpc_url: "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY"
```
