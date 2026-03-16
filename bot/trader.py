"""
Hyperliquid order execution wrapper.

Uses the official hyperliquid-python-sdk.  All order placements use IOC
(Immediate-Or-Cancel) limit orders priced with a small slippage so they
behave like market orders while giving price protection.
"""

import logging
import math
from typing import Dict, Optional, Tuple

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

logger = logging.getLogger(__name__)

SLIPPAGE = 0.002  # 0.2% slippage tolerance for IOC "market" orders


class HyperliquidTrader:
    def __init__(self, private_key: str, testnet: bool = False):
        api_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self._account = Account.from_key(private_key)
        self._info = Info(api_url, skip_ws=True)
        self._exchange = Exchange(self._account, api_url)
        self._address = self._account.address
        logger.info("HyperliquidTrader initialised. Address: %s", self._address)

    # ------------------------------------------------------------------
    # Account queries
    # ------------------------------------------------------------------

    def account_value(self) -> float:
        """Return total account equity in USD."""
        state = self._info.user_state(self._address)
        return float(state.get("marginSummary", {}).get("accountValue", 0))

    def open_positions(self) -> Dict[str, Dict]:
        """Return map of coin → position dict for open positions."""
        state = self._info.user_state(self._address)
        positions = {}
        for pos in state.get("assetPositions", []):
            p = pos.get("position", {})
            szi = float(p.get("szi", 0))
            if szi != 0:
                coin = p["coin"]
                positions[coin] = {
                    "coin": coin,
                    "size": szi,
                    "side": "Long" if szi > 0 else "Short",
                    "entry_price": float(p.get("entryPx", 0)),
                    "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
                    "leverage": float(p.get("leverage", {}).get("value", 1)),
                }
        return positions

    def mid_price(self, coin: str) -> float:
        """Fetch current mid price for a coin."""
        mids = self._info.all_mids()
        raw = mids.get(coin)
        if raw is None:
            raise ValueError(f"No mid price for {coin}")
        return float(raw)

    def coin_decimals(self, coin: str) -> int:
        """Return the number of decimal places for the coin's size."""
        meta = self._info.meta()
        for asset in meta.get("universe", []):
            if asset["name"] == coin:
                return int(asset.get("szDecimals", 4))
        return 4

    # ------------------------------------------------------------------
    # Order helpers
    # ------------------------------------------------------------------

    def _round_size(self, size: float, coin: str) -> float:
        dec = self.coin_decimals(coin)
        factor = 10 ** dec
        return math.floor(size * factor) / factor

    def set_leverage(self, coin: str, leverage: int, cross_margin: bool = True):
        """Set leverage for a coin.  Silently ignores errors if unchanged."""
        try:
            self._exchange.update_leverage(leverage, coin, cross_margin)
            logger.debug("Leverage for %s set to %dx (%s)", coin, leverage, "cross" if cross_margin else "isolated")
        except Exception as exc:
            logger.warning("Could not set leverage for %s: %s", coin, exc)

    def open_position(
        self,
        coin: str,
        side: str,          # "Long" or "Short"
        usd_size: float,
        leverage: int = 1,
    ) -> Optional[Dict]:
        """
        Open a position worth `usd_size` USD on `coin`.

        Returns the exchange response dict, or None on failure.
        """
        self.set_leverage(coin, leverage)

        mid = self.mid_price(coin)
        is_buy = side == "Long"
        px = mid * (1 + SLIPPAGE) if is_buy else mid * (1 - SLIPPAGE)
        px = round(px, 6)

        coin_size = self._round_size((usd_size * leverage) / mid, coin)
        if coin_size <= 0:
            logger.warning("Computed size is 0 for %s %s (usd=%.2f)", side, coin, usd_size)
            return None

        logger.info(
            "OPEN %s %s  size=%.5f  px=%.4f  usd=%.2f  lev=%dx",
            side, coin, coin_size, px, usd_size, leverage,
        )
        try:
            result = self._exchange.order(
                coin, is_buy, coin_size, px,
                {"limit": {"tif": "Ioc"}},
                reduce_only=False,
            )
            logger.info("Order result: %s", result)
            return result
        except Exception as exc:
            logger.error("Failed to open %s %s: %s", side, coin, exc)
            return None

    def close_position(self, coin: str, side: str) -> Optional[Dict]:
        """
        Close an existing position on `coin`.
        `side` is the direction of the position to close ("Long" or "Short").
        """
        positions = self.open_positions()
        pos = positions.get(coin)
        if pos is None:
            logger.debug("No open position to close for %s", coin)
            return None

        size = abs(pos["size"])
        is_buy = side == "Short"  # close short → buy; close long → sell
        mid = self.mid_price(coin)
        px = mid * (1 + SLIPPAGE) if is_buy else mid * (1 - SLIPPAGE)
        px = round(px, 6)

        logger.info("CLOSE %s %s  size=%.5f  px=%.4f", side, coin, size, px)
        try:
            result = self._exchange.order(
                coin, is_buy, size, px,
                {"limit": {"tif": "Ioc"}},
                reduce_only=True,
            )
            logger.info("Close result: %s", result)
            return result
        except Exception as exc:
            logger.error("Failed to close %s %s: %s", side, coin, exc)
            return None
