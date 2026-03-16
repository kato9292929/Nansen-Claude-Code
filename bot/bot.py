"""
Copy-trading bot core.

Lifecycle
─────────
1. Discovery (every `rediscover_interval` seconds)
   • Query Nansen leaderboard for top traders
   • Update the tracked-wallet set

2. Monitor loop (every `poll_interval` seconds)
   • Poll smart-money.perp-trades for new trades
   • For each new trade whose address is in our tracked set, copy it

3. Copy execution
   • Calculate proportional USD size
   • Enforce min/max and total-exposure caps
   • Place IOC order via Hyperliquid SDK

4. Risk checks (every poll)
   • Check per-trader drawdown; drop if threshold exceeded
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from .discovery import TrackedTrader, discover_top_traders
from .nansen import NansenClient, NansenError
from .trader import HyperliquidTrader

logger = logging.getLogger(__name__)

STATE_FILE = Path("state.json")

# Actions we recognise from the Nansen perp-trades feed
OPEN_ACTIONS = {"open", "open long", "open short", "increase", "increase long", "increase short"}
CLOSE_ACTIONS = {"close", "close long", "close short", "decrease", "partial close"}


class CopyTradeBot:
    def __init__(self, cfg: Dict):
        nc_cfg = cfg["nansen"]
        self._nansen = NansenClient(
            api_key=nc_cfg["api_key"],
            endpoint=nc_cfg.get("endpoint", "https://mcp.nansen.ai/ra/mcp/"),
        )

        hl_cfg = cfg["hyperliquid"]
        pk = hl_cfg.get("private_key", "")
        if pk.startswith("${"):
            pk = os.environ.get(pk[2:-1], "")
        if not pk:
            raise ValueError(
                "Hyperliquid private key not set. "
                "Provide it in config.yaml or via HL_PRIVATE_KEY env var."
            )
        self._hl = HyperliquidTrader(
            private_key=pk,
            testnet=hl_cfg.get("testnet", False),
        )

        ct = cfg["copy_trading"]
        self._allocation_ratio: float = ct["allocation_ratio"]
        self._max_traders: int = ct["max_traders"]
        self._max_leverage: int = ct["max_leverage"]
        self._min_trade_usd: float = ct["min_trade_usd"]
        self._max_trade_usd: float = ct["max_trade_usd"]
        self._poll_interval: int = ct["poll_interval"]

        disc = cfg["discovery"]
        self._symbols: List[str] = disc["symbols"]
        self._disc_days: int = disc["days"]
        self._min_win_rate: float = disc["min_win_rate"]
        self._min_trades: int = disc["min_trades"]
        self._min_pnl_usd: float = disc["min_pnl_usd"]
        self._rediscover_interval: int = disc["rediscover_interval"]
        self._sm_labels: List[str] = disc.get("smart_money_labels", [])

        risk = cfg["risk"]
        self._max_total_pos_usd: float = risk["max_total_position_usd"]
        self._max_drawdown_pct: float = risk["max_trader_drawdown_pct"]

        # Runtime state
        self._tracked: Dict[str, TrackedTrader] = {}   # address → trader
        self._seen_hashes: Set[str] = set()            # de-dupe trade hashes
        self._last_discovery: float = 0.0

        self._load_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                self._seen_hashes = set(data.get("seen_hashes", []))
                logger.info("Loaded %d seen trade hashes from state file.", len(self._seen_hashes))
            except Exception as exc:
                logger.warning("Could not load state file: %s", exc)

    def _save_state(self):
        try:
            data = {"seen_hashes": list(self._seen_hashes)}
            STATE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.warning("Could not save state file: %s", exc)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _run_discovery(self):
        logger.info("=== Running trader discovery ===")
        traders = discover_top_traders(
            nansen=self._nansen,
            symbols=self._symbols,
            days=self._disc_days,
            min_win_rate=self._min_win_rate,
            min_trades=self._min_trades,
            min_pnl_usd=self._min_pnl_usd,
            max_traders=self._max_traders,
        )

        # Preserve baseline PnL for drawdown tracking
        new_tracked: Dict[str, TrackedTrader] = {}
        for t in traders:
            if t.address in self._tracked:
                t.baseline_pnl_usd = self._tracked[t.address].baseline_pnl_usd
            else:
                t.baseline_pnl_usd = t.total_pnl_usd
            new_tracked[t.address] = t

        dropped = set(self._tracked) - set(new_tracked)
        added = set(new_tracked) - set(self._tracked)
        if dropped:
            logger.info("Dropped traders: %s", [a[:10] for a in dropped])
        if added:
            logger.info("Added traders: %s", [a[:10] for a in added])

        self._tracked = new_tracked
        self._last_discovery = time.time()

    # ------------------------------------------------------------------
    # Risk helpers
    # ------------------------------------------------------------------

    def _total_open_exposure(self) -> float:
        positions = self._hl.open_positions()
        return sum(abs(p["size"]) * self._hl.mid_price(p["coin"]) for p in positions.values())

    def _per_trader_usd_budget(self) -> float:
        """USD we are willing to risk per trader per trade."""
        account_val = self._hl.account_value()
        total_budget = account_val * self._allocation_ratio
        n = max(len(self._tracked), 1)
        return total_budget / n

    def _check_drawdown(self, trader: TrackedTrader) -> bool:
        """Return True if trader is within acceptable drawdown."""
        if trader.baseline_pnl_usd <= 0:
            return True
        loss_pct = (
            (trader.baseline_pnl_usd - trader.total_pnl_usd)
            / trader.baseline_pnl_usd
            * 100
        )
        if loss_pct >= self._max_drawdown_pct:
            logger.warning(
                "Trader %s exceeds drawdown threshold (%.1f%% loss). Dropping.",
                trader.address[:10], loss_pct,
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Trade processing
    # ------------------------------------------------------------------

    def _process_trade(self, trade: Dict):
        addr = trade.get("trader_address", "")
        tx_hash = trade.get("transaction_hash", "")
        symbol = trade.get("token_symbol", "")
        side = trade.get("side", "")           # "Long" or "Short"
        action_raw = (trade.get("action") or "").lower()
        value_usd = float(trade.get("value_usd") or 0)

        if not all([addr, symbol, side]):
            return
        if tx_hash in self._seen_hashes:
            return
        self._seen_hashes.add(tx_hash)

        trader = self._tracked.get(addr)
        if trader is None:
            return

        logger.info(
            "Trade detected — %s %s %s  $%.0f  [%s…]",
            action_raw.upper(), side, symbol, value_usd, addr[:10],
        )

        is_close = any(kw in action_raw for kw in CLOSE_ACTIONS)
        is_open = not is_close or any(kw in action_raw for kw in OPEN_ACTIONS)

        if is_close and not is_open:
            self._copy_close(symbol, side)
            return

        # --- Copy open / increase ---
        if not self._check_drawdown(trader):
            del self._tracked[addr]
            return

        # Check total exposure cap
        current_exposure = self._total_open_exposure()
        if current_exposure >= self._max_total_pos_usd:
            logger.warning(
                "Total exposure $%.0f ≥ cap $%.0f. Skipping trade.",
                current_exposure, self._max_total_pos_usd,
            )
            return

        # Size calculation: proportional to what the trader risks
        budget = self._per_trader_usd_budget()
        # Scale by value_usd (trader's absolute trade size) — but cap it
        usd_size = min(budget, self._max_trade_usd)
        usd_size = max(usd_size, 0)

        if usd_size < self._min_trade_usd:
            logger.info(
                "Computed size $%.2f < min $%.2f. Skipping.", usd_size, self._min_trade_usd
            )
            return

        # Respect remaining exposure headroom
        remaining = self._max_total_pos_usd - current_exposure
        usd_size = min(usd_size, remaining)

        # Leverage: use the trader's leverage info if available, capped
        leverage = min(int(trade.get("leverage", 1) or 1), self._max_leverage)
        leverage = max(leverage, 1)

        self._hl.open_position(
            coin=symbol,
            side=side,
            usd_size=usd_size,
            leverage=leverage,
        )

    def _copy_close(self, symbol: str, side: str):
        positions = self._hl.open_positions()
        if symbol in positions:
            self._hl.close_position(symbol, side)
        else:
            logger.debug("No open copy position to close for %s %s", side, symbol)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        logger.info("=== Nansen Copy-Trade Bot starting ===")

        while True:
            # Discovery phase
            if time.time() - self._last_discovery >= self._rediscover_interval:
                try:
                    self._run_discovery()
                except Exception as exc:
                    logger.error("Discovery failed: %s", exc)

            if not self._tracked:
                logger.info("No tracked traders yet. Retrying in 60s …")
                time.sleep(60)
                continue

            watched_addrs = set(self._tracked.keys())
            logger.info(
                "Polling smart-money.perp-trades  (watching %d traders) …",
                len(watched_addrs),
            )

            try:
                trades = self._nansen.smart_money_perp_trades(
                    limit=200,
                    labels=self._sm_labels if self._sm_labels else None,
                )
            except NansenError as exc:
                logger.error("Nansen poll error: %s", exc)
                time.sleep(self._poll_interval)
                continue
            except Exception as exc:
                logger.error("Unexpected poll error: %s", exc)
                time.sleep(self._poll_interval)
                continue

            new_count = 0
            for trade in trades:
                addr = trade.get("trader_address", "")
                tx_hash = trade.get("transaction_hash", "")
                if addr in watched_addrs and tx_hash not in self._seen_hashes:
                    new_count += 1
                    try:
                        self._process_trade(trade)
                    except Exception as exc:
                        logger.error("Error processing trade %s: %s", tx_hash, exc)

            if new_count:
                logger.info("Processed %d new trades.", new_count)
                self._save_state()

            time.sleep(self._poll_interval)
