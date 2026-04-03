"""SQLite position tracking and TP ladder management."""

import csv
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sniper.positions")

DB_PATH = Path("db/sniper.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY,
    token_name TEXT,
    contract_address TEXT UNIQUE,
    chain TEXT DEFAULT 'solana',
    entry_price_usd REAL,
    entry_amount_usd REAL,
    token_quantity REAL,
    entry_time TIMESTAMP,
    current_tier INTEGER DEFAULT 0,
    total_invested_usd REAL,
    total_withdrawn_usd REAL DEFAULT 0,
    remaining_quantity REAL,
    status TEXT DEFAULT 'active',
    dex_url TEXT,
    source_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id),
    trade_type TEXT,
    amount_usd REAL,
    token_quantity REAL,
    price_usd REAL,
    tier_triggered INTEGER,
    tx_signature TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY,
    total_capital REAL DEFAULT 30.0,
    available_capital REAL DEFAULT 30.0,
    total_deployed REAL DEFAULT 0,
    total_realized_pnl REAL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class PositionManager:
    """Manage positions, trades, and portfolio in SQLite."""

    def __init__(self, config: dict):
        self.config = config
        self.tp_ladder = config.get("tp_ladder", [])
        self.db_path = DB_PATH

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Initialize database schema and portfolio row."""
        conn = self._get_conn()
        try:
            conn.executescript(SCHEMA)
            # Ensure portfolio row exists
            row = conn.execute("SELECT COUNT(*) as c FROM portfolio").fetchone()
            if row["c"] == 0:
                capital = self.config.get("trading", {}).get("starting_capital", 30.0)
                conn.execute(
                    "INSERT INTO portfolio (total_capital, available_capital) VALUES (?, ?)",
                    (capital, capital),
                )
            conn.commit()
        finally:
            conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def open_position(
        self,
        token_name: str,
        ca: str,
        entry_price: float,
        quantity: float,
        amount_usd: float,
        dex_url: Optional[str] = None,
        source_msg: Optional[str] = None,
        tx_signature: Optional[str] = None,
    ) -> int:
        """Open a new position. Returns position ID."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO positions 
                   (token_name, contract_address, entry_price_usd, entry_amount_usd,
                    token_quantity, entry_time, total_invested_usd, remaining_quantity,
                    dex_url, source_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (token_name, ca, entry_price, amount_usd, quantity, now,
                 amount_usd, quantity, dex_url, source_msg),
            )
            position_id = cursor.lastrowid

            # Record trade
            conn.execute(
                """INSERT INTO trades 
                   (position_id, trade_type, amount_usd, token_quantity, price_usd,
                    tier_triggered, tx_signature)
                   VALUES (?, 'buy', ?, ?, ?, 0, ?)""",
                (position_id, amount_usd, quantity, entry_price, tx_signature),
            )

            # Update portfolio
            conn.execute(
                """UPDATE portfolio SET 
                   available_capital = available_capital - ?,
                   total_deployed = total_deployed + ?,
                   updated_at = ?""",
                (amount_usd, amount_usd, now),
            )

            conn.commit()
            logger.info(
                f"Opened position #{position_id}: {token_name} ({ca[:8]}...) "
                f"${amount_usd:.2f} @ ${entry_price:.8f}"
            )
            return position_id
        finally:
            conn.close()

    def get_position(self, ca: str) -> Optional[dict]:
        """Get position by contract address."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM positions WHERE contract_address = ?", (ca,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_active_positions(self) -> list[dict]:
        """Get all active positions."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status IN ('active', 'moonbag')"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def check_tp_ladder(self, ca: str, current_price: float) -> list[dict]:
        """Check which TP tiers are triggered for a position.
        
        Returns list of triggered tiers with sell details.
        """
        pos = self.get_position(ca)
        if not pos or pos["status"] == "closed":
            return []

        entry_price = pos["entry_price_usd"]
        current_tier = pos["current_tier"]
        remaining = pos["remaining_quantity"]
        triggered = []

        for i, tier in enumerate(self.tp_ladder):
            tier_idx = i + 1  # tiers are 1-indexed
            if tier_idx <= current_tier:
                continue  # Already triggered

            target_price = entry_price * tier["multiplier"]
            if current_price >= target_price:
                sell_qty = remaining * tier["sell_pct"]
                if sell_qty > 0:
                    triggered.append({
                        "tier": tier_idx,
                        "multiplier": tier["multiplier"],
                        "sell_pct": tier["sell_pct"],
                        "sell_quantity": sell_qty,
                        "target_price": target_price,
                        "current_price": current_price,
                    })
                    remaining -= sell_qty

        return triggered

    def execute_tp(
        self,
        ca: str,
        tier: int,
        sell_quantity: float,
        realized_usd: float,
        price_usd: float,
        tx_signature: Optional[str] = None,
    ):
        """Record a take-profit execution."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            pos = dict(conn.execute(
                "SELECT * FROM positions WHERE contract_address = ?", (ca,)
            ).fetchone())

            new_remaining = pos["remaining_quantity"] - sell_quantity
            new_withdrawn = pos["total_withdrawn_usd"] + realized_usd
            new_status = pos["status"]

            # If very little remaining, mark as moonbag or closed
            if new_remaining <= 0:
                new_status = "closed"
            elif tier >= len(self.tp_ladder):
                new_status = "moonbag"

            conn.execute(
                """UPDATE positions SET 
                   current_tier = ?, remaining_quantity = ?, 
                   total_withdrawn_usd = ?, status = ?
                   WHERE contract_address = ?""",
                (tier, new_remaining, new_withdrawn, new_status, ca),
            )

            conn.execute(
                """INSERT INTO trades 
                   (position_id, trade_type, amount_usd, token_quantity, price_usd,
                    tier_triggered, tx_signature)
                   VALUES (?, 'tp_sell', ?, ?, ?, ?, ?)""",
                (pos["id"], realized_usd, sell_quantity, price_usd, tier, tx_signature),
            )

            # Update portfolio
            conn.execute(
                """UPDATE portfolio SET 
                   available_capital = available_capital + ?,
                   total_realized_pnl = total_realized_pnl + ?,
                   updated_at = ?""",
                (realized_usd, realized_usd, now),
            )

            conn.commit()
            logger.info(
                f"TP tier {tier} ({self.tp_ladder[tier-1]['multiplier']}x) on "
                f"{pos['token_name']}: sold {sell_quantity:.4f} for ${realized_usd:.2f}"
            )
        finally:
            conn.close()

    def add_to_position(
        self,
        ca: str,
        additional_amount: float,
        quantity: float,
        price: float,
        tx_signature: Optional[str] = None,
    ):
        """Add to an existing position (dip buy)."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            pos = dict(conn.execute(
                "SELECT * FROM positions WHERE contract_address = ?", (ca,)
            ).fetchone())

            new_invested = pos["total_invested_usd"] + additional_amount
            new_quantity = pos["token_quantity"] + quantity
            new_remaining = pos["remaining_quantity"] + quantity
            # Weighted average entry price
            new_entry = new_invested / new_quantity if new_quantity > 0 else price

            conn.execute(
                """UPDATE positions SET 
                   total_invested_usd = ?, token_quantity = ?,
                   remaining_quantity = ?, entry_price_usd = ?,
                   entry_amount_usd = entry_amount_usd + ?
                   WHERE contract_address = ?""",
                (new_invested, new_quantity, new_remaining, new_entry,
                 additional_amount, ca),
            )

            conn.execute(
                """INSERT INTO trades 
                   (position_id, trade_type, amount_usd, token_quantity, price_usd,
                    tier_triggered, tx_signature)
                   VALUES (?, 'buy', ?, ?, ?, -1, ?)""",
                (pos["id"], additional_amount, quantity, price, tx_signature),
            )

            conn.execute(
                """UPDATE portfolio SET 
                   available_capital = available_capital - ?,
                   total_deployed = total_deployed + ?,
                   updated_at = ?""",
                (additional_amount, additional_amount, now),
            )

            conn.commit()
            logger.info(
                f"Added ${additional_amount:.2f} to {pos['token_name']} "
                f"({quantity:.4f} tokens @ ${price:.8f})"
            )
        finally:
            conn.close()

    def get_portfolio_summary(self) -> dict:
        """Get portfolio summary with all positions."""
        conn = self._get_conn()
        try:
            portfolio = dict(conn.execute("SELECT * FROM portfolio ORDER BY id DESC LIMIT 1").fetchone())
            active = conn.execute(
                "SELECT COUNT(*) as c FROM positions WHERE status = 'active'"
            ).fetchone()["c"]
            moonbag = conn.execute(
                "SELECT COUNT(*) as c FROM positions WHERE status = 'moonbag'"
            ).fetchone()["c"]
            closed = conn.execute(
                "SELECT COUNT(*) as c FROM positions WHERE status = 'closed'"
            ).fetchone()["c"]

            return {
                **portfolio,
                "active_positions": active,
                "moonbag_positions": moonbag,
                "closed_positions": closed,
            }
        finally:
            conn.close()

    def export_csv(self, filepath: str = "positions_export.csv"):
        """Export all positions and trades to CSV."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT p.*, 
                   (SELECT COUNT(*) FROM trades t WHERE t.position_id = p.id) as trade_count
                   FROM positions p ORDER BY p.created_at DESC"""
            ).fetchall()

            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                if rows:
                    writer.writerow(rows[0].keys())
                    for row in rows:
                        writer.writerow(tuple(row))

            logger.info(f"Exported {len(rows)} positions to {filepath}")
        finally:
            conn.close()

    def position_exists(self, ca: str) -> bool:
        """Check if a position exists for this CA (any status)."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM positions WHERE contract_address = ?", (ca,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def has_active_position(self, ca: str) -> bool:
        """Check if there's an active position for this CA."""
        pos = self.get_position(ca)
        return pos is not None and pos["status"] in ("active", "moonbag")


# CLI interface for checking positions
if __name__ == "__main__":
    import sys
    import yaml

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    pm = PositionManager(cfg)

    if len(sys.argv) < 2:
        print("Usage: python -m src.position_manager [summary|export|positions]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "summary":
        summary = pm.get_portfolio_summary()
        print("\n=== Portfolio Summary ===")
        print(f"  Total Capital:    ${summary['total_capital']:.2f}")
        print(f"  Available:        ${summary['available_capital']:.2f}")
        print(f"  Deployed:         ${summary['total_deployed']:.2f}")
        print(f"  Realized PnL:     ${summary['total_realized_pnl']:.2f}")
        print(f"  Active Positions: {summary['active_positions']}")
        print(f"  Moonbags:         {summary['moonbag_positions']}")
        print(f"  Closed:           {summary['closed_positions']}")
        print()

    elif cmd == "export":
        filepath = sys.argv[2] if len(sys.argv) > 2 else "positions_export.csv"
        pm.export_csv(filepath)
        print(f"Exported to {filepath}")

    elif cmd == "positions":
        positions = pm.get_active_positions()
        if not positions:
            print("No active positions.")
        else:
            print(f"\n=== Active Positions ({len(positions)}) ===")
            for p in positions:
                print(f"  {p['token_name']:12s} | {p['contract_address'][:12]}... | "
                      f"${p['entry_amount_usd']:.2f} | tier {p['current_tier']} | "
                      f"{p['status']}")
            print()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
