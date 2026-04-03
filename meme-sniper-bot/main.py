#!/usr/bin/env python3
"""Meme Token Sniper Bot — Entry Point.

Listens to a Telegram group for meme coin calls, buys automatically,
and manages take-profit exits via a configurable ladder.
"""

import asyncio
import logging
import signal
import sys

from src.utils import load_config, setup_logging
from src.wallet import WalletManager
from src.position_manager import PositionManager
from src.trader import Trader
from src.classifier import PostClassifier
from src.price_monitor import PriceMonitor
from src.listener import TelegramListener

logger = logging.getLogger("sniper.main")


async def main():
    # Load config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)
    setup_logging(config)

    dry_run = config.get("trading", {}).get("dry_run", True)
    if dry_run:
        logger.info("=" * 50)
        logger.info("  DRY RUN MODE — no real swaps will execute")
        logger.info("  Set trading.dry_run: false in config.yaml to go live")
        logger.info("=" * 50)

    # Initialize wallet
    logger.info("Initializing wallet...")
    wallet = WalletManager(config)
    try:
        wallet.load_keypair()
        logger.info(f"Wallet loaded: {wallet.public_key}")
    except FileNotFoundError:
        pubkey = wallet.generate_keypair()
        logger.info(f"New wallet generated: {pubkey}")
        logger.info(f"Fund this address with ~$35 of SOL before going live!")

    # Show balance
    try:
        sol_balance = await wallet.get_sol_balance()
        logger.info(f"SOL balance: {sol_balance:.4f} SOL")
        if sol_balance < 0.01 and not dry_run:
            logger.warning("⚠️  Very low SOL balance! Fund your wallet before going live.")
    except Exception as e:
        logger.warning(f"Could not fetch balance: {e}")

    # Initialize components
    position_manager = PositionManager(config)
    trader = Trader(config, wallet_keypair=wallet.keypair)
    
    classifier = PostClassifier(
        config,
        position_checker=position_manager.has_active_position,
    )

    price_monitor = PriceMonitor(config, position_manager, trader)
    listener = TelegramListener(config, classifier, position_manager, trader)

    # Show portfolio summary
    summary = position_manager.get_portfolio_summary()
    logger.info(
        f"Portfolio: ${summary['available_capital']:.2f} available / "
        f"${summary['total_capital']:.2f} total | "
        f"{summary['active_positions']} active positions"
    )

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig, frame):
        logger.info(f"Received {signal.Signals(sig).name}, shutting down...")
        price_monitor.stop()
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Start price monitor in background
    monitor_task = asyncio.create_task(price_monitor.run())
    logger.info("Price monitor started in background")

    # Start Telegram listener (blocks until disconnect)
    try:
        logger.info("Starting Telegram listener...")
        await listener.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Listener error: {e}")
    finally:
        price_monitor.stop()
        await listener.stop()
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

    logger.info("Bot shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
