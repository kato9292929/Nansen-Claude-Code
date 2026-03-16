#!/usr/bin/env python3
"""
Nansen × Hyperliquid Copy-Trade Bot
────────────────────────────────────
Usage:
    python main.py [--config config.yaml]

Environment variables:
    HL_PRIVATE_KEY   Hyperliquid wallet private key (overrides config.yaml)
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def _expand_env_vars(obj):
    """Recursively expand ${VAR} placeholders in config values."""
    if isinstance(obj, str):
        return re.sub(
            r"\$\{(\w+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            obj,
        )
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(v) for v in obj]
    return obj


def load_config(path: str) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    return _expand_env_vars(cfg)


def setup_logging(cfg: dict):
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    log_file = log_cfg.get("file")

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=handlers,
    )


def main():
    parser = argparse.ArgumentParser(description="Nansen × Hyperliquid copy-trade bot")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"Config file not found: {args.config}")
        sys.exit(1)

    cfg = load_config(args.config)
    setup_logging(cfg)

    logger = logging.getLogger("main")
    logger.info("Loaded config from %s", args.config)

    from bot.bot import CopyTradeBot
    try:
        bot = CopyTradeBot(cfg)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
