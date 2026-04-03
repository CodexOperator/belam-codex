"""Solana wallet generation and management."""

import json
import logging
from pathlib import Path
from typing import Optional

import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

from src.utils import lamports_to_sol, SOL_MINT

logger = logging.getLogger("sniper.wallet")


class WalletManager:
    """Manage Solana keypair and balances."""

    def __init__(self, config: dict):
        self.config = config
        self.wallet_path = Path(config.get("wallet", {}).get("path", "wallet/keypair.json"))
        self.rpc_url = config.get("solana", {}).get("rpc_url", "https://api.mainnet-beta.solana.com")
        self.keypair: Optional[Keypair] = None
        self.public_key: Optional[str] = None

    def generate_keypair(self) -> str:
        """Generate a new Solana keypair and save to file.
        
        Returns the public key as string.
        """
        self.keypair = Keypair()
        self.public_key = str(self.keypair.pubkey())

        # Save keypair bytes
        self.wallet_path.parent.mkdir(parents=True, exist_ok=True)

        keypair_data = {
            "public_key": self.public_key,
            "secret_key": base58.b58encode(bytes(self.keypair)).decode("utf-8"),
        }

        with open(self.wallet_path, "w") as f:
            json.dump(keypair_data, f, indent=2)

        logger.info(f"Generated new wallet: {self.public_key}")
        return self.public_key

    def load_keypair(self) -> Keypair:
        """Load keypair from saved file."""
        if not self.wallet_path.exists():
            raise FileNotFoundError(
                f"No wallet found at {self.wallet_path}. Run setup.sh first."
            )

        with open(self.wallet_path) as f:
            data = json.load(f)

        secret_bytes = base58.b58decode(data["secret_key"])
        self.keypair = Keypair.from_bytes(secret_bytes)
        self.public_key = str(self.keypair.pubkey())

        logger.info(f"Loaded wallet: {self.public_key}")
        return self.keypair

    def ensure_loaded(self) -> Keypair:
        """Ensure keypair is loaded, load from file if needed."""
        if self.keypair is None:
            self.load_keypair()
        return self.keypair

    async def get_sol_balance(self) -> float:
        """Get SOL balance in SOL (not lamports)."""
        self.ensure_loaded()
        async with AsyncClient(self.rpc_url) as client:
            resp = await client.get_balance(
                Pubkey.from_string(self.public_key),
                commitment=Confirmed,
            )
            lamports = resp.value
            return lamports_to_sol(lamports)

    async def get_token_balance(self, mint: str) -> float:
        """Get SPL token balance for a given mint."""
        self.ensure_loaded()
        async with AsyncClient(self.rpc_url) as client:
            resp = await client.get_token_accounts_by_owner_json_parsed(
                Pubkey.from_string(self.public_key),
                opts={"mint": Pubkey.from_string(mint)},
                commitment=Confirmed,
            )

            if not resp.value:
                return 0.0

            # Parse token account data
            for account in resp.value:
                parsed = account.account.data.parsed
                info = parsed["info"]
                amount = info["tokenAmount"]
                return float(amount["uiAmount"] or 0)

            return 0.0

    async def get_balance_summary(self) -> dict:
        """Get full balance summary."""
        sol = await self.get_sol_balance()
        return {
            "public_key": self.public_key,
            "sol_balance": sol,
        }
