"""
Trader discovery module.

Queries the Nansen PnL leaderboard across multiple symbols and ranks wallets
by a composite score, returning the top N candidates to follow.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List

from .nansen import NansenClient

logger = logging.getLogger(__name__)


@dataclass
class TrackedTrader:
    address: str
    label: str
    total_pnl_usd: float
    avg_win_rate: float
    total_trades: int
    roi_pct: float
    symbols_active: List[str] = field(default_factory=list)
    # Running PnL since we started tracking (for drawdown detection)
    baseline_pnl_usd: float = 0.0
    score: float = 0.0


def _composite_score(pnl: float, win_rate: float, roi_pct: float, trades: int) -> float:
    """
    Composite ranking score:
      - Rewards absolute PnL (log-scaled)
      - Rewards high win rate
      - Rewards ROI%
      - Light penalty for low trade count (less statistical confidence)
    """
    import math
    pnl_score = math.log1p(max(pnl, 0)) * 0.4
    wr_score = win_rate * 100 * 0.3
    roi_score = min(roi_pct, 500) * 0.2          # cap to avoid outliers dominating
    confidence = min(trades / 30, 1.0) * 0.1     # max confidence at 30+ trades
    return pnl_score + wr_score + roi_score + confidence


def discover_top_traders(
    nansen: NansenClient,
    symbols: List[str],
    days: int,
    min_win_rate: float,
    min_trades: int,
    min_pnl_usd: float,
    max_traders: int,
) -> List[TrackedTrader]:
    """
    Fetch the Nansen perp PnL leaderboard for each symbol and return
    the top `max_traders` qualifying wallets ranked by composite score.
    """
    candidates: Dict[str, TrackedTrader] = {}

    for symbol in symbols:
        logger.info("Fetching leaderboard for %s (last %d days) …", symbol, days)
        try:
            rows = nansen.perp_pnl_leaderboard(symbol=symbol, days=days, limit=50)
        except Exception as exc:
            logger.warning("Leaderboard fetch failed for %s: %s", symbol, exc)
            continue

        for row in rows:
            addr = row.get("trader_address", "")
            if not addr:
                continue

            pnl = float(row.get("pnl_usd", 0))
            win_rate = float(row.get("win_rate", 0))
            trades = int(row.get("trade_count", 0))
            roi_pct = float(row.get("roi_percent", 0))

            # Apply quality filters
            if win_rate < min_win_rate:
                continue
            if trades < min_trades:
                continue
            if pnl < min_pnl_usd:
                continue

            score = _composite_score(pnl, win_rate, roi_pct, trades)

            if addr in candidates:
                existing = candidates[addr]
                existing.total_pnl_usd += pnl
                existing.total_trades += trades
                # Update win rate as weighted average
                total = existing.total_trades + trades
                existing.avg_win_rate = (
                    (existing.avg_win_rate * existing.total_trades + win_rate * trades)
                    / total if total else win_rate
                )
                existing.score = max(existing.score, score)
                if symbol not in existing.symbols_active:
                    existing.symbols_active.append(symbol)
            else:
                candidates[addr] = TrackedTrader(
                    address=addr,
                    label=row.get("trader_label", ""),
                    total_pnl_usd=pnl,
                    avg_win_rate=win_rate,
                    total_trades=trades,
                    roi_pct=roi_pct,
                    symbols_active=[symbol],
                    score=score,
                )

    ranked = sorted(candidates.values(), key=lambda t: t.score, reverse=True)
    top = ranked[:max_traders]

    logger.info(
        "Discovery complete. %d candidates → top %d selected.",
        len(candidates), len(top),
    )
    for i, t in enumerate(top, 1):
        logger.info(
            "  #%d  %s (%s)  pnl=$%.0f  wr=%.0f%%  trades=%d  score=%.2f  symbols=%s",
            i, t.address[:10] + "…", t.label or "unlabeled",
            t.total_pnl_usd, t.avg_win_rate * 100,
            t.total_trades, t.score, t.symbols_active,
        )

    return top
