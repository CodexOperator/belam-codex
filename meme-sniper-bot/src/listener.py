"""Telegram group listener using Telethon userbot."""

import asyncio
import logging
from typing import Optional

from telethon import TelegramClient, events
from telethon.tl.types import Message

from src.classifier import PostClassifier, Classification
from src.position_manager import PositionManager
from src.trader import Trader
from src.utils import extract_solana_ca

logger = logging.getLogger("sniper.listener")


class TelegramListener:
    """Listen to a Telegram group and act on trading signals."""

    def __init__(
        self,
        config: dict,
        classifier: PostClassifier,
        position_manager: PositionManager,
        trader: Trader,
    ):
        self.config = config
        self.classifier = classifier
        self.pm = position_manager
        self.trader = trader

        tg_cfg = config.get("telegram", {})
        self.api_id = int(tg_cfg["api_id"])
        self.api_hash = tg_cfg["api_hash"]
        self.phone = tg_cfg["phone"]
        self.group = tg_cfg.get("group", "inside_calls")
        self.session_name = tg_cfg.get("session_name", "sniper_session")

        trade_cfg = config.get("trading", {})
        self.per_trade_amount = trade_cfg.get("per_trade_amount", 3.0)
        self.dry_run = trade_cfg.get("dry_run", True)

        self.client: Optional[TelegramClient] = None
        self._resolved_group = None

    async def start(self):
        """Initialize Telethon client and start listening."""
        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash,
        )

        await self.client.start(phone=self.phone)
        logger.info(f"Telegram client started as {self.phone}")

        # Resolve group
        try:
            self._resolved_group = await self.client.get_entity(self.group)
            logger.info(
                f"Listening to group: {getattr(self._resolved_group, 'title', self.group)}"
            )
        except Exception as e:
            logger.error(f"Failed to resolve group '{self.group}': {e}")
            raise

        # Register message handler
        @self.client.on(events.NewMessage(chats=self._resolved_group))
        async def handler(event: events.NewMessage.Event):
            await self._handle_message(event.message)

        logger.info("Message handler registered. Waiting for signals...")
        await self.client.run_until_disconnected()

    async def _handle_message(self, message: Message):
        """Process an incoming message from the target group."""
        text = message.text or message.message or ""
        if not text.strip():
            return

        # Truncate for logging
        preview = text[:80].replace("\n", " ")
        logger.debug(f"New message: {preview}...")

        # Classify
        try:
            result = self.classifier.classify(text)
            # Handle both sync and async
            if asyncio.iscoroutine(result):
                result = await result
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return

        logger.info(
            f"Classified as {result.classification.value} "
            f"(confidence: {result.confidence:.0%}): "
            f"{result.token_name or 'unknown'} | "
            f"{result.reason}"
        )

        if result.classification == Classification.FRESH_BUY:
            await self._handle_fresh_buy(result, text)
        elif result.classification == Classification.DIP_ADD:
            await self._handle_dip_add(result, text)
        elif result.classification == Classification.UPDATE:
            logger.info(f"Update post for {result.token_name} — skipping")
        else:
            logger.debug("Noise — skipping")

    async def _handle_fresh_buy(self, result, source_text: str):
        """Execute a fresh buy."""
        ca = result.contract_address
        if not ca:
            logger.warning("Fresh buy classified but no CA extracted — skipping")
            return

        # Double-check no existing position
        if self.pm.has_active_position(ca):
            logger.info(f"Already have position for {ca[:12]}... — treating as dip add")
            await self._handle_dip_add(result, source_text)
            return

        # Check available capital
        portfolio = self.pm.get_portfolio_summary()
        if portfolio["available_capital"] < self.per_trade_amount:
            logger.warning(
                f"Insufficient capital: ${portfolio['available_capital']:.2f} < "
                f"${self.per_trade_amount:.2f} — skipping buy"
            )
            await self._notify(
                f"⚠️ Skipped {result.token_name}: insufficient capital "
                f"(${portfolio['available_capital']:.2f} available)"
            )
            return

        logger.info(
            f"🚀 BUYING ${self.per_trade_amount:.2f} of "
            f"{result.token_name} ({ca[:12]}...)"
        )

        try:
            trade_result = await self.trader.buy_token(ca, self.per_trade_amount)

            # Record position
            self.pm.open_position(
                token_name=result.token_name or "UNKNOWN",
                ca=ca,
                entry_price=trade_result.get("token_price_approx", 0),
                quantity=trade_result.get("token_quantity_raw", 0),
                amount_usd=self.per_trade_amount,
                dex_url=result.dex_url,
                source_msg=source_text[:500],
                tx_signature=trade_result.get("tx_signature"),
            )

            tx = trade_result.get("tx_signature", "N/A")
            mode = "[DRY RUN] " if self.dry_run else ""

            await self._notify(
                f"🟢 {mode}Bought ${self.per_trade_amount:.2f} of "
                f"${result.token_name}\n"
                f"CA: {ca}\n"
                f"TX: {tx}\n"
                f"Dex: {result.dex_url or 'N/A'}"
            )

        except Exception as e:
            logger.error(f"Buy failed for {result.token_name}: {e}")
            await self._notify(
                f"❌ Buy FAILED for ${result.token_name}: {e}"
            )

    async def _handle_dip_add(self, result, source_text: str):
        """Add to an existing position."""
        ca = result.contract_address
        if not ca:
            return

        if not self.pm.has_active_position(ca):
            logger.info(f"No existing position for dip add on {ca[:12]}... — treating as fresh buy")
            await self._handle_fresh_buy(result, source_text)
            return

        portfolio = self.pm.get_portfolio_summary()
        if portfolio["available_capital"] < self.per_trade_amount:
            logger.warning(f"Insufficient capital for dip add — skipping")
            return

        logger.info(
            f"📈 DIP ADD: ${self.per_trade_amount:.2f} to "
            f"{result.token_name} ({ca[:12]}...)"
        )

        try:
            trade_result = await self.trader.buy_token(ca, self.per_trade_amount)

            self.pm.add_to_position(
                ca=ca,
                additional_amount=self.per_trade_amount,
                quantity=trade_result.get("token_quantity_raw", 0),
                price=trade_result.get("token_price_approx", 0),
                tx_signature=trade_result.get("tx_signature"),
            )

            mode = "[DRY RUN] " if self.dry_run else ""
            await self._notify(
                f"🔵 {mode}Added ${self.per_trade_amount:.2f} to "
                f"${result.token_name} (dip buy)\n"
                f"CA: {ca}"
            )

        except Exception as e:
            logger.error(f"Dip add failed for {result.token_name}: {e}")

    async def _notify(self, text: str):
        """Send notification to Saved Messages (self DM)."""
        if not self.client:
            return
        try:
            await self.client.send_message("me", text)
        except Exception as e:
            logger.warning(f"Failed to send self-notification: {e}")

    async def stop(self):
        """Disconnect the Telegram client."""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")
