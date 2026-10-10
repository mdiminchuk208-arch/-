#!/usr/bin/env bash
set -euo pipefail
cd /workspace/-
export PIP_CACHE_DIR=/workspace/.cache/pip
export MPLCONFIGDIR=/workspace/.cache/matplotlib
mkdir -p "$PIP_CACHE_DIR" "$MPLCONFIGDIR"
python3 -m venv /workspace/crypto-bot-venv
/workspace/crypto-bot-venv/bin/python -m pip install --no-input --disable-pip-version-check -e . -r requirements-dev.txt -r requirements-research.txt -r requirements-strategy-v2.txt
/workspace/crypto-bot-venv/bin/python -m pip check
/workspace/crypto-bot-venv/bin/python -c 'import numpy, scipy, sklearn, matplotlib, pyarrow; from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio; assert VirtualPortfolio().trade_entry_allowed is False'
