# -*- coding: utf-8 -*-
"""
Trappy Testnet v1.1.5 - Main Telegram Bot
Multi-Asset (USDT, TRX, TRAPPY) with Telegram Mini App & Inline Mention Transfers
"""
import re
import time
import logging
import os
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
    def do_GET(self):
        if self.path in ['/', '/health', '/healthz']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            resp = json.dumps({
                "status": "healthy",
                "service": "trappy-testnet-bot",
                "version": "1.1.5",
                "assets": ["USDT", "TRX", "TRAPPY"]
            })
            self.wfile.write(resp.encode('utf-8'))
        else:
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
        user_url = f"{config.MINI_APP_URL}?wallet={user['wallet_id']}&usdt={balances.get('USDT', 0)}&trx={balances.get('TRX', 0)}&trappy={balances.get('TRAPPY', 0)}"
        
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
    if user.get('is_new'):
        welcome_text = (
            f"👋 <b>Welcome to Trappy Testnet, {first_name}!</b>\n\n"
            "Trappy is your personal testnet crypto wallet inside Telegram.\n"
            "Store, send, and create giveaways for testnet cryptocurrencies with zero fees and instant settlement.\n\n"
            f"🏷️ <b>Your Personal Address:</b>\n<code>{user['wallet_id']}</code>\n\n"
            "<b>Supported Assets:</b>\n"
            "• <b>Tether</b> (USDT)\n"
            "• <b>TRON</b> (TRX)\n"
            "• <b>Trappy</b> (TRAPPY) — Native Token\n\n"
            "To get started, tap <b>Deposit</b> below to claim your first free testnet coins or launch the <b>Wallet</b>!"
        )
        try:
            bot.send_message(
                chat_id=message.chat.id,
                text=welcome_text,
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
        "Create crypto cheques to send in DMs, group chats, or channels!\n\n"
        "📌 <b>Create a Cheque:</b>\n"
        "<code>/cheque &lt;amount&gt; &lt;currency&gt; [winners] [comment]</code>\n\n"
        "<b>Examples:</b>\n"
        "• Single cheque in DM: <code>/cheque 50 USDT For lunch</code>\n"
        "• Multi-user cheque: <code>/cheque 1000 TRAPPY 5</code>\n\n"
        "💡 <i>Tip: Type <code>@TrappyTestnetBot 50 USDT</code> in any DM to drop an instant cheque!</i>"
    )
    bot.send_message(message.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "💳 Invoices")
def handle_btn_invoices(message):
    txt = (
        "💳 <b>Trappy Testnet Invoices</b>\n\n"
        "Request testnet crypto from any Telegram user or in DMs.\n\n"
        "📌 <b>Create an Invoice:</b>\n"
        "<code>/invoice &lt;amount&gt; &lt;currency&gt; [description]</code>\n\n"
        "<b>Example:</b>\n"
        "<code>/invoice 25 USDT For coffee</code>\n\n"
        "💡 <i>Tip: Use inline mode in any DM to request a payment!</i>"
    )
    bot.send_message(message.chat.id, txt)

@bot.message_handler(func=lambda m: m.text in ["🎁 Giveaways", "🎁 Cheques / Giveaways"])
def handle_btn_giveaways(message):
    user_id, _, _ = get_message_sender(message)
    show_cheques_info(message.chat.id, user_id)

def show_cheques_info(chat_id, user_id):
    is_owner = user_id in config.OWNER_IDS
    owner_note = "\n\n👑 <b>Owner:</b> You have unlimited giveaway limits!" if is_owner else "\n\n⚠️ You can only giveaway crypto up to your wallet balance."
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
        "⚡ <b>Trappy Testnet v1.1.5</b>\n\n"
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

MENTION_WALLET_REGEX = re.compile(
    r'@(?:TrappyTestnetBot|TrappyTestnet|CryptoTestnetBot|trappytestnetbot|trappytestnet|trappy)\s+(?:wallet|balance)',
    re.IGNORECASE
)

@bot.message_handler(func=lambda m: bool(m.text and ('$' in m.text or any(alias in m.text.lower() for alias in config.BOT_ALIASES))))
def handle_bot_mentions(message):
    text = message.text.strip()
    sender_id, sender_username, sender_name = get_message_sender(message)
    db.get_or_create_user(sender_id, sender_username, sender_name)
    
    # 1. Matching Photo: @CryptoTestnetBot $10 @username Comment...
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
        
    # 3. Mention Giveaway: @TrappyTestnet giveaway 1000 TRAPPY 5
    m_gw = MENTION_GIVEAWAY_REGEX.search(text)
    if m_gw:
        amount_str, currency_raw, winners_str = m_gw.groups()
        execute_create_giveaway(message, sender_id, amount_str, currency_raw, winners_str)
        return
        
    # 4. Hidden Owner Addcrypto: @TrappyTestnet addcrypto @username 1000 USDT
    m_add = MENTION_ADDCRYPTO_REGEX.search(text)
    if m_add:
        target_str, amount_str, currency_raw = m_add.groups()
        execute_addcrypto(message, sender_id, target_str, amount_str, currency_raw)
        return
        
    # 5. Mention Wallet: @TrappyTestnet wallet
    if MENTION_WALLET_REGEX.search(text):
        send_wallet_message(message.chat.id, sender_id)
        return

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
    if not target_user:
        safe_reply(message, f"❌ Target user <code>@{target_str.lstrip('@')}</code> not found in Trappy Testnet. Ask them to start the bot first!")
        return
        
    to_user_id = target_user['user_id']
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
# INLINE QUERY ENGINE (CHEVRON, CHEQUES, INVOICES & DIRECT TRANSFERS)
# ==============================================================================
@bot.inline_handler(func=lambda query: True)
def handle_inline_queries(query):
    user_id = query.from_user.id
    user = db.get_or_create_user(user_id, query.from_user.username, query.from_user.first_name)
    q = query.query.strip()
    sender_tag = f"@{query.from_user.username or query.from_user.first_name}"
    
    results = []
    
    # 1. When query is empty: Real interactive quick actions for DMs & chats
    if not q:
        results.append(
            InlineQueryResultArticle(
                id="inline_cheque_usdt_10",
                title="✉️ Send 10 USDT Cheque",
                description="Drop a claimable 10 USDT cheque into this chat or DM",
                reply_markup=kb.get_cheque_claim_inline("c_quick_10_usdt"),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>10 USDT</b>\n"
                        f"👤 <b>Creator:</b> {sender_tag}\n\n"
                        "Tap the button below to claim this cheque into your wallet!"
                    ),
                    parse_mode="HTML"
                )
            )
        )
        results.append(
            InlineQueryResultArticle(
                id="inline_cheque_trappy_1000",
                title="⚡ Send 1,000 TRAPPY Cheque",
                description="Drop a claimable 1,000 TRAPPY cheque into this chat or DM",
                reply_markup=kb.get_cheque_claim_inline("c_quick_1000_trappy"),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>1,000 TRAPPY</b>\n"
                        f"👤 <b>Creator:</b> {sender_tag}\n\n"
                        "Tap the button below to claim this cheque into your wallet!"
                    ),
                    parse_mode="HTML"
                )
            )
        )
        results.append(
            InlineQueryResultArticle(
                id="inline_invoice_prompt",
                title="💳 Request 25 USDT (Invoice)",
                description="Request testnet payment from the user in this chat or DM",
                reply_markup=kb.get_invoice_pay_inline("iv_quick_25_usdt", "25", "USDT"),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"💳 <b>PAYMENT INVOICE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>25 USDT</b>\n"
                        f"👤 <b>Pay to:</b> {sender_tag}\n\n"
                        "Tap the button below to pay this invoice."
                    ),
                    parse_mode="HTML"
                )
            )
        )
        results.append(
            InlineQueryResultArticle(
                id="inline_wallet_share",
                title="👛 Share My Testnet Addresses",
                description=f"TRC-20: {user.get('tron_address', '')[:14]}... | Trappy: {user.get('trappy_address', '')[:14]}...",
                input_message_content=InputTextMessageContent(
                    message_text=render_wallet_text(user_id),
                    parse_mode="HTML"
                )
            )
        )
        bot.answer_inline_query(query.id, results, cache_time=1)
        return

    # 2. When query contains text: e.g. 50 USDT, $25, 1000 TRAPPY for dinner, 20 USDT @alex
    m_parse = re.match(r'^\$?([\d.]+)(?:\s+([a-zA-Z]+))?(?:\s+@?([a-zA-Z0-9_]{3,42}))?(?:\s+(.*))?', q)
    if m_parse:
        amt_str, curr_raw, target_raw, note_raw = m_parse.groups()
        try:
            amt = float(amt_str)
        except ValueError:
            amt = 10.0
            
        curr = (curr_raw or 'USDT').upper()
        if curr not in config.SUPPORTED_CRYPTOS:
            curr = 'USDT'
            
        note = note_raw or ""
        note_str = f"\n💬 <i>Note: {note}</i>" if note else ""
        f_amt = format_crypto_amount(amt, curr)

        # Cheque Option
        results.append(
            InlineQueryResultArticle(
                id=f"inline_ch_{amt}_{curr}",
                title=f"✉️ Send Cheque: {f_amt} {curr}",
                description=f"Claimable by recipient in this DM or chat" + (f" ({note})" if note else ""),
                reply_markup=kb.get_cheque_claim_inline(f"ch_{amt}_{curr}"),
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✉️ <b>TRAPPY TESTNET CHEQUE</b>\n\n"
                        f"💰 <b>Amount:</b> <b>{f_amt} {curr}</b>\n"
                        f"👤 <b>Creator:</b> {sender_tag}{note_str}\n\n"
                        "Tap the button below to claim this cheque into your wallet!"
                    ),
                    parse_mode="HTML"
                )
            )
        )

        # Invoice Option
        results.append(
            InlineQueryResultArticle(
                id=f"inline_iv_{amt}_{curr}",
                title=f"💳 Payment Request: {f_amt} {curr}",
                description=f"Request {f_amt} {curr} from the user in this DM" + (f" ({note})" if note else ""),
                reply_markup=kb.get_invoice_pay_inline(f"iv_{amt}_{curr}", f_amt, curr),
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

        # Direct Transfer Option (if target username specified)
        if target_raw:
            clean_target = target_raw.lstrip('@')
            results.append(
                InlineQueryResultArticle(
                    id=f"inline_pay_{amt}_{curr}_{clean_target}",
                    title=f"💸 Direct Pay: {f_amt} {curr} to @{clean_target}",
                    description=f"Transfer testnet {curr} directly to @{clean_target}",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("👛 Open Wallet", web_app=types.WebAppInfo(url=config.MINI_APP_URL))
                    ),
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"💸 <b>Trappy Testnet Transfer</b>\n\n"
                            f"From: {sender_tag}\n"
                            f"To: @{clean_target}\n"
                            f"Amount: <b>{f_amt} {curr}</b>{note_str}\n"
                            f"Status: ✅ Instant Settlement"
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
        
        if rid.startswith("inline_ch_"):
            parts = rid.split("_")
            amt = float(parts[2])
            curr = parts[3]
            db.create_cheque(sender_id, curr, amt, 1)
        elif rid.startswith("inline_iv_"):
            parts = rid.split("_")
            amt = float(parts[2])
            curr = parts[3]
            db.create_invoice(sender_id, curr, amt)
        elif rid.startswith("inline_pay_"):
            parts = rid.split("_")
            amt = float(parts[2])
            curr = parts[3]
            target_str = parts[4]
            target_user = db.find_user(target_str)
            if target_user:
                db.transfer_crypto(sender_id, target_user['user_id'], curr, amt)
    except Exception as e:
        logger.warning(f"Error handling chosen inline: {e}")

# ==============================================================================
# CALLBACK QUERY DISPATCHER
# ==============================================================================
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    db.get_or_create_user(user_id, call.from_user.username, call.from_user.first_name)
    
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
            "Share your receiving address to receive testnet coins, or tap a button below to claim from the faucet:\n\n"
            f"• <b>TRC-20 Address (USDT / TRX):</b>\n<code>{t_addr}</code>\n\n"
            f"• <b>Trappy Native Address (TRAPPY):</b>\n<code>{trp_addr}</code>\n\n"
            "Free Faucet Claims:"
        )
        bot.edit_message_text(
            text=txt,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=kb.get_deposit_inline_keyboard()
        )

    elif data.startswith("faucet_"):
        sym = data.replace("faucet_", "")
        success, reason, amt, mins = db.claim_faucet(user_id, sym)
        if success:
            famt = format_crypto_amount(amt, sym)
            bot.answer_callback_query(call.id, f"🎉 Received +{famt} {sym} testnet!", show_alert=True)
            text = render_wallet_text(user_id)
            try:
                bot.edit_message_text(
                    text=text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=kb.get_wallet_inline_keyboard()
                )
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, f"⏳ Cooldown active. Try again in {mins}m.", show_alert=True)

    elif data == "action_withdraw":
        bot.answer_callback_query(call.id)
        txt = (
            "📤 <b>Send / Transfer Testnet Crypto</b>\n\n"
            "You can transfer testnet coins to any Telegram user, realistic crypto address, or wallet ID!\n\n"
            "<b>Quick Formats:</b>\n"
            "• By username: <code>$10 @username</code>\n"
            "• By TRC20 address: <code>/pay TRmz... 50 USDT</code>\n"
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
            "✍️ <b>Enter transfer details:</b>\nFormat: <code>@username amount CURRENCY</code>\nExample: <code>@friend 100 USDT</code>"
        )

    elif data == "send_by_address":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_pay_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter address transfer details:</b>\nFormat: <code>&lt;address&gt; &lt;amount&gt; &lt;CURRENCY&gt;</code>\nExample:\n<code>TRmzNV2HxSAdRDmQyahqvGrJS8vFPeHkUh 50 USDT</code>\nor:\n<code>trp12727tjqmvgx9zrtm6qqj040t6l6jdp6v3enx86 1000 TRAPPY</code>"
        )

    elif data == "send_by_wallet_id":
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'action': 'waiting_pay_prompt'}
        bot.send_message(
            call.message.chat.id,
            "✍️ <b>Enter transfer details:</b>\nFormat: <code>TRP-xxxx amount CURRENCY</code>\nExample: <code>TRP-9051-A1B2 500 TRAPPY</code>"
        )

    elif data.startswith("claim_ch_"):
        ch_id = data.replace("claim_ch_", "")
        execute_claim_cheque(user_id, ch_id, call.message.chat.id, call)

    elif data.startswith("ch_done_"):
        bot.answer_callback_query(call.id, "This cheque has already completed!", show_alert=True)

    elif data.startswith("pay_iv_"):
        iv_id = data.replace("pay_iv_", "")
        execute_pay_invoice(user_id, iv_id, call)

    elif data.startswith("iv_done_"):
        bot.answer_callback_query(call.id, "This invoice is already paid!", show_alert=True)

    elif data.startswith("claim_gw_"):
        gw_id = data.replace("claim_gw_", "")
        execute_claim_giveaway(user_id, gw_id, call.message.chat.id, call)

    elif data.startswith("gw_done_"):
        bot.answer_callback_query(call.id, "This giveaway has already completed!", show_alert=True)

    # Hidden Owner Shortcuts
    elif data == "owner_quick_usdt" and user_id in config.OWNER_IDS:
        db.add_crypto(user_id, 'USDT', 10000.0)
        bot.answer_callback_query(call.id, "+10,000 USDT added!", show_alert=True)
    elif data == "owner_quick_trx" and user_id in config.OWNER_IDS:
        db.add_crypto(user_id, 'TRX', 50000.0)
        bot.answer_callback_query(call.id, "+50,000 TRX added!", show_alert=True)
    elif data == "owner_quick_trappy" and user_id in config.OWNER_IDS:
        db.add_crypto(user_id, 'TRAPPY', 100000.0)
        bot.answer_callback_query(call.id, "+100,000 TRAPPY added!", show_alert=True)
    elif data == "owner_post_gw" and user_id in config.OWNER_IDS:
        bot.answer_callback_query(call.id)
        bot.send_message(
            user_id,
            "🚀 To post to @trappytestnet, send:\n<code>/channel_giveaway 10000 TRAPPY 20 @trappytestnet</code>"
        )

def execute_claim_giveaway(user_id, gw_id, chat_id, call=None):
    gw = db.get_giveaway(gw_id)
    if not gw:
        if call:
            bot.answer_callback_query(call.id, "Giveaway not found.", show_alert=True)
        return
        
    req_channel = gw.get('required_channel', 'trappytestnet')
    try:
        member = bot.get_chat_member(f"@{req_channel}", user_id)
        if member.status in ['left', 'kicked']:
            if call:
                bot.answer_callback_query(call.id, f"❌ You must join @{req_channel} to claim!", show_alert=True)
            else:
                bot.send_message(chat_id, f"❌ Please subscribe to @{req_channel} to claim this giveaway!")
            return
    except Exception:
        pass
        
    success, reason, amt, currency, remaining = db.claim_giveaway(gw_id, user_id)
    if success:
        famt = format_crypto_amount(amt, currency)
        if call:
            bot.answer_callback_query(call.id, f"🎉 Claimed +{famt} {currency}!", show_alert=True)
            updated_gw = db.get_giveaway(gw_id)
            try:
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=kb.get_giveaway_claim_inline(
                        gw_id, updated_gw['claimed_count'], updated_gw['winners_count'],
                        is_completed=(updated_gw['status'] == 'completed')
                    )
                )
            except Exception:
                pass
        else:
            bot.send_message(chat_id, f"🎉 <b>Giveaway Claimed!</b> +{famt} {currency} added to your wallet!")
    else:
        if reason == "already_claimed":
            if call:
                bot.answer_callback_query(call.id, "⚠️ You already claimed this giveaway!", show_alert=True)
        elif reason == "completed":
            if call:
                bot.answer_callback_query(call.id, "❌ All rewards have already been claimed!", show_alert=True)
        else:
            if call:
                bot.answer_callback_query(call.id, f"Error: {reason}", show_alert=True)

# ==============================================================================
# CHANNEL & GROUP INTEGRATION (ADDING BOT TO CHANNELS)
# ==============================================================================
@bot.my_chat_member_handler()
def handle_chat_member_update(update):
    """Triggered when bot is added to or removed from channels & groups"""
    try:
        chat = update.chat
        new_status = update.new_chat_member.status
        user = update.from_user
        
        if chat.type == 'channel':
            if new_status in ['administrator', 'member']:
                db.register_channel(chat.id, chat.title, chat.username or '', user.id if user else None)
                logger.info(f"Bot added to channel: {chat.title} ({chat.id})")
                can_post = getattr(update.new_chat_member, 'can_post_messages', True)
                if can_post:
                    try:
                        bot.send_message(
                            chat_id=chat.id,
                            text=(
                                "⚡ <b>Trappy Testnet is now connected to this channel!</b>\n\n"
                                "Members can now participate in channel giveaways and receive transfers."
                            ),
                            reply_markup=kb.get_channel_invite_inline()
                        )
                    except Exception as e:
                        logger.warning(f"Could not send channel greeting: {e}")
            elif new_status in ['left', 'kicked']:
                db.unregister_channel(chat.id)
                logger.info(f"Bot removed from channel: {chat.title} ({chat.id})")
        elif chat.type in ['group', 'supergroup']:
            if new_status in ['administrator', 'member']:
                db.register_channel(chat.id, chat.title, chat.username or '', user.id if user else None)
                logger.info(f"Bot added to group: {chat.title} ({chat.id})")
            elif new_status in ['left', 'kicked']:
                db.unregister_channel(chat.id)
    except Exception as e:
        logger.warning(f"Error handling my_chat_member: {e}")

@bot.channel_post_handler(content_types=['text'])
def handle_channel_post(message):
    """Processes commands and mentions inside channel posts"""
    text = (message.text or '').strip()
    if not text:
        return
    sender_id, sender_username, sender_name = get_message_sender(message)
    # Check for dollar transfers or bot mentions
    if text.startswith('$') or any(alias in text.lower() for alias in config.BOT_ALIASES):
        m_dollar = MENTION_DOLLAR_PAY_REGEX.search(text)
        if m_dollar:
            amount_str, target_username, comment = m_dollar.groups()
            execute_payment(message, sender_id, target_username, amount_str, "USDT", note=comment or "")
            return
            
        m_pay = MENTION_PAY_REGEX.search(text)
        if m_pay:
            target_username, amount_str, currency_raw, comment = m_pay.groups()
            execute_payment(message, sender_id, target_username, amount_str, currency_raw, note=comment or "")
            return
            
        m_gw = MENTION_GIVEAWAY_REGEX.search(text)
        if m_gw:
            amount_str, currency_raw, winners_str = m_gw.groups()
            ch_name = message.chat.username or getattr(message.chat, 'title', 'trappytestnet')
            execute_create_giveaway(message, sender_id, amount_str, currency_raw, winners_str, channel=ch_name)
            return

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    logger.info("Starting Trappy Testnet v1.1.5 Bot on Localhost...")
    print("==================================================================")
    print("      TRAPPY TESTNET v1.1.5 TELEGRAM CRYPTO BOT")
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
