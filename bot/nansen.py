"""
Nansen MCP HTTP client.

Communicates with the Nansen MCP server over Streamable HTTP transport
(JSON-RPC 2.0).  Handles both plain JSON and SSE responses transparently.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class NansenError(Exception):
    pass


class NansenClient:
    def __init__(self, api_key: str, endpoint: str = "https://mcp.nansen.ai/ra/mcp/"):
        self.endpoint = endpoint.rstrip("/") + "/"
        self._headers = {
            "NANSEN-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self._req_id = 0

    # ------------------------------------------------------------------
    # Low-level transport
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": self._next_id(),
        }
        logger.debug("Calling tool %s with args %s", tool_name, arguments)

        resp = requests.post(
            self.endpoint,
            headers=self._headers,
            json=payload,
            stream=True,
            timeout=60,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse(resp)
        return self._parse_json(resp)

    def _parse_json(self, resp: requests.Response) -> Any:
        data = resp.json()
        return self._unwrap(data)

    def _parse_sse(self, resp: requests.Response) -> Any:
        """Parse server-sent events and return the first completed result."""
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                break
            try:
                data = json.loads(payload)
                result = self._unwrap(data)
                if result is not None:
                    return result
            except json.JSONDecodeError:
                continue
        return None

    def _unwrap(self, data: Dict) -> Any:
        if "error" in data:
            raise NansenError(f"MCP error: {data['error']}")
        result = data.get("result", {})
        # MCP tool results wrap text in a content array
        if isinstance(result, dict) and "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    text = item["text"]
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
        return result

    # ------------------------------------------------------------------
    # Typed helpers
    # ------------------------------------------------------------------

    def perp_pnl_leaderboard(
        self,
        symbol: str,
        days: int = 7,
        limit: int = 20,
    ) -> List[Dict]:
        """Top Hyperliquid perp traders by PnL for a given symbol."""
        result = self._call(
            "token.perp-pnl-leaderboard",
            {"symbol": symbol, "days": days, "limit": limit},
        )
        return result if isinstance(result, list) else []

    def smart_money_perp_trades(
        self,
        limit: int = 100,
        labels: Optional[List[str]] = None,
        side: Optional[str] = None,
    ) -> List[Dict]:
        """
        Recent perpetual trades from smart-money wallets on Hyperliquid.

        Returns list of trade dicts with keys:
          trader_address, trader_address_label, token_symbol,
          side, action, token_amount, price_usd, value_usd,
          type, block_timestamp, transaction_hash
        """
        filters: Dict[str, Any] = {}
        if labels:
            filters["include_smart_money_labels"] = labels
        if side:
            filters["side"] = side  # "Long" or "Short"

        args: Dict[str, Any] = {"limit": limit}
        if filters:
            args["filters"] = filters

        result = self._call("smart-money.perp-trades", args)
        return result if isinstance(result, list) else []

    def wallet_perp_trades(
        self,
        address: str,
        days: int = 1,
        limit: int = 50,
    ) -> List[Dict]:
        """Historical perp trades for a specific wallet."""
        result = self._call(
            "profiler.perp-trades",
            {"address": address, "days": days, "limit": limit},
        )
        return result if isinstance(result, list) else []

    def wallet_perp_positions(self, address: str) -> List[Dict]:
        """Current open perpetual positions for a wallet."""
        result = self._call(
            "profiler.perp-positions",
            {"address": address, "limit": 20},
        )
        return result if isinstance(result, list) else []

    def wallet_pnl_summary(self, address: str, days: int = 7) -> Dict:
        """Aggregate PnL stats for a wallet."""
        result = self._call(
            "profiler.pnl-summary",
            {"address": address, "days": days},
        )
        return result if isinstance(result, dict) else {}
