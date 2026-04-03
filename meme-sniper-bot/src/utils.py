"""Shared utilities for the meme sniper bot."""

import logging
import re
import sys
from pathlib import Path
from typing import Optional

import yaml


def load_config(path: str = "config.yaml") -> dict:
    """Load and validate configuration from YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Validate required fields
    required = [
        ("telegram.api_id", config.get("telegram", {}).get("api_id")),
        ("telegram.api_hash", config.get("telegram", {}).get("api_hash")),
        ("telegram.phone", config.get("telegram", {}).get("phone")),
    ]

    missing = [name for name, val in required if not val]
    if missing:
        raise ValueError(f"Missing required config fields: {', '.join(missing)}")

    return config


def setup_logging(config: dict) -> logging.Logger:
    """Configure logging to stdout + file."""
    log_cfg = config.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    log_file = log_cfg.get("file", "sniper.log")

    fmt = logging.Formatter(
        "%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger("sniper")
    root.setLevel(level)

    # Stdout handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    return root


# Solana base58 contract address pattern (32-44 chars, base58 alphabet)
SOLANA_CA_PATTERN = re.compile(r"\b([123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{32,44})\b")

# DexScreener URL pattern
DEXSCREENER_PATTERN = re.compile(r"https?://dexscreener\.com/solana/([a-zA-Z0-9]+)")

# Birdeye URL pattern
BIRDEYE_PATTERN = re.compile(r"https?://birdeye\.so/token/([a-zA-Z0-9]+)")

# Token name with $ prefix
TOKEN_NAME_PATTERN = re.compile(r"\$([A-Za-z][A-Za-z0-9_]{0,20})")

# SOL mint address
SOL_MINT = "So11111111111111111111111111111111111111112"

# Known non-CA base58 strings to filter out (common Solana program IDs, etc.)
KNOWN_PROGRAM_IDS = {
    SOL_MINT,
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    "11111111111111111111111111111111",
}


def extract_solana_ca(text: str) -> Optional[str]:
    """Extract a Solana contract address from text.
    
    Checks DexScreener/Birdeye URLs first, then raw base58 strings.
    Filters out known program IDs.
    """
    # Try DexScreener URL first
    match = DEXSCREENER_PATTERN.search(text)
    if match:
        ca = match.group(1)
        if len(ca) >= 32 and ca not in KNOWN_PROGRAM_IDS:
            return ca

    # Try Birdeye URL
    match = BIRDEYE_PATTERN.search(text)
    if match:
        ca = match.group(1)
        if len(ca) >= 32 and ca not in KNOWN_PROGRAM_IDS:
            return ca

    # Try raw base58 addresses
    candidates = SOLANA_CA_PATTERN.findall(text)
    for ca in candidates:
        if ca not in KNOWN_PROGRAM_IDS:
            return ca

    return None


def extract_token_name(text: str) -> Optional[str]:
    """Extract $TOKEN name from text."""
    match = TOKEN_NAME_PATTERN.search(text)
    return match.group(1) if match else None


def extract_dex_url(text: str) -> Optional[str]:
    """Extract DexScreener or Birdeye URL from text."""
    match = DEXSCREENER_PATTERN.search(text)
    if match:
        return match.group(0)
    match = BIRDEYE_PATTERN.search(text)
    if match:
        return match.group(0)
    return None


def lamports_to_sol(lamports: int) -> float:
    """Convert lamports to SOL."""
    return lamports / 1_000_000_000


def sol_to_lamports(sol: float) -> int:
    """Convert SOL to lamports."""
    return int(sol * 1_000_000_000)


def format_usd(amount: float) -> str:
    """Format a USD amount."""
    return f"${amount:,.2f}"


def format_pct(pct: float) -> str:
    """Format a percentage."""
    return f"{pct:+.1f}%"
