"""Price monitoring daemon for active positions."""

import asyncio
import logging
import time
from typing import Optional

import aiohttp

logger = logging.getLogger("sniper.price_monitor")

DEXSCREENER_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens"


class PriceMonitor:
    """Poll DexScreener for active position prices and trigger TP sells."""

    def __init__(self, config: dict, position_manager, trader):
        self.config = config
        self.pm = position_manager
        self.trader = trader
        
        monitor_cfg = config.get("price_monitor", {})
        self.poll_interval = monitor_cfg.get("poll_interval_seconds", 30)
        self.log_interval = monitor_cfg.get("log_interval_seconds", 300)
        self._last_price_log: dict[str, float] = {}  # ca -> last_log_time
        self._running = False

    async def fetch_prices(self, contract_addresses: list[str]) -> dict[str, float]:
        """Fetch current USD prices for multiple tokens from DexScreener.
        
        Returns dict of {contract_address: price_usd}.
        DexScreener supports comma-separated addresses (max ~30 per call).
        """
        if not contract_addresses:
            return {}

        prices = {}

        # DexScreener allows multiple tokens per call
        # Process in batches of 20
        for i in range(0, len(contract_addresses), 20):
            batch = contract_addresses[i:i+20]
            addresses_str = ",".join(batch)
            url = f"{DEXSCREENER_TOKEN_URL}/{addresses_str}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 429:
                            logger.warning("DexScreener rate limited, backing off 60s")
                            await asyncio.sleep(60)
                            continue
                        if resp.status != 200:
                            logger.warning(f"DexScreener returned {resp.status}")
                            continue

                        data = await resp.json()
                        pairs = data.get("pairs") or []

                        for pair in pairs:
                            base_token = pair.get("baseToken", {})
                            ca = base_token.get("address", "")
                            price_str = pair.get("priceUsd")

                            if ca and price_str:
                                try:
                                    price = float(price_str)
                                    # Keep highest liquidity pair price
                                    if ca not in prices:
                                        prices[ca] = price
                                except (ValueError, TypeError):
                                    continue

            except asyncio.TimeoutError:
                logger.warning("DexScreener request timed out")
            except Exception as e:
                logger.error(f"DexScreener fetch error: {e}")

        return prices

    async def check_and_execute_tp(self, ca: str, current_price: float):
        """Check TP ladder and execute sells for a position."""
        triggered_tiers = self.pm.check_tp_ladder(ca, current_price)

        if not triggered_tiers:
            return

        pos = self.pm.get_position(ca)
        if not pos:
            return

        for tier_info in triggered_tiers:
            tier = tier_info["tier"]
            sell_qty = tier_info["sell_quantity"]
            multiplier = tier_info["multiplier"]

            logger.info(
                f"🎯 TP TRIGGERED! {pos['token_name']} hit {multiplier}x "
                f"(${current_price:.8f}) — selling {sell_qty:.4f} tokens"
            )

            try:
                # Convert quantity to raw token amount
                # NOTE: This assumes we're tracking raw amounts; may need
                # decimal adjustment per token
                sell_amount_raw = int(sell_qty)
                if sell_amount_raw <= 0:
                    sell_amount_raw = 1  # Minimum sell

                result = await self.trader.sell_token(
                    contract_address=ca,
                    token_amount=sell_amount_raw,
                )

                realized_usd = result.get("usd_received", 0)
                tx_sig = result.get("tx_signature", "")

                # Record in position manager
                self.pm.execute_tp(
                    ca=ca,
                    tier=tier,
                    sell_quantity=sell_qty,
                    realized_usd=realized_usd,
                    price_usd=current_price,
                    tx_signature=tx_sig,
                )

                logger.info(
                    f"✅ TP {multiplier}x executed for {pos['token_name']}: "
                    f"sold for ${realized_usd:.2f} | tx: {tx_sig[:16]}..."
                )

            except Exception as e:
                logger.error(
                    f"❌ TP execution failed for {pos['token_name']} "
                    f"tier {tier}: {e}"
                )

    def _should_log_price(self, ca: str) -> bool:
        """Rate limit price logging to avoid spam."""
        now = time.time()
        last = self._last_price_log.get(ca, 0)
        if now - last >= self.log_interval:
            self._last_price_log[ca] = now
            return True
        return False

    async def poll_once(self):
        """Single poll cycle — fetch prices, check TPs."""
        positions = self.pm.get_active_positions()
        if not positions:
            return

        cas = [p["contract_address"] for p in positions]
        prices = await self.fetch_prices(cas)

        for pos in positions:
            ca = pos["contract_address"]
            price = prices.get(ca)

            if price is None:
                continue

            # Calculate current multiplier
            entry_price = pos["entry_price_usd"]
            if entry_price > 0:
                multiplier = price / entry_price
            else:
                multiplier = 0

            # Log periodically
            if self._should_log_price(ca):
                logger.info(
                    f"📊 {pos['token_name']:10s} | "
                    f"${price:.8f} | "
                    f"{multiplier:.1f}x | "
                    f"tier {pos['current_tier']}"
                )

            # Check and execute TP
            await self.check_and_execute_tp(ca, price)

    async def run(self):
        """Start the price monitoring loop."""
        logger.info(
            f"Price monitor started (interval: {self.poll_interval}s, "
            f"log every: {self.log_interval}s)"
        )
        self._running = True

        while self._running:
            try:
                await self.poll_once()
            except Exception as e:
                logger.error(f"Price monitor error: {e}")

            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Price monitor stopped")
