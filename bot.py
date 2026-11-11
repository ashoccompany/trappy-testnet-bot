# -*- coding: utf-8 -*-
"""
Trappy Testnet - Main Telegram Bot
Multi-Asset (USDT, TRX, TRAPPY) with Telegram Mini App & Inline Mention Transfers
"""
import re
import time
import logging
import os
import secrets
import http.server
import socketserver
import threading
import json

import telebot
from telebot import types
from telebot.types import (
    InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton
)

import config
import database as db
import keyboards as kb

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("TrappyTestnet")

# Initialize database
db.init_db()

# Render Keep-Alive HTTP Health Server
class RenderHealthHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # 1. Serve Mini App HTML directly from Render (Zero redirects, instant load)
        if path in ['/', '/wallet', '/index.html']:
            html_path = os.path.join(os.path.dirname(__file__), "webapp", "index.html")
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
            return

        # 2. Live Mini App Wallet API
        if path == '/api/wallet':
            qs = urllib.parse.parse_qs(parsed.query)
            user_id_raw = qs.get('user_id', [None])[0]
            if user_id_raw and str(user_id_raw).isdigit():
                uid = int(user_id_raw)
                user = db.get_or_create_user(uid)
                balances = db.get_all_balances(uid)
                total_usd = sum(balances.get(sym, 0.0) * info['usd_price'] for sym, info in config.SUPPORTED_CRYPTOS.items())
                data = {
                    "ok": True,
                    "user_id": uid,
                    "username": user.get('username', ''),
                    "first_name": user.get('first_name', ''),
                    "wallet_id": user.get('wallet_id', ''),
                    "tron_address": user.get('tron_address', ''),
                    "trappy_address": user.get('trappy_address', ''),
                    "balances": {sym: round(balances.get(sym, 0.0), 2) for sym in config.SUPPORTED_CRYPTOS},
                    "prices": {sym: info['usd_price'] for sym, info in config.SUPPORTED_CRYPTOS.items()},
                    "total_usd": round(total_usd, 2)
                }
            else:
                data = {"ok": False, "error": "Missing or invalid user_id parameter"}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return

        # 3. Keep-alive health check for anti-sleeper
        if path in ['/health', '/healthz']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            resp = json.dumps({
                "status": "healthy",
                "service": "trappy-testnet-bot",
                "assets": ["USDT", "TRX", "TRAPPY"]
            })
            self.wfile.write(resp.encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/faucet':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
                data = json.loads(body)
                user_id_raw = data.get('user_id')
                resp = {
                    "ok": False,
                    "error": "Public faucet is disabled. Testnet allocations are granted by the administrator."
                }
            except Exception as e:
                resp = {"ok": False, "error": str(e)}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_render_health_server():
    port = int(os.environ.get('PORT', 10000))
    try:
        server = socketserver.TCPServer(('0.0.0.0', port), RenderHealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Render keep-alive HTTP server listening on port {port}")
    except Exception as e:
        logger.warning(f"Could not start Render health server: {e}")

# Start Keep-Alive Server immediately
start_render_health_server()

# Initialize TeleBot
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

# In-memory states for multi-step prompts
user_states = {}

# Set native Telegram Chat Menu Button and Default Administrator Rights on startup
try:
    bot.set_chat_menu_button(
        menu_button=types.MenuButtonWebApp(
            type="web_app",
            text="👛 Wallet",
            web_app=types.WebAppInfo(url=config.MINI_APP_URL)
        )
    )
except Exception as e:
    logger.warning(f"Could not set chat menu button: {e}")

try:
    rights_channel = types.ChatAdministratorRights(
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_messages=True,
        can_edit_messages=True
    )
    bot.set_my_default_administrator_rights(rights=rights_channel, for_channels=True)
    
    rights_group = types.ChatAdministratorRights(
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=True
    )
    bot.set_my_default_administrator_rights(rights=rights_group, for_channels=False)
except Exception as e:
    logger.warning(f"Could not set default administrator rights: {e}")

# ==============================================================================
# WALLET FORMATTING (EXACTLY 3 CRYPTOS: USDT, TRX, TRAPPY)
# ==============================================================================
def format_crypto_amount(val, sym):
    if val == 0:
        return "0"
    if val == int(val):
        return f"{int(val):,}"
    dec = config.SUPPORTED_CRYPTOS.get(sym, {}).get('decimals', 2)
    return f"{val:,.{dec}f}".rstrip('0').rstrip('.')

def render_wallet_text(user_id):
    user = db.get_user(user_id)
    if not user:
        return "Wallet not found."
    balances = db.get_all_balances(user_id)
    usd_total = db.calculate_usd_total(balances)
    
    t_addr = user.get('tron_address') or db.generate_tron_address(user_id)
    trp_addr = user.get('trappy_address') or db.generate_trappy_address(user_id)
    
    lines = [
        "👛 <b>Wallet</b>\n",
        f"<b>Tether</b>: {format_crypto_amount(balances.get('USDT', 0), 'USDT')} USDT\n",
        f"<b>TRON</b>: {format_crypto_amount(balances.get('TRX', 0), 'TRX')} TRX\n",
        f"<b>Trappy</b>: {format_crypto_amount(balances.get('TRAPPY', 0), 'TRAPPY')} TRAPPY\n",
        f"≈ ${usd_total:,.2f}\n",
        "🏷️ <b>Testnet Deposit Addresses:</b>",
        f"• <b>TRC-20 (USDT / TRX):</b>\n<code>{t_addr}</code>",
        f"• <b>Trappy Native:</b>\n<code>{trp_addr}</code>"
    ]
    return "\n".join(lines)

def send_wallet_message(chat_id, user_id):
    try:
        user = db.get_or_create_user(user_id)
        text = render_wallet_text(user_id)
        balances = db.get_all_balances(user_id)
        user_url = f"{config.MINI_APP_URL}?user_id={user_id}"
        
        bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb.get_wallet_inline_keyboard(webapp_url=user_url)
        )
    except Exception as e:
        logger.warning(f"Error sending wallet message: {e}")

# ==============================================================================
# SENDER EXTRACTION & SAFE MESSAGING (SUPPORTS USERS, ADMINS & CHANNELS)
# ==============================================================================
def get_message_sender(message):
    """
    Safely retrieves (user_id, username, display_name) for any Telegram update,
    whether sent by a direct user, an anonymous admin, or a channel broadcast.
    """
    if getattr(message, 'from_user', None):
        u_id = message.from_user.id
        u_name = message.from_user.username or ''
        first_name = message.from_user.first_name or f"User {u_id}"
        disp_name = f"@{u_name}" if u_name else first_name
        return u_id, u_name, disp_name
    elif getattr(message, 'sender_chat', None):
        c_name = message.sender_chat.username or ''
        c_title = message.sender_chat.title or "Channel"
        disp_name = f"@{c_name}" if c_name else c_title
        return config.OWNER_IDS[0], c_name, disp_name
    elif getattr(message, 'chat', None):
        c_name = message.chat.username or ''
        c_title = message.chat.title or "Channel"
        disp_name = f"@{c_name}" if c_name else c_title
        return config.OWNER_IDS[0], c_name, disp_name
    return config.OWNER_IDS[0], '', 'Anonymous'

def safe_reply(message, text, reply_markup=None):
    try:
        return bot.reply_to(message, text, reply_markup=reply_markup)
    except Exception:
        try:
            return bot.send_message(message.chat.id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"Could not send reply: {e}")
            return None

# ==============================================================================
# COMMAND: /start, /wallet, /cheques, /help
# ==============================================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id, username, first_name = get_message_sender(message)
    user = db.get_or_create_user(user_id=user_id, username=username, first_name=first_name)
    
    args = message.text.split()
    if len(args) > 1:
        param = args[1]
        if param.startswith("c_"):
            execute_claim_cheque(user_id, param, message.chat.id)
            return
        elif param.startswith("iv_"):
            execute_view_invoice(user_id, param, message.chat.id)
            return
        elif param.startswith("claim_gw_"):
            gw_id = param.replace("claim_", "")
            execute_claim_giveaway(user_id, gw_id, message.chat.id)
            return

    # First-time onboarding experience
    if user.get('is_new', False):
        t_addr = user.get('tron_address') or db.generate_tron_address(user_id)
        trp_addr = user.get('trappy_address') or db.generate_trappy_address(user_id)
        welcome_text = (
            f"⚡ <b>Welcome to Trappy Testnet, {first_name}!</b>\n\n"
            "Your multi-currency testnet crypto wallet is ready. Send, receive, and create "
            "instant claimable cheques and invoices in private chats, groups, and channels.\n\n"
            "💎 <b>Supported Testnet Assets:</b>\n"
            "• <b>USDT</b> — Tether (TRC-20, $1.00)\n"
            "• <b>TRX</b> — TRON Network ($0.16)\n"
            "• <b>TRAPPY</b> — Trappy Native ($0.25)\n\n"
            "👛 <b>Your Testnet Deposit Addresses:</b>\n"
            f"• <b>TRC-20:</b> <code>{t_addr}</code>\n"
            f"• <b>Trappy:</b> <code>{trp_addr}</code>\n\n"
            "📥 <i>Share your testnet address to receive funds, or tap below to manage your wallet:</i>"
        )
        try:
            bot.send_message(
                chat_id=message.chat.id,
                text=welcome_text,
                reply_markup=kb.get_welcome_inline_keyboard()
            )
            bot.send_message(
                chat_id=message.chat.id,
                text="💡 <b>Quick Navigation:</b>",
                reply_markup=kb.get_main_reply_keyboard()
            )
            send_wallet_message(message.chat.id, user_id)
        except Exception as e:
            logger.warning(f"Error in start welcome: {e}")
        return

    main_text = (
        f"⚡ <b>Trappy Testnet</b>\n\n"
        f"Address: <code>{user['wallet_id']}</code>\n\n"
        "Manage your balances below or send quick transfers using:\n"
        "<code>$10 @username</code>"
    )
    try:
        bot.send_message(
            chat_id=message.chat.id,
            text=main_text,
            reply_markup=kb.get_main_reply_keyboard()
        )
        send_wallet_message(message.chat.id, user_id)
    except Exception as e:
        logger.warning(f"Error in start handler: {e}")

@bot.message_handler(commands=['wallet'])
def handle_cmd_wallet(message):
    user_id, _, _ = get_message_sender(message)
    send_wallet_message(message.chat.id, user_id)

@bot.message_handler(commands=['addtochannel', 'channel', 'addchannel'])
def handle_cmd_add_to_channel(message):
    txt = (
        "📢 <b>Add Trappy Testnet to Your Channel</b>\n\n"
        "In Telegram, bots can only join channels as <b>Administrators</b>.\n\n"
        "⚡ <b>Option 1 (Instant 1-Click Link):</b>\n"
        "Tap the button below to pick your channel and instantly add the bot with required rights.\n\n"
        "⚡ <b>Option 2 (Manual Settings):</b>\n"
        "Open your Channel ➔ <b>Administrators</b> ➔ <b>Add Administrator</b> ➔ Search <code>@TrappyTestnetBot</code> ➔ Save."
    )
    bot.send_message(message.chat.id, txt, reply_markup=kb.get_add_to_channel_keyboard())

@bot.message_handler(commands=['cheques'])
def handle_cmd_cheques(message):
    user_id, _, _ = get_message_sender(message)
    show_cheques_info(message.chat.id, user_id)

@bot.message_handler(commands=['cheque', 'check'])
def handle_cmd_cheque(message):
    user_id, username, first_name = get_message_sender(message)
    db.get_or_create_user(user_id, username, first_name)
    parts = message.text.split(maxsplit=4)
    if len(parts) < 3:
        safe_reply(
            message,
            "💡 <b>Usage:</b>\n<code>/cheque &lt;amount&gt; &lt;currency&gt; [winners] [comment]</code>\n\n"
            "<b>Examples:</b>\n"
            "• Single cheque: <code>/cheque 50 USDT For lunch</code>\n"
            "• Multi cheque: <code>/cheque 1000 TRAPPY 5</code>"
        )
        return
    amt_str = parts[1]
    curr_str = parts[2]
    winners_str = "1"
    note = ""
    if len(parts) > 3:
        if parts[3].isdigit():
            winners_str = parts[3]
            note = parts[4] if len(parts) > 4 else ""
        else:
            note = " ".join(parts[3:])
    execute_create_cheque(message, user_id, amt_str, curr_str, winners_str=winners_str, note=note)

@bot.message_handler(commands=['invoice', 'bill'])
def handle_cmd_invoice(message):
    user_id, username, first_name = get_message_sender(message)
    db.get_or_create_user(user_id, username, first_name)
    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        safe_reply(
            message,
            "💡 <b>Usage:</b>\n<code>/invoice &lt;amount&gt; &lt;currency&gt; [description]</code>\n\n"
            "<b>Example:</b>\n<code>/invoice 25 USDT For coffee</code>"
        )
        return
    amt_str = parts[1]
    curr_str = parts[2]
    note = parts[3] if len(parts) > 3 else ""
    execute_create_invoice(message, user_id, amt_str, curr_str, note=note)

@bot.message_handler(commands=['help'])
def handle_cmd_help(message):
    help_text = (
        "⚡ <b>Trappy Testnet Guide</b>\n\n"
        "• <b>Wallet:</b> /wallet — View your balances & realistic testnet addresses.\n"
        "• <b>Cheque:</b> <code>/cheque 50 USDT [comment]</code> — Create claimable cheque.\n"
        "• <b>Invoice:</b> <code>/invoice 25 USDT [desc]</code> — Request payment.\n"
        "• <b>Pay:</b> <code>/pay @username 100 USDT</code> — Transfer testnet coins.\n"
        "• <b>Pay to Address:</b> <code>/pay TRmz... 50 USDT</code> or <code>/pay trp1... 500 TRAPPY</code>\n"
        "• <b>Dollar shortcut:</b> <code>$10 @username</code> — Quick send $10 USDT.\n"
        "• <b>Giveaway:</b> <code>/giveaway 500 TRAPPY 5</code> — Create channel/chat giveaway.\n\n"
        "📢 Official Channel: @trappytestnet\n"
        "🤖 Ecosystem: @trappyb0t"
    )
    bot.send_message(message.chat.id, help_text)

# ==============================================================================
# REPLY KEYBOARD ROUTING (DM & CHAT FRIENDLY)
# ==============================================================================
@bot.message_handler(func=lambda m: m.text == "👛 Wallet")
def handle_btn_wallet(message):
    user_id, _, _ = get_message_sender(message)
    send_wallet_message(message.chat.id, user_id)

@bot.message_handler(func=lambda m: m.text == "✉️ Cheques")
def handle_btn_cheques(message):
    txt = (
        "✉️ <b>Trappy Testnet Cheques</b>\n\n"
        "Create claimable crypto cheques to send in DMs, groups, or channels!\n"
        "Choose an instant preset below or enter a custom amount:"
    )
    bot.send_message(message.chat.id, txt, reply_markup=kb.get_cheque_menu_inline())

@bot.message_handler(func=lambda m: m.text == "💳 Invoices")
def handle_btn_invoices(message):
    txt = (
        "💳 <b>Trappy Testnet Invoices</b>\n\n"
        "Request testnet crypto from any Telegram user or in DMs.\n"
        "Choose an instant preset below or create a custom invoice:"
    )
    bot.send_message(message.chat.id, txt, reply_markup=kb.get_invoice_menu_inline())
@bot.message_handler(func=lambda m: m.text in ["📤 Send / Transfer", "📤 Send"])
def handle_btn_send_transfer(message):
    sender_id, _, _ = get_message_sender(message)
    txt = (
        "📤 <b>Send / Transfer Testnet Crypto</b>\n\n"
        "You can transfer testnet coins to any Telegram user, realistic crypto address, or wallet ID!\n\n"
        "<b>Quick Formats:</b>\n"
        "• By username: <code>$10 @username [comment]</code>\n"
        "• By command: <code>/pay @username 50 USDT [comment]</code>\n"
        "• By TRC-20 address: <code>/pay TRmz... 50 USDT</code>\n"
        "• By Trappy address: <code>/pay trp1... 500 TRAPPY</code>"
    )
    bot.send_message(message.chat.id, txt, reply_markup=kb.get_withdraw_inline_keyboard())


@bot.message_handler(func=lambda m: m.text in ["🎁 Giveaways", "🎁 Cheques / Giveaways"])
def handle_btn_giveaways(message):
    user_id, _, _ = get_message_sender(message)
    show_cheques_info(message.chat.id, user_id)

def show_cheques_info(chat_id, user_id):
    is_owner = user_id in config.OWNER_IDS
    owner_note = ""
    txt = (
        "🎁 <b>Crypto Cheques & Giveaways</b>\n\n"
        "Create multi-user giveaways or direct cheques in channels and chats!\n\n"
        "📌 <b>Create a Giveaway:</b>\n"
        "<code>/giveaway &lt;amount&gt; &lt;currency&gt; &lt;winners&gt;</code>\n"
        "Example:\n<code>/giveaway 1000 TRAPPY 5</code>"
        f"{owner_note}\n\n"
        "📢 <b>Giveaways Channel:</b> @trappytestnet"
    )
    bot.send_message(chat_id, txt, reply_markup=kb.get_channel_invite_inline())

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
def handle_btn_about(message):
    txt = (
        "⚡ <b>Trappy Testnet</b>\n\n"
        "Simulated cryptocurrency wallet and giveaway platform.\n\n"
        "• <b>Channel:</b> @trappytestnet\n"
        "• <b>Ecosystem:</b> @trappyb0t\n"
        "• <b>Assets:</b> USDT, TRX, TRAPPY"
    )
    bot.send_message(message.chat.id, txt)

# ==============================================================================
# MENTION & DIRECT COMMAND ENGINE
# Matches:
# @CryptoTestnetBot $10 @username Comment...
# @TrappyTestnet $10 @username
# @TrappyTestnet pay @username 500 USDT
# ==============================================================================
MENTION_DOLLAR_PAY_REGEX = re.compile(
    r'(?:@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+)?\$([\d.]+)\s+@?([a-zA-Z0-9_]{3,32})(?:\s+(.*))?',
    re.IGNORECASE
)

MENTION_PAY_REGEX = re.compile(
    r'(?:@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+)?(?:pay|send)\s+@?([a-zA-Z0-9_]{3,32})\s+([\d.]+)\s*([a-zA-Z]+)(?:\s+(.*))?',
    re.IGNORECASE
)

MENTION_GIVEAWAY_REGEX = re.compile(
    r'(?:@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+)?(?:giveaway|airdrop)\s+([\d.]+)\s*([a-zA-Z]+)\s*(\d+)',
    re.IGNORECASE
)

MENTION_ADDCRYPTO_REGEX = re.compile(
    r'(?:@(?:TrappyTestnetBot|TrappyTestnet|trappytestnetbot|trappytestnet|trappy)\s+)?addcrypto\s+@?([a-zA-Z0-9_]{2,32})\s+([\d.]+)\s*([a-zA-Z]+)',
    re.IGNORECASE
)


MENTION_CHEQUE_REGEX = re.compile(
    r'(?:@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+)?(?:cheque|check)\s+([\d.]+)\s*([a-zA-Z]+)(?:\s+(\d+))?(?:\s+(.*))?',
    re.IGNORECASE
)

MENTION_INVOICE_REGEX = re.compile(
    r'(?:@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+)?invoice\s+([\d.]+)\s*([a-zA-Z]+)(?:\s+(.*))?',
    re.IGNORECASE
)

MENTION_FAUCET_REGEX = re.compile(
    r'@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+(?:faucet|deposit)',
    re.IGNORECASE
)

MENTION_WALLET_REGEX = re.compile(
    r'@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+(?:wallet|balance)',
    re.IGNORECASE
)

def process_mention_or_command(message, text, is_channel=False):
    sender_id, sender_username, sender_name = get_message_sender(message)
    db.get_or_create_user(sender_id, sender_username, sender_name)

    # 1. Matching Dollar Pay: @TrappyTestnetBot $10 @username Comment...
    m_dollar = MENTION_DOLLAR_PAY_REGEX.search(text)
    if m_dollar:
        amount_str, target_username, comment = m_dollar.groups()
        execute_payment(message, sender_id, target_username, amount_str, "USDT", note=comment or "")
        return

    # 2. Mention Pay: @TrappyTestnet pay @someusername 500 TRAPPY
    m_pay = MENTION_PAY_REGEX.search(text)
    if m_pay:
        target_username, amount_str, currency_raw, comment = m_pay.groups()
        execute_payment(message, sender_id, target_username, amount_str, currency_raw, note=comment or "")
        return

    # 3. Mention Cheque: @TrappyTestnet cheque 1000 TRAPPY 5 [note]
    m_cheque = MENTION_CHEQUE_REGEX.search(text)
    if m_cheque:
        amount_str, currency_raw, winners_str, comment = m_cheque.groups()
        execute_create_cheque(message, sender_id, amount_str, currency_raw, winners_str or "1", note=comment or "")
        return

    # 4. Mention Invoice: @TrappyTestnet invoice 25 USDT [note]
    m_invoice = MENTION_INVOICE_REGEX.search(text)
    if m_invoice:
        amount_str, currency_raw, comment = m_invoice.groups()
        execute_create_invoice(message, sender_id, amount_str, currency_raw, note=comment or "")
        return

    # 5. Mention Giveaway: @TrappyTestnet giveaway 1000 TRAPPY 5
    m_gw = MENTION_GIVEAWAY_REGEX.search(text)
    if m_gw:
        amount_str, currency_raw, winners_str = m_gw.groups()
        execute_create_giveaway(message, sender_id, amount_str, currency_raw, winners_str)
        return

    # 6. Silent Owner Addcrypto: @TrappyTestnet addcrypto @username 1000 USDT
    m_add = MENTION_ADDCRYPTO_REGEX.search(text)
    if m_add and sender_id in config.OWNER_IDS:
        target_str, amount_str, currency_raw = m_add.groups()
        execute_addcrypto(message, sender_id, target_str, amount_str, currency_raw)
        return

    # 7. Mention Wallet: @TrappyTestnet wallet
    if MENTION_WALLET_REGEX.search(text):
        send_wallet_message(message.chat.id, sender_id)
        return

    # 8. Mention Faucet: @TrappyTestnet faucet
    if MENTION_FAUCET_REGEX.search(text):
        show_deposit_options(message.chat.id, sender_id)
        return

    # 9. Pure Mention Fallback (When bot is tagged or mentioned in any chat/channel)
    mention_resp = (
        "⚡ <b>Trappy Testnet Bot</b> is active in this chat!\n\n"
        "💡 <b>Available Inline & Mention Commands:</b>\n"
        "• <code>@TrappyTestnetBot $10 @username [comment]</code> — Instant payment\n"
        "• <code>@TrappyTestnetBot pay @username 50 USDT</code> — Transfer testnet crypto\n"
        "• <code>@TrappyTestnetBot cheque 100 TRAPPY 5</code> — Multi-claim cheque\n"
        "• <code>@TrappyTestnetBot invoice 25 USDT</code> — Request payment\n"
        "• <code>@TrappyTestnetBot wallet</code> — Check your balance & addresses\n\n"
        "Tap below to open your Web Wallet or manage assets:"
    )
    safe_reply(message, mention_resp, reply_markup=kb.get_mention_response_inline())

@bot.message_handler(func=lambda m: bool(m.text and ('$' in m.text or any(alias in m.text.lower() for alias in config.BOT_ALIASES))))
def handle_bot_mentions(message):
    process_mention_or_command(message, message.text.strip(), is_channel=False)

@bot.channel_post_handler(func=lambda cp: True)
def handle_channel_posts(post):
    text = (post.text or post.caption or "").strip()
    if not text:
        return
    is_mentioned = any(alias in text.lower() for alias in config.BOT_ALIASES) or '$' in text or text.startswith('/')
    if is_mentioned:
        process_mention_or_command(post, text, is_channel=True)

@bot.my_chat_member_handler()
def handle_chat_member_update(update):
    new_status = update.new_chat_member.status
    chat = update.chat
    if new_status in ['administrator', 'member']:
        welcome_txt = (
            f"⚡ <b>Trappy Testnet Connected to {chat.title}!</b>\n\n"
            "This chat is now equipped with Trappy Testnet crypto capabilities.\n"
            "Members can send testnet coins, claim cheques, and run community giveaways.\n\n"
            "👇 Tap below to launch your Testnet Wallet:"
        )
        try:
            bot.send_message(
                chat.id,
                welcome_txt,
                reply_markup=kb.get_channel_connected_inline()
            )
        except Exception as e:
            logger.warning(f"Could not send join message to chat {chat.id}: {e}")

# ==============================================================================
# SLASH COMMANDS: /pay & /giveaway
# ==============================================================================
@bot.message_handler(commands=['pay', 'send'])
def handle_slash_pay(message):
    sender_id, sender_username, sender_name = get_message_sender(message)
    db.get_or_create_user(sender_id, sender_username, sender_name)
    parts = message.text.split()
    
    if message.reply_to_message and len(parts) >= 3:
        target_user = getattr(message.reply_to_message, 'from_user', None)
        if target_user:
            db.get_or_create_user(target_user.id, target_user.username or '', target_user.first_name or 'User')
            target_username = target_user.username or str(target_user.id)
        elif getattr(message.reply_to_message, 'sender_chat', None):
            target_username = message.reply_to_message.sender_chat.username or message.reply_to_message.sender_chat.title or 'Channel'
        else:
            target_username = parts[1]
        execute_payment(message, sender_id, target_username, parts[1], parts[2])
        return
        
    if len(parts) < 4:
        safe_reply(
            message,
            "💡 <b>Usage:</b>\n<code>/pay @username 100 USDT</code>\nor: <code>$10 @username</code>"
        )
        return
    execute_payment(message, sender_id, parts[1], parts[2], parts[3])

def execute_payment(message, sender_id, target_str, amount_str, currency_raw, note=""):
    currency = currency_raw.upper()
    if currency not in config.SUPPORTED_CRYPTOS:
        safe_reply(message, f"❌ Unsupported currency: <code>{currency}</code>\nSupported: {', '.join(config.SUPPORTED_CRYPTOS.keys())}")
        return
        
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        safe_reply(message, "❌ Invalid amount entered.")
        return
        
    target_user = db.find_user(target_str)
    target_chan = None
    if not target_user:
        target_chan = db.find_channel_by_target(target_str)
        if target_chan:
            to_user_id = target_chan.get('added_by') or config.OWNER_IDS[0]
            target_user = {'user_id': to_user_id, 'username': target_chan.get('username', ''), 'first_name': target_chan.get('title', 'Channel')}
        else:
            safe_reply(message, f"❌ Target user or channel <code>@{target_str.lstrip('@')}</code> not found.")
            return
    else:
        to_user_id = target_user['user_id']
        target_chan = db.find_channel_by_target(target_str)
    success, reason = db.transfer_crypto(sender_id, to_user_id, currency, amount, note=note)
    
    if success:
        formatted_amt = format_crypto_amount(amount, currency)
        _, _, sender_name = get_message_sender(message)
        receiver_name = f"@{target_user.get('username')}" if target_user.get('username') else (
            f"<code>{target_str[:12]}...</code>" if len(target_str) > 20 else target_user['first_name']
        )
        note_line = f"\n💬 <i>Note: {note}</i>" if note else ""
        
        reply_txt = (
            f"💸 <b>Transfer Successful!</b>\n\n"
            f"From: {sender_name}\n"
            f"To: {receiver_name}\n"
            f"Amount: <b>{formatted_amt} {currency}</b>{note_line}\n"
            f"Status: ✅ Instant Settlement"
        )
        safe_reply(message, reply_txt)
        
        # Broadcast live to channel if Message-after-Pay is enabled
        if target_chan:
            broadcast_channel_payment(target_chan['chat_id'], sender_name, formatted_amt, currency, note)

        try:
            bot.send_message(
                to_user_id,
                f"🎉 <b>You received testnet crypto!</b>\n+{formatted_amt} {currency} from {sender_name}!{note_line}"
            )
        except Exception:
            pass
    else:
        if reason == "insufficient_balance":
            bal = db.get_balance(sender_id, currency)
            safe_reply(message, f"❌ Insufficient balance! You have <b>{format_crypto_amount(bal, currency)} {currency}</b>.")
        elif reason == "Cannot send to yourself":
            safe_reply(message, "❌ You cannot send crypto to yourself!")
        else:
            safe_reply(message, f"❌ Transfer failed: {reason}")

# ==============================================================================
# CHEQUES & INVOICES EXECUTION ENGINE
# ==============================================================================
def execute_create_cheque(message, sender_id, amount_str, currency_raw, winners_str="1", note=""):
    currency = currency_raw.upper()
    if currency not in config.SUPPORTED_CRYPTOS:
        safe_reply(message, f"❌ Unsupported currency: <code>{currency}</code>")
        return
    try:
        amount = float(amount_str)
        winners = int(winners_str) if winners_str else 1
        if amount <= 0 or winners <= 0:
            raise ValueError()
    except ValueError:
        safe_reply(message, "❌ Invalid amount or winners count.")
        return

    success, reason, ch_id = db.create_cheque(sender_id, currency, amount, winners, note=note)
    if success:
        amt_each = amount / float(winners)
        f_total = format_crypto_amount(amount, currency)
        f_each = format_crypto_amount(amt_each, currency)
        _, _, sender_tag = get_message_sender(message)
        note_str = f"\n💬 <i>Note: {note}</i>" if note else ""
        mult_str = f"\n👥 <b>Winners:</b> {winners} ({f_each} {currency} each)" if winners > 1 else ""
        
        txt = (
            f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
            f"💰 <b>Amount:</b> <b>{f_total} {currency}</b>{mult_str}\n"
            f"👤 <b>Creator:</b> {sender_tag}{note_str}\n\n"
            f"Tap the button below to claim this cheque into your wallet!"
        )
        safe_reply(message, txt, reply_markup=kb.get_cheque_claim_inline(ch_id, claimed=0, winners=winners))
    else:
        if reason == "insufficient_balance":
            bal = db.get_balance(sender_id, currency)
            safe_reply(message, f"❌ Insufficient balance! You have <b>{format_crypto_amount(bal, currency)} {currency}</b>.")
        else:
            safe_reply(message, f"❌ Failed to create cheque: {reason}")

def execute_claim_cheque(user_id, ch_id, chat_id, call=None):
    ch = db.get_cheque(ch_id)
    if not ch:
        if call:
            bot.answer_callback_query(call.id, "Cheque not found.", show_alert=True)
        else:
            bot.send_message(chat_id, "❌ Cheque not found.")
        return
        
    success, reason, amt, currency, rem = db.claim_cheque(ch_id, user_id)
    if success:
        famt = format_crypto_amount(amt, currency)
        if call:
            bot.answer_callback_query(call.id, f"🎉 Claimed +{famt} {currency}!", show_alert=True)
            updated = db.get_cheque(ch_id)
            try:
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=kb.get_cheque_claim_inline(
                        ch_id, updated['claimed_count'], updated['winners_count'],
                        is_completed=(updated['status'] == 'completed')
                    )
                )
            except Exception:
                pass
        else:
            bot.send_message(chat_id, f"🎉 <b>Cheque Claimed!</b> +{famt} {currency} added to your wallet!")
    else:
        if reason == "already_claimed":
            if call:
                bot.answer_callback_query(call.id, "⚠️ You have already claimed this cheque!", show_alert=True)
            else:
                bot.send_message(chat_id, "⚠️ You have already claimed this cheque!")
        elif reason == "completed":
            if call:
                bot.answer_callback_query(call.id, "❌ This cheque has already been fully claimed!", show_alert=True)
            else:
                bot.send_message(chat_id, "❌ This cheque has already been fully claimed!")
        else:
            if call:
                bot.answer_callback_query(call.id, f"Error: {reason}", show_alert=True)

def execute_create_invoice(message, sender_id, amount_str, currency_raw, note=""):
    currency = currency_raw.upper()
    if currency not in config.SUPPORTED_CRYPTOS:
        safe_reply(message, f"❌ Unsupported currency: <code>{currency}</code>")
        return
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        safe_reply(message, "❌ Invalid amount.")
        return
        
    success, reason, iv_id = db.create_invoice(sender_id, currency, amount, note=note)
    if success:
        f_amt = format_crypto_amount(amount, currency)
        _, _, sender_tag = get_message_sender(message)
        note_str = f"\n💬 <i>Description: {note}</i>" if note else ""
        txt = (
            f"💳 <b>PAYMENT INVOICE</b>\n\n"
            f"💰 <b>Amount:</b> <b>{f_amt} {currency}</b>\n"
            f"👤 <b>Pay to:</b> {sender_tag}{note_str}\n\n"
            f"Tap the button below to pay this invoice."
        )
        safe_reply(message, txt, reply_markup=kb.get_invoice_pay_inline(iv_id, f_amt, currency))
    else:
        safe_reply(message, f"❌ Failed to create invoice: {reason}")

def execute_pay_invoice(user_id, iv_id, call):
    iv = db.get_invoice(iv_id)
    if not iv:
        bot.answer_callback_query(call.id, "Invoice not found.", show_alert=True)
        return
    success, reason, amt, currency, creator_id = db.pay_invoice(iv_id, user_id)
    if success:
        famt = format_crypto_amount(amt, currency)
        bot.answer_callback_query(call.id, f"✅ Paid {famt} {currency}!", show_alert=True)
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=kb.get_invoice_pay_inline(iv_id, famt, currency, is_paid=True)
            )
        except Exception:
            pass
        payer = db.get_user(user_id)
        pname = f"@{payer['username']}" if payer.get('username') else payer.get('first_name', 'Someone')
        try:
            bot.send_message(creator_id, f"🎉 <b>Invoice Paid!</b>\n{pname} paid your invoice of <b>{famt} {currency}</b>!")
        except Exception:
            pass
    else:
        if reason == "insufficient_balance":
            bal = db.get_balance(user_id, currency)
            bot.answer_callback_query(call.id, f"❌ Insufficient balance! You have {format_crypto_amount(bal, currency)} {currency}.", show_alert=True)
        elif reason == "cannot_pay_self":
            bot.answer_callback_query(call.id, "❌ You cannot pay your own invoice!", show_alert=True)
        elif reason == "already_paid":
            bot.answer_callback_query(call.id, "✅ This invoice has already been paid!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"Payment failed: {reason}", show_alert=True)

def execute_view_invoice(user_id, iv_id, chat_id):
    iv = db.get_invoice(iv_id)
    if not iv:
        bot.send_message(chat_id, "❌ Invoice not found.")
        return
    f_amt = format_crypto_amount(iv['amount'], iv['currency'])
    creator = db.get_user(iv['creator_id'])
    cname = f"@{creator['username']}" if creator and creator.get('username') else (creator['first_name'] if creator else "User")
    note_str = f"\n💬 <i>Description: {iv['note']}</i>" if iv['note'] else ""
    txt = (
        f"💳 <b>PAYMENT INVOICE</b>\n\n"
        f"💰 <b>Amount:</b> <b>{f_amt} {iv['currency']}</b>\n"
        f"👤 <b>Pay to:</b> {cname}{note_str}\n\n"
        f"Status: {'✅ Paid' if iv['status'] == 'paid' else '⚡ Active'}"
    )
    bot.send_message(chat_id, txt, reply_markup=kb.get_invoice_pay_inline(iv_id, f_amt, iv['currency'], is_paid=(iv['status'] == 'paid')))

@bot.message_handler(commands=['giveaway', 'airdrop'])
def handle_slash_giveaway(message):
    sender_id, sender_username, sender_name = get_message_sender(message)
    db.get_or_create_user(sender_id, sender_username, sender_name)
    parts = message.text.split()
    if len(parts) < 4:
        safe_reply(
            message,
            "💡 <b>Usage:</b>\n<code>/giveaway &lt;amount&gt; &lt;currency&gt; &lt;winners_count&gt;</code>\n"
            "Example: <code>/giveaway 1000 TRAPPY 5</code>"
        )
        return
    execute_create_giveaway(message, sender_id, parts[1], parts[2], parts[3])

def execute_create_giveaway(message, sender_id, amount_str, currency_raw, winners_str, channel="trappytestnet"):
    currency = currency_raw.upper()
    if currency not in config.SUPPORTED_CRYPTOS:
        safe_reply(message, f"❌ Unsupported currency: <code>{currency}</code>")
        return
        
    try:
        amount = float(amount_str)
        winners = int(winners_str)
        if amount <= 0 or winners <= 0:
            raise ValueError()
    except ValueError:
        safe_reply(message, "❌ Amount and winners count must be positive numbers.")
        return
        
    success, reason, gw_id = db.create_giveaway(sender_id, currency, amount, winners, channel)
    
    if success:
        amt_per_user = amount / float(winners)
        formatted_total = format_crypto_amount(amount, currency)
        formatted_each = format_crypto_amount(amt_per_user, currency)
        _, _, creator_tag = get_message_sender(message)
        
        gw_text = (
            f"🎁 <b>TRAPPY TESTNET GIVEAWAY!</b>\n\n"
            f"💰 <b>Total Pool:</b> <b>{formatted_total} {currency}</b>\n"
            f"👥 <b>Winners:</b> {winners} ({formatted_each} {currency} each)\n"
            f"👑 <b>Host:</b> {creator_tag}\n"
            f"📢 <b>Channel:</b> @{channel}\n\n"
            f"Tap the button below to claim your testnet reward!"
        )
        bot.send_message(
            chat_id=message.chat.id,
            text=gw_text,
            reply_markup=kb.get_giveaway_claim_inline(gw_id, claimed=0, winners=winners)
        )
    else:
        if reason == "insufficient_balance":
            bal = db.get_balance(sender_id, currency)
            safe_reply(
                message,
                f"❌ You cannot exceed the amount in your wallet!\nYour balance: <b>{format_crypto_amount(bal, currency)} {currency}</b>."
            )
        else:
            safe_reply(message, f"❌ Failed to create giveaway: {reason}")

# ==============================================================================
# HIDDEN OWNER COMMANDS (TG ID: 9051090063 ONLY)
# ==============================================================================
@bot.message_handler(commands=['addcrypto'])
def handle_slash_addcrypto(message):
    sender_id, _, _ = get_message_sender(message)
    if sender_id not in config.OWNER_IDS:
        return
    parts = message.text.split()
    if len(parts) < 4:
        safe_reply(
            message,
            "👑 <b>Owner Addcrypto:</b>\n<code>/addcrypto @user 10000 USDT</code>\n<code>/addcrypto me 50000 TRAPPY</code>"
        )
        return
    execute_addcrypto(message, sender_id, parts[1], parts[2], parts[3])

def execute_addcrypto(message, sender_id, target_str, amount_str, currency_raw):
    if sender_id not in config.OWNER_IDS:
        return
        
    currency = currency_raw.upper()
    if currency not in config.SUPPORTED_CRYPTOS:
        safe_reply(message, f"❌ Unsupported currency: {currency}")
        return
        
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        safe_reply(message, "❌ Invalid amount.")
        return
        
    if target_str.lower() in ['me', 'self']:
        target_user = db.get_user(sender_id)
    else:
        target_user = db.find_user(target_str)
        
    if not target_user:
        safe_reply(message, f"❌ Target user '{target_str}' not found.")
        return
        
    target_uid = target_user['user_id']
    ok, new_bal = db.add_crypto(target_uid, currency, amount)
    if ok:
        tname = f"@{target_user.get('username')}" if target_user.get('username') else target_user['first_name']
        famt = format_crypto_amount(amount, currency)
        fbal = format_crypto_amount(new_bal, currency)
        safe_reply(
            message,
            f"👑 <b>Owner Added Crypto!</b>\nTarget: {tname} (<code>{target_uid}</code>)\n"
            f"Added: +<b>{famt} {currency}</b>\nNew Balance: <b>{fbal} {currency}</b>"
        )

@bot.message_handler(commands=['channel_giveaway'])
def handle_channel_giveaway(message):
    sender_id, _, _ = get_message_sender(message)
    if sender_id not in config.OWNER_IDS:
        return
        
    parts = message.text.split()
    if len(parts) < 3:
        safe_reply(
            message,
            "💡 <b>Usage:</b>\n<code>/channel_giveaway &lt;amount&gt; &lt;currency&gt; &lt;winners&gt; [channel]</code>\n"
            "Example: <code>/channel_giveaway 10000 TRAPPY 20 @trappytestnet</code>"
        )
        return
        
    amount_str = parts[1]
    currency_raw = parts[2]
    winners_str = parts[3] if len(parts) > 3 else "10"
    channel = parts[4] if len(parts) > 4 else f"@{config.OFFICIAL_CHANNEL_USERNAME}"
    
    currency = currency_raw.upper()
    if currency not in config.SUPPORTED_CRYPTOS:
        safe_reply(message, f"❌ Unsupported currency: {currency}")
        return
        
    try:
        amount = float(amount_str)
        winners = int(winners_str)
    except ValueError:
        safe_reply(message, "❌ Invalid numbers.")
        return
        
    success, reason, gw_id = db.create_giveaway(sender_id, currency, amount, winners, channel.lstrip('@'))
    if success:
        amt_per_user = amount / float(winners)
        formatted_total = format_crypto_amount(amount, currency)
        formatted_each = format_crypto_amount(amt_per_user, currency)
        
        gw_text = (
            f"🎁 <b>OFFICIAL TRAPPY TESTNET GIVEAWAY!</b>\n\n"
            f"💰 <b>Total Pool:</b> <b>{formatted_total} {currency}</b>\n"
            f"👥 <b>Winners:</b> {winners} ({formatted_each} {currency} each)\n"
            f"📢 <b>Channel:</b> {channel}\n\n"
            f"Tap the button below to claim your testnet reward!"
        )
        try:
            bot.send_message(
                chat_id=channel,
                text=gw_text,
                reply_markup=kb.get_giveaway_claim_inline(gw_id, claimed=0, winners=winners)
            )
            safe_reply(message, f"✅ Giveaway posted directly to {channel}!")
        except Exception as e:
            safe_reply(message, f"⚠️ Could not post to {channel}: {e}")
            bot.send_message(
                message.chat.id,
                gw_text,
                reply_markup=kb.get_giveaway_claim_inline(gw_id, claimed=0, winners=winners)
            )

@bot.message_handler(commands=['owner'])
def handle_cmd_owner(message):
    sender_id, _, _ = get_message_sender(message)
    if sender_id not in config.OWNER_IDS:
        return
    stats = db.get_stats()
    txt = (
        "👑 <b>Owner Controls (Hidden)</b>\n\n"
        f"Users: {stats['users']} | Giveaways: {stats['giveaways']} | Transfers: {stats['transfers']}\n\n"
        "Commands:\n"
        "• <code>/addcrypto me 10000 USDT</code>\n"
        "• <code>/addcrypto me 100000 TRAPPY</code>\n"
        "• <code>/channel_giveaway 10000 TRAPPY 20 @trappytestnet</code>"
    )
    bot.send_message(message.chat.id, txt, reply_markup=kb.get_hidden_owner_inline())

# ==============================================================================
# INLINE QUERY & MENTION DISPATCH ENGINE (UNIVERSAL TOKEN & INTENT PARSER)
# ==============================================================================
def parse_inline_query_intent(q):
    q = q.strip()
    if not q:
        return {'type': 'empty'}
        
    low = q.lower()
    
    if low in ['wallet', 'bal', 'balance', 'address', 'addr', 'mywallet', 'portfolio']:
        return {'type': 'wallet'}
        
    intent = None
    if low.startswith('pay ') or low.startswith('send ') or low.startswith('transfer '):
        intent = 'pay'
        q = re.sub(r'^(pay|send|transfer)\s+', '', q, flags=re.IGNORECASE).strip()
    elif low.startswith('cheque ') or low.startswith('check ') or low.startswith('drop '):
        intent = 'cheque'
        q = re.sub(r'^(cheque|check|drop)\s+', '', q, flags=re.IGNORECASE).strip()
    elif low.startswith('invoice ') or low.startswith('request ') or low.startswith('bill '):
        intent = 'invoice'
        q = re.sub(r'^(invoice|request|bill)\s+', '', q, flags=re.IGNORECASE).strip()
    elif low.startswith('giveaway ') or low.startswith('gw '):
        intent = 'cheque'
        q = re.sub(r'^(giveaway|gw)\s+', '', q, flags=re.IGNORECASE).strip()

    tokens = q.split()
    target_user = None
    rem_tokens = []
    for t in tokens:
        if t.startswith('@') and len(t) > 1 and not target_user:
            target_user = t.lstrip('@')
        else:
            rem_tokens.append(t)
            
    amount = None
    currency = 'USDT'
    winners = 1
    note_words = []
    
    for t in rem_tokens:
        clean_num = t.replace('$', '').replace('€', '').replace(',', '')
        try:
            val = float(clean_num)
            if amount is None:
                amount = val
                continue
            elif winners == 1 and val.is_integer() and int(val) > 0 and intent == 'cheque':
                winners = int(val)
                continue
        except ValueError:
            pass
            
        upper_t = t.upper()
        if upper_t in config.SUPPORTED_CRYPTOS:
            currency = upper_t
            continue
            
        note_words.append(t)
        
    if amount is None:
        amount = 10.0
        
    note = " ".join(note_words).strip()
    
    return {
        'type': intent or ('pay' if target_user else 'multi'),
        'amount': amount,
        'currency': currency,
        'target': target_user,
        'winners': winners,
        'note': note
    }

@bot.inline_handler(func=lambda query: True)
def handle_inline_queries(query):
    user_id = query.from_user.id
    user = db.get_or_create_user(user_id, query.from_user.username, query.from_user.first_name)
    q = query.query.strip()
    sender_tag = f"@{query.from_user.username or query.from_user.first_name}"
    
    bal_usdt = db.get_balance(user_id, 'USDT')
    bal_trx = db.get_balance(user_id, 'TRX')
    bal_trappy = db.get_balance(user_id, 'TRAPPY')
    tot_usd = bal_usdt * 1.0 + bal_trx * 0.16 + bal_trappy * 0.25
    
    parsed = parse_inline_query_intent(q)
    results = []
    
    # 1. When empty: Show live wallet balance, quick cheque, invoice, addresses
    if parsed['type'] == 'empty':
        results.append(
            InlineQueryResultArticle(
                id=f"iw_{user_id}",
                title="👛 My Testnet Wallet & Balances",
                description=f"USDT: {bal_usdt:,.2f} | TRX: {bal_trx:,.2f} | TRAPPY: {bal_trappy:,.2f} (${tot_usd:,.2f})",
                reply_markup=kb.get_wallet_inline_keyboard(webapp_url=config.get_mini_app_url(user_id)),
                input_message_content=InputTextMessageContent(
                    message_text=render_wallet_text(user_id),
                    parse_mode="HTML"
                )
            )
        )
        ch10_id = f"c_{secrets.token_hex(4)}"
        results.append(
            InlineQueryResultArticle(
                id=f"ich_10.0_USDT_1_{ch10_id}",
                title="✉️ Send 10 USDT Cheque",
                description="Drop a claimable 10 USDT cheque into this chat or DM",
                reply_markup=kb.get_cheque_claim_inline(ch10_id),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>10.00 USDT</b>\n"
                        f"👤 <b>Creator:</b> {sender_tag}\n\n"
                        "Tap the button below to claim this cheque into your wallet!"
                    ),
                    parse_mode="HTML"
                )
            )
        )
        chtr_id = f"c_{secrets.token_hex(4)}"
        results.append(
            InlineQueryResultArticle(
                id=f"ich_1000.0_TRAPPY_1_{chtr_id}",
                title="⚡ Send 1,000 TRAPPY Cheque",
                description="Drop a claimable 1,000 TRAPPY cheque into this chat or DM",
                reply_markup=kb.get_cheque_claim_inline(chtr_id),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>1,000.00 TRAPPY</b>\n"
                        f"👤 <b>Creator:</b> {sender_tag}\n\n"
                        "Tap the button below to claim this cheque into your wallet!"
                    ),
                    parse_mode="HTML"
                )
            )
        )
        iv25_id = f"iv_{secrets.token_hex(4)}"
        results.append(
            InlineQueryResultArticle(
                id=f"iiv_25.0_USDT_{iv25_id}",
                title="💳 Request 25 USDT (Invoice)",
                description="Request 25 USDT payment from the user in this chat or DM",
                reply_markup=kb.get_invoice_pay_inline(iv25_id, "25.00", "USDT"),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"💳 <b>PAYMENT INVOICE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>25.00 USDT</b>\n"
                        f"👤 <b>Pay to:</b> {sender_tag}\n\n"
                        "Tap the button below to pay this invoice."
                    ),
                    parse_mode="HTML"
                )
            )
        )
        results.append(
            InlineQueryResultArticle(
                id=f"iaddr_{user_id}",
                title="🔗 Share My Testnet Addresses",
                description=f"TRC-20: {user.get('tron_address', '')[:14]}... | Trappy: {user.get('trappy_address', '')[:14]}...",
                input_message_content=InputTextMessageContent(
                    message_text=render_wallet_text(user_id),
                    parse_mode="HTML"
                )
            )
        )
        bot.answer_inline_query(query.id, results, cache_time=1)
        return

    # 2. Wallet query
    if parsed['type'] == 'wallet':
        results.append(
            InlineQueryResultArticle(
                id=f"iw_{user_id}",
                title="👛 My Testnet Wallet & Balances",
                description=f"USDT: {bal_usdt:,.2f} | TRX: {bal_trx:,.2f} | TRAPPY: {bal_trappy:,.2f} (${tot_usd:,.2f})",
                reply_markup=kb.get_wallet_inline_keyboard(webapp_url=config.get_mini_app_url(user_id)),
                input_message_content=InputTextMessageContent(
                    message_text=render_wallet_text(user_id),
                    parse_mode="HTML"
                )
            )
        )
        results.append(
            InlineQueryResultArticle(
                id=f"iaddr_{user_id}",
                title="🔗 Share My Testnet Addresses",
                description=f"TRC-20: {user.get('tron_address', '')[:14]}... | Trappy: {user.get('trappy_address', '')[:14]}...",
                input_message_content=InputTextMessageContent(
                    message_text=render_wallet_text(user_id),
                    parse_mode="HTML"
                )
            )
        )
        bot.answer_inline_query(query.id, results, cache_time=1)
        return

    # 3. Dynamic queries: amount, currency, target, note, winners
    amt = parsed['amount']
    curr = parsed['currency']
    target = parsed['target']
    winners = parsed['winners']
    note = parsed['note']
    f_amt = format_crypto_amount(amt, curr)
    note_str = f"\n💬 <i>Note: {note}</i>" if note else ""

    if target:
        results.append(
            InlineQueryResultArticle(
                id=f"ipay_{amt}_{curr}_{target}_{secrets.token_hex(4)}",
                title=f"💸 Direct Pay: {f_amt} {curr} to @{target}",
                description=f"Transfer {f_amt} {curr} directly to @{target}" + (f" ({note})" if note else ""),
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("👛 Open Wallet", web_app=types.WebAppInfo(url=config.get_mini_app_url(user_id)))
                ),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"💸 <b>Trappy Testnet Transfer</b>\n\n"
                        f"From: {sender_tag}\n"
                        f"To: @{target}\n"
                        f"Amount: <b>{f_amt} {curr}</b>{note_str}\n"
                        f"Status: ✅ Instant Settlement"
                    ),
                    parse_mode="HTML"
                )
            )
        )

    ch_id = f"c_{secrets.token_hex(4)}"
    ch_title = f"✉️ Send Cheque: {f_amt} {curr}" + (f" ({winners} claims)" if winners > 1 else "")
    ch_desc = f"Claimable by recipient in this DM or chat" + (f" ({note})" if note else "")
    results.append(
        InlineQueryResultArticle(
            id=f"ich_{amt}_{curr}_{winners}_{ch_id}",
            title=ch_title,
            description=ch_desc,
            reply_markup=kb.get_cheque_claim_inline(ch_id, winners=winners),
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
                    f"💰 <b>Amount:</b> <b>{f_amt} {curr}</b>" + (f" (split between {winners} users)" if winners > 1 else "") + f"\n"
                    f"👤 <b>Creator:</b> {sender_tag}{note_str}\n\n"
                    "Tap the button below to claim this cheque into your wallet!"
                ),
                parse_mode="HTML"
            )
        )
    )

    iv_id = f"iv_{secrets.token_hex(4)}"
    iv_target_str = f" from @{target}" if target else ""
    results.append(
        InlineQueryResultArticle(
            id=f"iiv_{amt}_{curr}_{iv_id}",
            title=f"💳 Payment Request: {f_amt} {curr}{iv_target_str}",
            description=f"Request {f_amt} {curr} payment" + (f" ({note})" if note else ""),
            reply_markup=kb.get_invoice_pay_inline(iv_id, f_amt, curr),
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"💳 <b>PAYMENT INVOICE</b>\n\n"
                    f"💰 <b>Amount:</b> <b>{f_amt} {curr}</b>\n"
                    f"👤 <b>Pay to:</b> {sender_tag}{note_str}\n\n"
                    "Tap the button below to pay this invoice."
                ),
                parse_mode="HTML"
            )
        )
    )

    bot.answer_inline_query(query.id, results, cache_time=1)

@bot.chosen_inline_handler(func=lambda result: True)
def handle_chosen_inline(chosen):
    """Processes transfers, cheques, and invoices chosen via inline query"""
    try:
        sender_id = chosen.from_user.id
        db.get_or_create_user(sender_id, chosen.from_user.username, chosen.from_user.first_name)
        rid = chosen.result_id
        
        if rid.startswith("ich_"):
            parts = rid.split("_")
            amt = float(parts[1])
            curr = parts[2]
            winners = int(parts[3])
            ch_id = f"c_{parts[5]}" if len(parts) > 5 else parts[4]
            db.create_cheque(sender_id, curr, amt, winners_count=winners, custom_id=ch_id)
        elif rid.startswith("iiv_"):
            parts = rid.split("_")
            amt = float(parts[1])
            curr = parts[2]
            iv_id = f"iv_{parts[4]}" if len(parts) > 4 else parts[3]
            db.create_invoice(sender_id, curr, amt, custom_id=iv_id)
        elif rid.startswith("ipay_"):
            parts = rid.split("_")
            amt = float(parts[1])
            curr = parts[2]
            target_str = parts[3]
            target_user = db.find_user(target_str)
            if target_user:
                db.transfer_crypto(sender_id, target_user['user_id'], curr, amt)
    except Exception as e:
        logger.warning(f"Error handling chosen inline: {e}")

# ==============================================================================
# CALLBACK QUERY DISPATCHER
# ==============================================================================
def send_admin_dashboard(chat_id, message_id=None):
    stats = db.get_system_telemetry()
    circ = stats['circulating']
    txt = (
        "⚡ <b>MASTER ADMINISTRATION TERMINAL</b>\n"
        "<i>Authorized Operator: 9051090063</i>\n\n"
        "📊 <b>System Telemetry:</b>\n"
        f"• Registered Users: <b>{stats['users']}</b>\n"
        f"• Connected Channels: <b>{stats['channels']}</b>\n"
        f"• Active Cheques: <b>{stats['cheques']}</b> | Invoices: <b>{stats['invoices']}</b>\n\n"
        "💰 <b>Circulating Testnet Supply:</b>\n"
        f"• <b>USDT:</b> {circ['USDT']:,.2f} USDT\n"
        f"• <b>TRX:</b> {circ['TRX']:,.2f} TRX\n"
        f"• <b>TRAPPY:</b> {circ['TRAPPY']:,.2f} TRAPPY\n"
        f"• <b>Total Valuation:</b> ${stats['total_usd']:,.2f}\n\n"
        "Select an administrative module below to manage the ecosystem:"
    )
    if message_id:
        try:
            bot.edit_message_text(txt, chat_id=chat_id, message_id=message_id, reply_markup=kb.get_admin_main_inline())
            return
        except Exception:
            pass
    bot.send_message(chat_id, txt, reply_markup=kb.get_admin_main_inline())

def send_channel_paying_panel(channel_chat_id, admin_chat_id=None):
    chan = db.get_channel_gateway(channel_chat_id)
    title = chan.get('title', 'Channel') if chan else 'Channel'
    t_addr = db.generate_tron_address(abs(channel_chat_id) % 100000000)
    trp_addr = db.generate_trappy_address(abs(channel_chat_id) % 100000000)
    
    txt = (
        f"🎰 <b>{title.upper()} — PAYMENT & BETTING PANEL</b>\n"
        "<i>Automated Testnet Crypto Gateway</i>\n\n"
        "To participate, deposit, or place a bet:\n"
        "1️⃣ Tap an instant payment button below, or transfer testnet crypto.\n"
        "2️⃣ Include your bet / reference in the comment (e.g. <code>red 50</code>, <code>dice 100</code>).\n"
        "3️⃣ Your payment is verified instantly and broadcast live to this channel!\n\n"
        "💎 <b>Accepted Assets:</b> USDT (TRC-20), TRX, TRAPPY\n"
        "🏷️ <b>Channel TRC-20 Address:</b>\n"
        f"<code>{t_addr}</code>\n"
        "🏷️ <b>Channel Trappy Address:</b>\n"
        f"<code>{trp_addr}</code>"
    )
    try:
        sent = bot.send_message(
            channel_chat_id,
            txt,
            reply_markup=kb.get_channel_paying_panel_inline(channel_chat_id)
        )
        if admin_chat_id:
            bot.send_message(admin_chat_id, f"✅ Paying panel successfully deployed in <b>{title}</b>!")
        return sent
    except Exception as e:
        if admin_chat_id:
            bot.send_message(admin_chat_id, f"⚠️ Could not post to channel: {e}\nMake sure the bot has admin permission to post messages.")
        return None

def broadcast_channel_payment(channel_chat_id, sender_tag, amount_str, currency, comment):
    chan = db.get_channel_gateway(channel_chat_id)
    if chan and int(chan.get('message_after_pay', 1)) == 0:
        return  # Message-after-pay is disabled for this channel
        
    time_str = time.strftime("%H:%M:%S UTC")
    comm_str = f"<i>\"{comment}\"</i>" if comment and comment.lower() != 'skip' else "<i>None</i>"
    receipt_txt = (
        "🎰 <b>LIVE PAYMENT BROADCAST</b>\n\n"
        f"👤 <b>From:</b> {sender_tag}\n"
        f"💰 <b>Amount:</b> <b>{amount_str} {currency}</b>\n"
        f"💬 <b>Comment:</b> {comm_str}\n"
        f"⏰ <b>Time:</b> {time_str}\n"
        "✅ <b>Status:</b> Confirmed Testnet Transaction"
    )
    try:
        bot.send_message(channel_chat_id, receipt_txt)
    except Exception as e:
        logger.warning(f"Could not broadcast channel payment to {channel_chat_id}: {e}")

# ==============================================================================
# CALLBACK QUERY DISPATCHER
# ==============================================================================
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    db.get_or_create_user(user_id, call.from_user.username, call.from_user.first_name)

    # --------------------------------------------------------------------------
    # Basic Navigation
    # --------------------------------------------------------------------------
    if data in ["action_wallet", "action_back_main"]:
        bot.answer_callback_query(call.id)
        text = render_wallet_text(user_id)
        try:
            bot.edit_message_text(
                text=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=kb.get_wallet_inline_keyboard()
            )
        except Exception:
            send_wallet_message(call.message.chat.id, user_id)

    elif data == "action_deposit":
        bot.answer_callback_query(call.id)
        user = db.get_user(user_id)
        t_addr = user.get('tron_address') or db.generate_tron_address(user_id)
        trp_addr = user.get('trappy_address') or db.generate_trappy_address(user_id)
        txt = (
            "📥 <b>Deposit Testnet Crypto</b>\n\n"
            "Share your receiving address with the sender or administrator to receive testnet funds:\n\n"
            f"• <b>TRC-20 Address (USDT / TRX):</b>\n<code>{t_addr}</code>\n\n"
            f"• <b>Trappy Native Address (TRAPPY):</b>\n<code>{trp_addr}</code>\n\n"
            "<i>Note: Public faucet claims are disabled. Allocations are granted directly by the administrator or via cheques and invoices.</i>"
        )
        bot.edit_message_text(
            text=txt,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=kb.get_deposit_inline_keyboard()
        )

    elif data == "action_withdraw":
        bot.answer_callback_query(call.id)
        txt = (
            "📤 <b>Send / Transfer Testnet Crypto</b>\n\n"
            "You can transfer testnet coins to any Telegram user, realistic crypto address, or wallet ID!\n\n"
            "<b>Quick Formats:</b>\n"
            "• By username: <code>$10 @username [comment]</code>\n"
            "• By command: <code>/pay @username 50 USDT [comment]</code>\n"
            "• By TRC-20 address: <code>/pay TRmz... 50 USDT</code>\n"
            "• By Trappy address: <code>/pay trp1... 500 TRAPPY</code>"
        )
        bot.edit_message_text(
            text=txt,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=kb.get_withdraw_inline_keyboard()
        )

    elif data == "send_by_username":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_pay_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter transfer details:</b>\nFormat: <code>@username amount CURRENCY [comment]</code>\nExample: <code>@username 50 USDT For lunch</code>"
        )

    elif data == "send_by_address":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_pay_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter address transfer details:</b>\nFormat: <code>&lt;address&gt; &lt;amount&gt; &lt;CURRENCY&gt; [comment]</code>\nExample: <code>TRmzNV2HxSAdRDmQyahqvGrJS8vFPeHkUh 50 USDT</code>"
        )

    elif data == "send_by_wallet_id":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_pay_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter transfer details:</b>\nFormat: <code>TRP-xxxx amount CURRENCY [comment]</code>\nExample: <code>TRP-9051-A1 50 USDT</code>"
        )

    # --------------------------------------------------------------------------
    # Interactive Cheques & Invoices Menus
    # --------------------------------------------------------------------------
    elif data == "action_cheque_prompt":
        bot.answer_callback_query(call.id)
        txt = (
            "✉️ <b>Create a Testnet Cheque</b>\n\n"
            "Issue a claimable crypto cheque. Select an instant amount below or specify custom winners and comments:"
        )
        try:
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_cheque_menu_inline())
        except Exception:
            bot.send_message(call.message.chat.id, txt, reply_markup=kb.get_cheque_menu_inline())

    elif data.startswith("ch_preset_"):
        bot.answer_callback_query(call.id)
        parts = data.replace("ch_preset_", "").split("_")
        amt_str, curr = parts[0], parts[1]
        execute_create_cheque(call.message, user_id, amt_str, curr, "1", "Instant Cheque")

    elif data == "ch_custom_prompt":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_cheque_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter Cheque Details:</b>\nFormat: <code>&lt;amount&gt; &lt;CURRENCY&gt; [winners] [comment]</code>\nExample: <code>50 USDT 1 For lunch</code>\nor: <code>1000 TRAPPY 5 Community Drop</code>"
        )

    elif data == "action_invoice_prompt":
        bot.answer_callback_query(call.id)
        txt = (
            "💳 <b>Create a Payment Invoice</b>\n\n"
            "Request testnet crypto from any user. Choose an instant amount below or enter custom details:"
        )
        try:
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_invoice_menu_inline())
        except Exception:
            bot.send_message(call.message.chat.id, txt, reply_markup=kb.get_invoice_menu_inline())

    elif data.startswith("iv_preset_"):
        bot.answer_callback_query(call.id)
        parts = data.replace("iv_preset_", "").split("_")
        amt_str, curr = parts[0], parts[1]
        execute_create_invoice(call.message, user_id, amt_str, curr, "Payment Request")

    elif data == "iv_custom_prompt":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_invoice_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter Invoice Details:</b>\nFormat: <code>&lt;amount&gt; &lt;CURRENCY&gt; [description]</code>\nExample: <code>25 USDT For coffee</code>\nor: <code>500 TRAPPY Web service fee</code>"
        )

    elif data.startswith("claim_ch_"):
        ch_id = data.replace("claim_ch_", "")
        execute_claim_cheque(user_id, ch_id, call.message.chat.id, call=call)

    elif data.startswith("pay_iv_"):
        iv_id = data.replace("pay_iv_", "")
        execute_pay_invoice(call.message, user_id, iv_id, call=call)

    elif data.startswith("claim_gw_"):
        gw_id = data.replace("claim_gw_", "")
        execute_claim_giveaway(user_id, gw_id, call.message.chat.id, call=call)

    elif data == "action_close_card":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # Channel Gateway & Paying Panel
    # --------------------------------------------------------------------------
    elif data.startswith("chan_deploy_panel_"):
        bot.answer_callback_query(call.id, "Deploying Paying Panel...", show_alert=False)
        chan_id = int(data.replace("chan_deploy_panel_", ""))
        send_channel_paying_panel(chan_id, admin_chat_id=call.message.chat.id)

    elif data.startswith("chan_settings_"):
        bot.answer_callback_query(call.id)
        chan_id = int(data.replace("chan_settings_", ""))
        chan = db.get_channel_gateway(chan_id)
        map_val = chan.get('message_after_pay', 1) if chan else 1
        txt = (
            "⚙️ <b>Channel Gateway Settings</b>\n\n"
            f"Channel: <b>{chan.get('title', 'Channel') if chan else chan_id}</b>\n"
            "• <b>Message-after-Pay:</b> When enabled, any payment made with a comment is automatically broadcast live to this channel.\n\n"
            "Toggle settings below:"
        )
        bot.send_message(call.message.chat.id, txt, reply_markup=kb.get_channel_gateway_settings_inline(chan_id, map_val))

    elif data.startswith("chan_toggle_map_"):
        chan_id = int(data.replace("chan_toggle_map_", ""))
        new_val = db.toggle_channel_message_after_pay(chan_id)
        status_txt = "ENABLED (ON ✅)" if new_val == 1 else "DISABLED (OFF ❌)"
        bot.answer_callback_query(call.id, f"Message-after-Pay is now {status_txt}", show_alert=True)
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb.get_channel_gateway_settings_inline(chan_id, new_val))
        except Exception:
            pass

    elif data.startswith("cpay_custom_"):
        chan_id = int(data.replace("cpay_custom_", ""))
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_chan_custom_pay', 'channel_id': chan_id}
        bot.send_message(
            user_id,
            "✍️ <b>Enter Payment Details for Channel Deposit:</b>\nFormat: <code>&lt;amount&gt; &lt;CURRENCY&gt; [comment / bet]</code>\nExample: <code>50 USDT red 50</code>"
        )

    elif data.startswith("cpay_"):
        # Format: cpay_{channel_id}_{amt}_{curr}
        parts = data.split("_")
        chan_id = int(parts[1])
        amt_str = parts[2]
        curr = parts[3]
        bot.answer_callback_query(call.id)
        
        user_states[user_id] = {
            'action': 'waiting_chan_pay_comment',
            'channel_id': chan_id,
            'amount': amt_str,
            'currency': curr
        }
        chan = db.get_channel_gateway(chan_id)
        chan_title = chan.get('title', 'Channel') if chan else 'the channel'
        bot.send_message(
            user_id,
            f"🎰 <b>Payment of {amt_str} {curr} to {chan_title}</b>\n\n"
            "✍️ <b>Enter your payment / bet comment:</b>\n"
            "Example: <code>red 50</code>, <code>dice 100</code>, or type <code>skip</code> to send without comment."
        )

    # --------------------------------------------------------------------------
    # Master Admin Terminal Callbacks (ID: 9051090063)
    # --------------------------------------------------------------------------
    elif data.startswith("adm_"):
        if user_id != 9051090063:
            bot.answer_callback_query(call.id, "Unauthorized.", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        
        if data == "adm_home":
            send_admin_dashboard(call.message.chat.id, message_id=call.message.message_id)

        elif data == "adm_leaderboard":
            top = db.get_top_richest_users(10)
            txt = "🏆 <b>RICHEST USERS LEADERBOARD</b>\n<i>Real-time USD Valuation</i>\n\n"
            for i, u in enumerate(top):
                uname = f"@{u['username']}" if u.get('username') else u.get('first_name', str(u['user_id']))
                txt += (
                    f"<b>#{i+1} {uname}</b> (<code>{u['user_id']}</code>)\n"
                    f"• USDT: {u['balances']['USDT']:,.1f} | TRX: {u['balances']['TRX']:,.1f} | TRAPPY: {u['balances']['TRAPPY']:,.1f}\n"
                    f"• Valuation: <b>${u['total_usd']:,.2f}</b>\n\n"
                )
            txt += "Tap any user below to inspect or grant/deduct funds:"
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_leaderboard_inline(top))

        elif data.startswith("adm_users_"):
            page = int(data.replace("adm_users_", ""))
            users, total_cnt, total_pages = db.get_all_users_paginated(page, 8)
            txt = f"👥 <b>USERS DIRECTORY</b> (Total: {total_cnt})\nPage {page} of {total_pages}\n\n"
            for u in users:
                uname = f"@{u['username']}" if u.get('username') else u.get('first_name', str(u['user_id']))
                txt += f"• <b>{uname}</b> (<code>{u['user_id']}</code>) — <b>${u['total_usd']:,.2f}</b>\n"
            txt += "\nSelect a user to inspect or adjust balances:"
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_users_list_inline(users, page, total_pages))

        elif data.startswith("adm_inspect_"):
            target_id = int(data.replace("adm_inspect_", ""))
            target_user = db.get_user(target_id)
            if not target_user:
                bot.send_message(call.message.chat.id, "User not found.")
                return
            bals = db.get_all_balances(target_id)
            tot_usd = bals.get('USDT', 0)*1.0 + bals.get('TRX', 0)*0.16 + bals.get('TRAPPY', 0)*0.25
            uname = f"@{target_user['username']}" if target_user.get('username') else "None"
            txt = (
                f"👤 <b>USER DOSSIER: {target_user.get('first_name', 'User')}</b>\n\n"
                f"• <b>Telegram ID:</b> <code>{target_id}</code>\n"
                f"• <b>Username:</b> {uname}\n"
                f"• <b>Wallet ID:</b> <code>{target_user.get('wallet_id', '')}</code>\n"
                f"• <b>TRC-20 Address:</b>\n<code>{target_user.get('tron_address', '')}</code>\n"
                f"• <b>Trappy Native Address:</b>\n<code>{target_user.get('trappy_address', '')}</code>\n\n"
                f"💰 <b>Current Balances:</b>\n"
                f"• USDT: <b>{format_crypto_amount(bals.get('USDT', 0), 'USDT')}</b>\n"
                f"• TRX: <b>{format_crypto_amount(bals.get('TRX', 0), 'TRX')}</b>\n"
                f"• TRAPPY: <b>{format_crypto_amount(bals.get('TRAPPY', 0), 'TRAPPY')}</b>\n"
                f"• Total USD: <b>${tot_usd:,.2f}</b>\n\n"
                "Select an administrative action:"
            )
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_user_manage_inline(target_id))

        elif data.startswith("adm_grant_"):
            # Format: adm_grant_{user_id}_{curr}
            parts = data.split("_")
            t_id = int(parts[2])
            curr = parts[3]
            txt = f"➕ <b>Grant {curr} to User <code>{t_id}</code></b>\nChoose preset amount or tap Custom:"
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_grant_presets_inline(t_id, curr))

        elif data.startswith("adm_exec_grant_"):
            # Format: adm_exec_grant_{user_id}_{curr}_{amount}
            parts = data.split("_")
            t_id = int(parts[3])
            curr = parts[4]
            amt = float(parts[5])
            ok, new_bal = db.admin_add_crypto(t_id, curr, amt)
            famt = format_crypto_amount(amt, curr)
            bot.answer_callback_query(call.id, f"Granted +{famt} {curr}!", show_alert=True)
            # Notify target user
            try:
                bot.send_message(t_id, f"🎉 <b>Testnet Crypto Received!</b>\nYou received <b>+{famt} {curr}</b> from the Administrator!")
            except Exception:
                pass
            # Refresh inspection
            bals = db.get_all_balances(t_id)
            tot_usd = bals.get('USDT', 0)*1.0 + bals.get('TRX', 0)*0.16 + bals.get('TRAPPY', 0)*0.25
            target_user = db.get_user(t_id)
            txt = (
                f"✅ <b>Successfully granted +{famt} {curr}!</b>\n\n"
                f"👤 <b>User <code>{t_id}</code> Updated Balances:</b>\n"
                f"• USDT: <b>{bals.get('USDT', 0):,.2f}</b>\n"
                f"• TRX: <b>{bals.get('TRX', 0):,.2f}</b>\n"
                f"• TRAPPY: <b>{bals.get('TRAPPY', 0):,.2f}</b>\n"
                f"• Total USD: <b>${tot_usd:,.2f}</b>"
            )
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_user_manage_inline(t_id))

        elif data.startswith("adm_custom_grant_"):
            parts = data.split("_")
            t_id = int(parts[3])
            curr = parts[4]
            user_states[9051090063] = {'action': 'admin_custom_grant', 'target_id': t_id, 'currency': curr}
            bot.send_message(call.message.chat.id, f"✍️ <b>Enter custom amount of {curr} to grant to User <code>{t_id}</code>:</b>")

        elif data.startswith("adm_deduct_"):
            t_id = int(data.replace("adm_deduct_", ""))
            user_states[9051090063] = {'action': 'admin_custom_deduct', 'target_id': t_id}
            bot.send_message(call.message.chat.id, f"✍️ <b>Enter amount and currency to deduct from User <code>{t_id}</code>:</b>\nExample: <code>100 USDT</code> or <code>5000 TRAPPY</code>")

        elif data.startswith("adm_reset_"):
            t_id = int(data.replace("adm_reset_", ""))
            db.admin_reset_user_balances(t_id)
            bot.answer_callback_query(call.id, f"Zeroed out balances for User {t_id}!", show_alert=True)
            # Refresh inspection
            target_user = db.get_user(t_id)
            txt = f"🔄 <b>All balances zeroed out for User <code>{t_id}</code>.</b>"
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_user_manage_inline(t_id))

        elif data.startswith("adm_user_cheque_"):
            t_id = int(data.replace("adm_user_cheque_", ""))
            user_states[9051090063] = {'action': 'admin_custom_master_cheque', 'note': f"Direct allocation for {t_id}"}
            bot.send_message(call.message.chat.id, f"✍️ <b>Enter cheque amount and currency for User <code>{t_id}</code>:</b>\nExample: <code>500 USDT</code>")

        elif data == "adm_master_cheque":
            txt = (
                "✉️ <b>ISSUE FORWARDABLE MASTER CHEQUE</b>\n\n"
                "As administrator, you can issue cheques of ANY amount without deduction.\n"
                "Select a preset amount below or create a custom multi-claim cheque:"
            )
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb.get_admin_master_cheque_menu())

        elif data.startswith("adm_mch_exec_"):
            # Format: adm_mch_exec_{curr}_{amount}
            parts = data.split("_")
            curr = parts[3]
            amt = float(parts[4])
            ok, ch_id = db.create_master_cheque(curr, amt, winners_count=1, note="Official Master Cheque")
            famt = format_crypto_amount(amt, curr)
            deep_link = f"https://t.me/{config.BOT_USERNAME}?start=c_{ch_id}"
            
            txt = (
                "✉️ <b>TRAPPY TESTNET MASTER CHEQUE</b>\n\n"
                f"💰 <b>Amount:</b> <b>{famt} {curr}</b>\n"
                "👥 <b>Winners:</b> 1 user\n"
                "💬 <i>Note: Official Master Cheque</i>\n\n"
                f"🔗 <b>Claim Link:</b> {deep_link}\n\n"
                "<i>You can forward this cheque message to any channel, group, or chat for users to claim!</i>"
            )
            bot.send_message(call.message.chat.id, txt, reply_markup=kb.get_cheque_claim_inline(ch_id))

        elif data == "adm_mch_custom":
            user_states[9051090063] = {'action': 'admin_custom_master_cheque'}
            bot.send_message(
                call.message.chat.id,
                "✍️ <b>Enter Master Cheque Details:</b>\nFormat: <code>&lt;amount&gt; &lt;CURRENCY&gt; [winners] [comment]</code>\nExample: <code>10000 USDT 10 Community Drop</code>"
            )

        elif data == "adm_search_user":
            user_states[9051090063] = {'action': 'admin_search_user'}
            bot.send_message(call.message.chat.id, "🔍 <b>Enter Telegram ID, @username, or TRC-20 / Trappy address to inspect:</b>")

        elif data == "adm_quick_grant":
            user_states[9051090063] = {'action': 'admin_quick_grant_prompt'}
            bot.send_message(call.message.chat.id, "✍️ <b>Enter user and grant amount:</b>\nFormat: <code>@username amount CURRENCY</code>\nExample: <code>@alice 500 USDT</code>")

        elif data == "adm_channels":
            chans = db.get_active_channels()
            txt = f"🎰 <b>CONNECTED CHANNELS</b> (Total: {len(chans)})\n\n"
            for c in chans:
                uname = f"@{c['username']}" if c.get('username') else "Private"
                txt += f"• <b>{c.get('title', 'Channel')}</b> ({uname}) — ID: <code>{c['chat_id']}</code>\n"
            txt += "\nSend <code>/channel_panel</code> in any connected channel to post the Paying Panel."
            bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("< Back to Admin Terminal", callback_data="adm_home")))

        elif data == "adm_broadcast":
            user_states[9051090063] = {'action': 'admin_broadcast_msg'}
            bot.send_message(call.message.chat.id, "📢 <b>Enter broadcast message to send to all registered users:</b>")

        elif data == "adm_lock":
            user_states[9051090063] = {}
            bot.edit_message_text("🔒 <b>Administrator Terminal Locked.</b>\nSend <code>admin</code> and verify passphrase to re-enter.", chat_id=call.message.chat.id, message_id=call.message.message_id)

        elif data == "adm_noop":
            pass

# ==============================================================================
# GENERAL TEXT MESSAGE HANDLER & ADMIN TRIGGER
# ==============================================================================
@bot.message_handler(content_types=['text'])
def handle_all_text_messages(message):
    text = (message.text or '').strip()
    if not text:
        return
    sender_id, sender_username, sender_name = get_message_sender(message)
    db.get_or_create_user(sender_id, sender_username, sender_name)

    # 1. SECRET ADMIN TRIGGER FOR ID 9051090063: Plaintext "admin"
    if sender_id == 9051090063 and text.lower() == "admin":
        user_states[9051090063] = {'action': 'waiting_admin_password'}
        bot.send_message(
            message.chat.id,
            "🔐 <b>Administrator Authentication Gate</b>\nPlease enter the security passphrase to unlock the management terminal:"
        )
        return

    # 2. Check for waiting states
    state_obj = user_states.get(sender_id, {})
    action = state_obj.get('action')

    # Admin Passphrase Verification
    if sender_id == 9051090063 and action == 'waiting_admin_password':
        if text == "son999":
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass
            user_states[9051090063] = {'admin_auth': True}
            send_admin_dashboard(message.chat.id)
        else:
            bot.send_message(message.chat.id, "❌ <b>Access Denied:</b> Incorrect security passphrase.")
            user_states[9051090063] = {}
        return

    # Admin Search User
    if sender_id == 9051090063 and action == 'admin_search_user':
        user_states[9051090063] = {'admin_auth': True}
        found = db.find_user(text)
        if found:
            t_id = found['user_id']
            bals = db.get_all_balances(t_id)
            tot_usd = bals.get('USDT', 0)*1.0 + bals.get('TRX', 0)*0.16 + bals.get('TRAPPY', 0)*0.25
            uname = f"@{found['username']}" if found.get('username') else "None"
            txt = (
                f"👤 <b>USER DOSSIER: {found.get('first_name', 'User')}</b>\n\n"
                f"• <b>Telegram ID:</b> <code>{t_id}</code>\n"
                f"• <b>Username:</b> {uname}\n"
                f"• <b>TRC-20 Address:</b>\n<code>{found.get('tron_address', '')}</code>\n"
                f"• <b>Trappy Native Address:</b>\n<code>{found.get('trappy_address', '')}</code>\n\n"
                f"💰 <b>Current Balances:</b>\n"
                f"• USDT: <b>{format_crypto_amount(bals.get('USDT', 0), 'USDT')}</b>\n"
                f"• TRX: <b>{format_crypto_amount(bals.get('TRX', 0), 'TRX')}</b>\n"
                f"• TRAPPY: <b>{format_crypto_amount(bals.get('TRAPPY', 0), 'TRAPPY')}</b>\n"
                f"• Total USD: <b>${tot_usd:,.2f}</b>"
            )
            bot.send_message(message.chat.id, txt, reply_markup=kb.get_admin_user_manage_inline(t_id))
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{text}</code> not found.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("< Back to Admin Terminal", callback_data="adm_home")))
        return

    # Admin Custom Grant
    if sender_id == 9051090063 and action == 'admin_custom_grant':
        t_id = state_obj.get('target_id')
        curr = state_obj.get('currency', 'USDT')
        user_states[9051090063] = {'admin_auth': True}
        try:
            amt = float(text.replace('$', '').strip())
            ok, new_bal = db.admin_add_crypto(t_id, curr, amt)
            famt = format_crypto_amount(amt, curr)
            bot.send_message(message.chat.id, f"✅ Successfully granted <b>+{famt} {curr}</b> to User <code>{t_id}</code>!")
            try:
                bot.send_message(t_id, f"🎉 <b>Testnet Crypto Received!</b>\nYou received <b>+{famt} {curr}</b> from the Administrator!")
            except Exception:
                pass
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Invalid amount: {e}")
        return

    # Admin Quick Grant (e.g. @user 500 USDT)
    if sender_id == 9051090063 and action == 'admin_quick_grant_prompt':
        user_states[9051090063] = {'admin_auth': True}
        parts = text.split()
        if len(parts) >= 3:
            target_str = parts[0]
            amt_str = parts[1]
            curr = parts[2].upper()
            target_user = db.find_user(target_str)
            if target_user:
                t_id = target_user['user_id']
                try:
                    amt = float(amt_str)
                    ok, new_bal = db.admin_add_crypto(t_id, curr, amt)
                    famt = format_crypto_amount(amt, curr)
                    bot.send_message(message.chat.id, f"✅ Successfully granted <b>+{famt} {curr}</b> to @{target_user.get('username') or t_id}!")
                    try:
                        bot.send_message(t_id, f"🎉 <b>Testnet Crypto Received!</b>\nYou received <b>+{famt} {curr}</b> from the Administrator!")
                    except Exception:
                        pass
                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Invalid amount: {e}")
            else:
                bot.send_message(message.chat.id, f"❌ User {target_str} not found.")
        else:
            bot.send_message(message.chat.id, "❌ Format: <code>@username amount CURRENCY</code>")
        return

    # Admin Custom Deduct
    if sender_id == 9051090063 and action == 'admin_custom_deduct':
        t_id = state_obj.get('target_id')
        user_states[9051090063] = {'admin_auth': True}
        parts = text.split()
        if len(parts) >= 2:
            amt_str, curr_raw = parts[0], parts[1].upper()
            try:
                amt = float(amt_str)
                ok, new_bal = db.admin_deduct_crypto(t_id, curr_raw, amt)
                bot.send_message(message.chat.id, f"✅ Deducted {amt} {curr_raw} from User {t_id}. New balance: {new_bal}")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Error: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Expected format: <code>amount CURRENCY</code>")
        return

    # Admin Custom Master Cheque
    if sender_id == 9051090063 and action == 'admin_custom_master_cheque':
        user_states[9051090063] = {'admin_auth': True}
        parts = text.split()
        if len(parts) >= 2:
            amt_str = parts[0]
            curr = parts[1].upper()
            win_str = parts[2] if len(parts) > 2 and parts[2].isdigit() else "1"
            note = " ".join(parts[3:]) if len(parts) > 3 else (state_obj.get('note') or "Official Master Cheque")
            try:
                amt = float(amt_str)
                winners = int(win_str)
                ok, ch_id = db.create_master_cheque(curr, amt, winners_count=winners, note=note)
                famt = format_crypto_amount(amt, curr)
                deep_link = f"https://t.me/{config.BOT_USERNAME}?start=c_{ch_id}"
                txt = (
                    "✉️ <b>TRAPPY TESTNET MASTER CHEQUE</b>\n\n"
                    f"💰 <b>Amount:</b> <b>{famt} {curr}</b>\n"
                    f"👥 <b>Winners:</b> {winners} user(s)\n"
                    f"💬 <i>Note: {note}</i>\n\n"
                    f"🔗 <b>Claim Link:</b> {deep_link}\n\n"
                    "<i>Forward this cheque to any channel or group for users to claim!</i>"
                )
                bot.send_message(message.chat.id, txt, reply_markup=kb.get_cheque_claim_inline(ch_id, claimed=0, winners=winners))
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Invalid cheque parameters: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Format: <code>amount CURRENCY [winners] [note]</code>")
        return

    # Admin Broadcast Message
    if sender_id == 9051090063 and action == 'admin_broadcast_msg':
        user_states[9051090063] = {'admin_auth': True}
        users, tot, _ = db.get_all_users_paginated(1, 1000)
        sent_cnt = 0
        for u in users:
            try:
                bot.send_message(u['user_id'], f"📢 <b>ANNOUNCEMENT</b>\n\n{text}")
                sent_cnt += 1
            except Exception:
                pass
        bot.send_message(message.chat.id, f"✅ Broadcast sent to {sent_cnt} registered users!")
        return

    # Waiting Cheque Prompt (Regular User)
    if action == 'waiting_cheque_prompt':
        user_states[sender_id] = {}
        parts = text.split()
        if len(parts) >= 2:
            amt_str = parts[0]
            curr = parts[1]
            win_str = parts[2] if len(parts) > 2 and parts[2].isdigit() else "1"
            note = " ".join(parts[3:]) if len(parts) > 3 else ""
            execute_create_cheque(message, sender_id, amt_str, curr, win_str, note=note)
        else:
            bot.send_message(message.chat.id, "❌ Expected format: <code>amount CURRENCY [winners] [comment]</code>")
        return

    # Waiting Invoice Prompt (Regular User)
    if action == 'waiting_invoice_prompt':
        user_states[sender_id] = {}
        parts = text.split()
        if len(parts) >= 2:
            amt_str = parts[0]
            curr = parts[1]
            note = " ".join(parts[2:]) if len(parts) > 2 else ""
            execute_create_invoice(message, sender_id, amt_str, curr, note=note)
        else:
            bot.send_message(message.chat.id, "❌ Expected format: <code>amount CURRENCY [description]</code>")
        return

    # Waiting Payment Prompt (Regular User)
    if action == 'waiting_pay_prompt':
        user_states[sender_id] = {}
        parts = text.split()
        if len(parts) >= 3:
            target_str = parts[0]
            amt_str = parts[1]
            curr = parts[2]
            note = " ".join(parts[3:]) if len(parts) > 3 else ""
            execute_payment(message, sender_id, target_str, amt_str, curr, note=note)
        else:
            bot.send_message(message.chat.id, "❌ Expected format: <code>&lt;target&gt; &lt;amount&gt; &lt;CURRENCY&gt; [comment]</code>")
        return

    # Waiting Channel Payment Comment
    if action == 'waiting_chan_pay_comment':
        chan_id = state_obj.get('channel_id')
        amt_str = state_obj.get('amount')
        curr = state_obj.get('currency')
        user_states[sender_id] = {}
        comment = text if text.lower() != 'skip' else ""
        
        # Execute payment to channel
        chan = db.get_channel_gateway(chan_id)
        recipient_id = chan.get('added_by') if chan and chan.get('added_by') else config.OWNER_IDS[0]
        try:
            amt = float(amt_str)
        except ValueError:
            amt = 10.0
            
        ok, res = db.transfer_crypto(sender_id, recipient_id, curr, amt, note=comment)
        if ok:
            famt = format_crypto_amount(amt, curr)
            bot.send_message(
                message.chat.id,
                f"✅ <b>Payment Confirmed!</b>\nYou transferred <b>{famt} {curr}</b> to <b>{chan.get('title', 'Channel') if chan else 'Channel'}</b>!\n💬 Comment: <i>\"{comment or 'None'}\"</i>"
            )
            sender_tag = f"@{sender_username}" if sender_username else sender_name
            broadcast_channel_payment(chan_id, sender_tag, famt, curr, comment)
        else:
            if res == "insufficient_balance":
                bal = db.get_balance(sender_id, curr)
                bot.send_message(message.chat.id, f"❌ Insufficient balance! You have <b>{format_crypto_amount(bal, curr)} {curr}</b>.")
            else:
                bot.send_message(message.chat.id, f"❌ Payment failed: {res}")
        return

    # Waiting Channel Custom Payment
    if action == 'waiting_chan_custom_pay':
        chan_id = state_obj.get('channel_id')
        user_states[sender_id] = {}
        parts = text.split()
        if len(parts) >= 2:
            amt_str = parts[0]
            curr = parts[1].upper()
            comment = " ".join(parts[2:]) if len(parts) > 2 else ""
            chan = db.get_channel_gateway(chan_id)
            recipient_id = chan.get('added_by') if chan and chan.get('added_by') else config.OWNER_IDS[0]
            try:
                amt = float(amt_str)
                ok, res = db.transfer_crypto(sender_id, recipient_id, curr, amt, note=comment)
                if ok:
                    famt = format_crypto_amount(amt, curr)
                    bot.send_message(
                        message.chat.id,
                        f"✅ <b>Payment Confirmed!</b>\nYou sent <b>{famt} {curr}</b> to <b>{chan.get('title', 'Channel') if chan else 'Channel'}</b>!\n💬 Comment: <i>\"{comment or 'None'}\"</i>"
                    )
                    sender_tag = f"@{sender_username}" if sender_username else sender_name
                    broadcast_channel_payment(chan_id, sender_tag, famt, curr, comment)
                else:
                    if res == "insufficient_balance":
                        bal = db.get_balance(sender_id, curr)
                        bot.send_message(message.chat.id, f"❌ Insufficient balance! You have <b>{format_crypto_amount(bal, curr)} {curr}</b>.")
                    else:
                        bot.send_message(message.chat.id, f"❌ Payment failed: {res}")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Invalid amount: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Format: <code>amount CURRENCY [comment]</code>")
        return


@bot.message_handler(commands=['channel_panel'])
def handle_cmd_channel_panel(message):
    sender_id, _, _ = get_message_sender(message)
    chat = message.chat
    if chat.type in ['channel', 'supergroup', 'group']:
        send_channel_paying_panel(chat.id, admin_chat_id=sender_id)
    else:
        bot.send_message(
            message.chat.id,
            "💡 <b>Channel Paying Panel:</b>\nAdd this bot as an admin to your channel and run <code>/channel_panel</code> inside the channel, or tap the deploy button sent when the bot joined!"
        )

def main():
    logger.info("Starting Trappy Testnet Bot on Localhost...")
    print("==================================================================")
    print("      Trappy Testnet TELEGRAM CRYPTO BOT")
    print(f"      Bot Username: @{config.BOT_USERNAME}")
    print(f"      Official Channel: {config.OFFICIAL_CHANNEL}")
    print("      Assets: USDT, TRX, TRAPPY")
    print("      Channel & Group Integration: ACTIVE")
    print("==================================================================")
    
    ALLOWED_UPDATES = [
        'message',
        'edited_message',
        'channel_post',
        'edited_channel_post',
        'inline_query',
        'chosen_inline_result',
        'callback_query',
        'my_chat_member',
        'chat_member'
    ]
    
    while True:
        try:
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=20,
                skip_pending=True,
                allowed_updates=ALLOWED_UPDATES
            )
        except Exception as e:
            logger.error(f"Polling loop exception: {e}")
            time.sleep(3)

if __name__ == '__main__':
    main()
