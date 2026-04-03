"""Jupiter Aggregator V6 API integration for Solana swaps."""

import logging
from typing import Optional

import aiohttp
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from src.utils import SOL_MINT, sol_to_lamports

logger = logging.getLogger("sniper.trader")

JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_URL = "https://quote-api.jup.ag/v6/swap"
JUPITER_PRICE_URL = "https://price.jup.ag/v6/price"


class Trader:
    """Execute swaps via Jupiter Aggregator."""

    def __init__(self, config: dict, wallet_keypair: Optional[Keypair] = None):
        self.config = config
        self.keypair = wallet_keypair
        self.slippage_bps = config.get("trading", {}).get("slippage_bps", 500)
        self.dry_run = config.get("trading", {}).get("dry_run", True)
        self.rpc_url = config.get("solana", {}).get(
            "rpc_url", "https://api.mainnet-beta.solana.com"
        )

    def set_keypair(self, keypair: Keypair):
        """Set the wallet keypair for signing transactions."""
        self.keypair = keypair

    async def get_sol_price_usd(self) -> float:
        """Get current SOL price in USD via Jupiter Price API."""
        async with aiohttp.ClientSession() as session:
            params = {"ids": "SOL"}
            async with session.get(JUPITER_PRICE_URL, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"Jupiter price API error: {resp.status}")
                data = await resp.json()
                return float(data["data"]["SOL"]["price"])

    async def get_token_price(self, contract_address: str) -> Optional[float]:
        """Get token price in USD via Jupiter Price API."""
        async with aiohttp.ClientSession() as session:
            params = {"ids": contract_address}
            async with session.get(JUPITER_PRICE_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                token_data = data.get("data", {}).get(contract_address)
                if token_data:
                    return float(token_data["price"])
                return None

    async def usd_to_sol_lamports(self, usd_amount: float) -> int:
        """Convert USD amount to SOL lamports."""
        sol_price = await self.get_sol_price_usd()
        sol_amount = usd_amount / sol_price
        return sol_to_lamports(sol_amount)

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: Optional[int] = None,
    ) -> dict:
        """Get a swap quote from Jupiter.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address  
            amount: Amount in smallest units (lamports for SOL)
            slippage_bps: Slippage tolerance in basis points
        """
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": slippage_bps or self.slippage_bps,
            "onlyDirectRoutes": "false",
            "asLegacyTransaction": "false",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(JUPITER_QUOTE_URL, params=params) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Jupiter quote error ({resp.status}): {error_text}")
                quote = await resp.json()
                
                if "error" in quote:
                    raise Exception(f"Jupiter quote error: {quote['error']}")
                
                in_amount = int(quote.get("inAmount", 0))
                out_amount = int(quote.get("outAmount", 0))
                logger.info(
                    f"Quote: {input_mint[:8]}... -> {output_mint[:8]}... | "
                    f"in={in_amount} out={out_amount}"
                )
                return quote

    async def execute_swap(self, quote: dict) -> Optional[str]:
        """Execute a swap from a Jupiter quote.
        
        Returns transaction signature or None if dry run.
        """
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would swap {quote.get('inAmount')} -> {quote.get('outAmount')}"
            )
            return "DRY_RUN_TX_SIG"

        if not self.keypair:
            raise ValueError("No wallet keypair set. Call set_keypair() first.")

        user_pubkey = str(self.keypair.pubkey())

        # Get swap transaction
        swap_payload = {
            "quoteResponse": quote,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(JUPITER_SWAP_URL, json=swap_payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Jupiter swap error ({resp.status}): {error_text}")
                swap_data = await resp.json()

            if "error" in swap_data:
                raise Exception(f"Jupiter swap error: {swap_data['error']}")

            # Deserialize and sign the transaction
            swap_tx_bytes = bytes(swap_data["swapTransaction"], "utf-8")
            import base64
            raw_tx = base64.b64decode(swap_tx_bytes)
            tx = VersionedTransaction.from_bytes(raw_tx)

            # Sign
            signed_tx = VersionedTransaction(tx.message, [self.keypair])

            # Send to RPC
            async with session.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        base64.b64encode(bytes(signed_tx)).decode("utf-8"),
                        {"encoding": "base64", "skipPreflight": True,
                         "maxRetries": 3},
                    ],
                },
            ) as resp:
                result = await resp.json()

                if "error" in result:
                    raise Exception(f"RPC error: {result['error']}")

                tx_sig = result["result"]
                logger.info(f"Swap executed: {tx_sig}")
                return tx_sig

    async def buy_token(
        self, contract_address: str, usd_amount: float
    ) -> dict:
        """Buy a token with a USD amount of SOL.
        
        Returns dict with quote details and tx signature.
        """
        logger.info(f"Buying ${usd_amount:.2f} of {contract_address[:12]}...")

        # Convert USD to SOL lamports
        lamports = await self.usd_to_sol_lamports(usd_amount)
        sol_price = await self.get_sol_price_usd()

        # Get quote: SOL -> Token
        quote = await self.get_quote(
            input_mint=SOL_MINT,
            output_mint=contract_address,
            amount=lamports,
        )

        out_amount = int(quote.get("outAmount", 0))

        # Get token price for records
        token_price = None
        if out_amount > 0:
            # Approximate price from quote
            sol_amount = lamports / 1e9
            usd_spent = sol_amount * sol_price
            # outAmount is in token's smallest unit — we need decimals
            # For now use the raw amount; price monitor will get accurate price
            token_price = usd_spent / out_amount if out_amount > 0 else None

        # Execute swap
        tx_sig = await self.execute_swap(quote)

        return {
            "tx_signature": tx_sig,
            "sol_spent_lamports": lamports,
            "sol_price_usd": sol_price,
            "usd_amount": usd_amount,
            "token_quantity_raw": out_amount,
            "token_price_approx": token_price,
            "quote": quote,
        }

    async def sell_token(
        self, contract_address: str, token_amount: int, decimals: int = 6
    ) -> dict:
        """Sell tokens back to SOL.
        
        Args:
            contract_address: Token mint address
            token_amount: Amount in smallest token units
            decimals: Token decimals (for logging)
        """
        logger.info(f"Selling {token_amount} of {contract_address[:12]}...")

        # Get quote: Token -> SOL
        quote = await self.get_quote(
            input_mint=contract_address,
            output_mint=SOL_MINT,
            amount=token_amount,
        )

        sol_out = int(quote.get("outAmount", 0))
        sol_price = await self.get_sol_price_usd()
        usd_received = (sol_out / 1e9) * sol_price

        # Execute swap
        tx_sig = await self.execute_swap(quote)

        return {
            "tx_signature": tx_sig,
            "sol_received_lamports": sol_out,
            "sol_price_usd": sol_price,
            "usd_received": usd_received,
            "token_amount_sold": token_amount,
            "quote": quote,
        }
