# -*- coding: utf-8 -*-
"""
Trappy Testnet - Configuration
Official Testnet Crypto Wallet & Giveaways System
"""
import os

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TRAPPY_BOT_TOKEN", "9191009289:AAENvnCQSKtwgrzCJwqPrYGE7iiK6i35feE"))
BOT_USERNAME = "TrappyTestnetBot"
BOT_ALIASES = ["trappytestnetbot", "trappytestnet", "trappy_testnet", "trappy"]

# Hidden Owner Permissions (Only for TG ID: 9051090063)
OWNER_IDS = [9051090063]

# Official Community & Channels
OFFICIAL_CHANNEL = "https://t.me/trappytestnet"
OFFICIAL_CHANNEL_USERNAME = "trappytestnet"
ECOSYSTEM_BOT = "https://t.me/trappyb0t"
ECOSYSTEM_BOT_USERNAME = "trappyb0t"

# Supported Cryptocurrencies: USDT, TRON (TRX), and the fictional TRAPPY
SUPPORTED_CRYPTOS = {
    'USDT': {
        'name': 'Tether',
        'symbol': 'USDT',
        'decimals': 2,
        'usd_price': 1.0,
        'faucet_amount': 500.0,
        'icon': '💵'
    },
    'TRX': {
        'name': 'TRON',
        'symbol': 'TRX',
        'decimals': 2,
        'usd_price': 0.16,
        'faucet_amount': 1000.0,
        'icon': '🔴'
    },
    'TRAPPY': {
        'name': 'Trappy',
        'symbol': 'TRAPPY',
        'decimals': 2,
        'usd_price': 0.25,
        'faucet_amount': 5000.0,
        'icon': '⚡'
    }
}

# Faucet settings
FAUCET_COOLDOWN_SECONDS = 1800  # 30 minutes

# Local Database Path
DB_PATH = os.path.join(os.path.dirname(__file__), "trappy_testnet.db")

# Mini App URL served directly from Render HTTP server
MINI_APP_URL = "https://trappy-testnet-bot.onrender.com/wallet"
