# -*- coding: utf-8 -*-
"""
Trappy Testnet - Keyboards & UI
"""
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from config import SUPPORTED_CRYPTOS, OFFICIAL_CHANNEL, MINI_APP_URL, BOT_USERNAME

ADD_TO_CHANNEL_URL = f"https://t.me/{BOT_USERNAME}?startchannel&admin=post_messages+edit_messages+delete_messages+invite_users"
ADD_TO_GROUP_URL = f"https://t.me/{BOT_USERNAME}?startgroup=true"

# ==============================================================================
# MAIN REPLY KEYBOARD (NO FAUCET)
# ==============================================================================
def get_main_reply_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("👛 Wallet"), KeyboardButton("📤 Send / Transfer"))
    kb.add(KeyboardButton("✉️ Cheques"), KeyboardButton("💳 Invoices"))
    kb.add(KeyboardButton("🎁 Giveaways"), KeyboardButton("ℹ️ Guide"))
    return kb

# ==============================================================================
# USER ONBOARDING & WALLET INLINE KEYBOARDS
# ==============================================================================
def get_welcome_inline_keyboard():
    """Welcome onboarding card buttons for new users"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    kb.add(
        InlineKeyboardButton("📥 Deposit Addresses", callback_data="action_deposit"),
        InlineKeyboardButton("✉️ New Cheque", callback_data="action_cheque_prompt")
    )
    kb.add(
        InlineKeyboardButton("📢 Add to Channel", url=ADD_TO_CHANNEL_URL),
        InlineKeyboardButton("👥 Add to Group", url=ADD_TO_GROUP_URL)
    )
    return kb

def get_wallet_inline_keyboard(webapp_url=None):
    """Wallet Card buttons"""
    kb = InlineKeyboardMarkup(row_width=2)
    target_url = webapp_url or MINI_APP_URL
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=target_url)))
    b_deposit = InlineKeyboardButton("📥 Deposit", callback_data="action_deposit")
    b_withdraw = InlineKeyboardButton("📤 Transfer", callback_data="action_withdraw")
    kb.add(b_deposit, b_withdraw)
    kb.add(
        InlineKeyboardButton("✉️ Cheque", callback_data="action_cheque_prompt"),
        InlineKeyboardButton("💳 Invoice", callback_data="action_invoice_prompt")
    )
    return kb

def get_deposit_inline_keyboard():
    """Deposit addresses only (No free faucets)"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

def get_withdraw_inline_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💸 Send by @username", callback_data="send_by_username"))
    kb.add(InlineKeyboardButton("⚡ Send to Testnet Address (TRC20 / Trappy)", callback_data="send_by_address"))
    kb.add(InlineKeyboardButton("🏷️ Send by Wallet ID (TRP-xxxx)", callback_data="send_by_wallet_id"))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

# ==============================================================================
# CHEQUES & INVOICES PROMPTS & MENUS
# ==============================================================================
def get_cheque_menu_inline():
    """Interactive cheque generation menu"""
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("✉️ 10 USDT", callback_data="ch_preset_10_USDT"),
        InlineKeyboardButton("✉️ 50 USDT", callback_data="ch_preset_50_USDT"),
        InlineKeyboardButton("✉️ 100 USDT", callback_data="ch_preset_100_USDT")
    )
    kb.add(
        InlineKeyboardButton("⚡ 500 TRAPPY", callback_data="ch_preset_500_TRAPPY"),
        InlineKeyboardButton("⚡ 1,000 TRAPPY", callback_data="ch_preset_1000_TRAPPY")
    )
    kb.add(InlineKeyboardButton("✍️ Custom Amount & Winners", callback_data="ch_custom_prompt"))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

def get_invoice_menu_inline():
    """Interactive payment invoice generation menu"""
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("💳 10 USDT", callback_data="iv_preset_10_USDT"),
        InlineKeyboardButton("💳 25 USDT", callback_data="iv_preset_25_USDT"),
        InlineKeyboardButton("💳 50 USDT", callback_data="iv_preset_50_USDT")
    )
    kb.add(
        InlineKeyboardButton("⚡ 500 TRAPPY", callback_data="iv_preset_500_TRAPPY"),
        InlineKeyboardButton("⚡ 1,000 TRAPPY", callback_data="iv_preset_1000_TRAPPY")
    )
    kb.add(InlineKeyboardButton("✍️ Custom Invoice Description", callback_data="iv_custom_prompt"))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

def get_cheque_claim_inline(cheque_id, claimed=0, winners=1, is_completed=False):
    kb = InlineKeyboardMarkup(row_width=1)
    if is_completed or claimed >= winners:
        kb.add(InlineKeyboardButton(f"✅ Cheque Claimed ({claimed}/{winners})", callback_data=f"ch_done_{cheque_id}"))
    else:
        text = "👛 Claim Cheque" if winners == 1 else f"👛 Claim Cheque ({claimed}/{winners})"
        kb.add(InlineKeyboardButton(text, callback_data=f"claim_ch_{cheque_id}"))
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    return kb

def get_invoice_pay_inline(invoice_id, amount_str, currency, is_paid=False):
    kb = InlineKeyboardMarkup(row_width=1)
    if is_paid:
        kb.add(InlineKeyboardButton(f"✅ Paid {amount_str} {currency}", callback_data=f"iv_done_{invoice_id}"))
    else:
        kb.add(InlineKeyboardButton(f"💳 Pay {amount_str} {currency}", callback_data=f"pay_iv_{invoice_id}"))
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    return kb

def get_giveaway_claim_inline(gw_id, claimed, winners, is_completed=False):
    kb = InlineKeyboardMarkup(row_width=1)
    if is_completed or claimed >= winners:
        kb.add(InlineKeyboardButton(f"✅ Giveaway Completed ({winners}/{winners})", callback_data=f"gw_done_{gw_id}"))
    else:
        kb.add(InlineKeyboardButton(f"🎁 Claim Giveaway ({claimed}/{winners})", callback_data=f"claim_gw_{gw_id}"))
    kb.add(InlineKeyboardButton("📢 Channel @trappytestnet", url=OFFICIAL_CHANNEL))
    return kb

def get_mention_response_inline():
    """Card buttons displayed when bot is mentioned in groups, channels or guest chats"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    kb.add(
        InlineKeyboardButton("✉️ Send Cheque", callback_data="action_cheque_prompt"),
        InlineKeyboardButton("💳 Request Invoice", callback_data="action_invoice_prompt")
    )
    kb.add(InlineKeyboardButton("🎁 Giveaways Channel", url=OFFICIAL_CHANNEL))
    return kb

def get_channel_connected_inline(chat_id=None):
    """Card buttons posted when bot is connected to a channel as admin"""
    kb = InlineKeyboardMarkup(row_width=1)
    if chat_id:
        kb.add(InlineKeyboardButton("🎰 Deploy Paying Panel in Channel", callback_data=f"chan_deploy_panel_{chat_id}"))
        kb.add(InlineKeyboardButton("⚙️ Gateway Settings (Message-after-Pay)", callback_data=f"chan_settings_{chat_id}"))
    kb.add(InlineKeyboardButton("👛 Open Testnet Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    kb.add(InlineKeyboardButton("📢 Official Channel", url=OFFICIAL_CHANNEL))
    return kb

# ==============================================================================
# CHANNEL PAYING PANEL (CASINO & DEPOSITS)
# ==============================================================================
def get_channel_paying_panel_inline(channel_chat_id):
    """Official Channel Paying / Betting Panel Buttons"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💸 Pay 10 USDT", callback_data=f"cpay_{channel_chat_id}_10_USDT"),
        InlineKeyboardButton("💸 Pay 50 USDT", callback_data=f"cpay_{channel_chat_id}_50_USDT")
    )
    kb.add(
        InlineKeyboardButton("💸 Pay 100 USDT", callback_data=f"cpay_{channel_chat_id}_100_USDT"),
        InlineKeyboardButton("⚡ Pay 1,000 TRAPPY", callback_data=f"cpay_{channel_chat_id}_1000_TRAPPY")
    )
    kb.add(InlineKeyboardButton("✍️ Custom Payment with Comment", callback_data=f"cpay_custom_{channel_chat_id}"))
    kb.add(InlineKeyboardButton("👛 Open Web Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    return kb

def get_channel_gateway_settings_inline(channel_chat_id, message_after_pay=1):
    kb = InlineKeyboardMarkup(row_width=1)
    status_icon = "ON ✅" if message_after_pay == 1 else "OFF ❌"
    kb.add(InlineKeyboardButton(f"🔔 Message-after-Pay: {status_icon}", callback_data=f"chan_toggle_map_{channel_chat_id}"))
    kb.add(InlineKeyboardButton("🎰 Re-post Paying Panel in Channel", callback_data=f"chan_deploy_panel_{channel_chat_id}"))
    kb.add(InlineKeyboardButton("< Close Settings", callback_data="action_close_card"))
    return kb

# ==============================================================================
# SECRET MASTER ADMIN PANEL KEYBOARDS (ID: 9051090063)
# ==============================================================================
def get_admin_main_inline():
    """Main Master Admin Dashboard"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🏆 Richest Users Leaderboard", callback_data="adm_leaderboard"))
    kb.add(
        InlineKeyboardButton("👥 Users Directory", callback_data="adm_users_1"),
        InlineKeyboardButton("🔍 Search User", callback_data="adm_search_user")
    )
    kb.add(
        InlineKeyboardButton("✉️ Issue Master Cheque", callback_data="adm_master_cheque"),
        InlineKeyboardButton("➕ Grant Testnet Funds", callback_data="adm_quick_grant")
    )
    kb.add(
        InlineKeyboardButton("🎰 Connected Channels", callback_data="adm_channels"),
        InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast")
    )
    kb.add(InlineKeyboardButton("🔒 Lock Admin Panel", callback_data="adm_lock"))
    return kb

def get_admin_leaderboard_inline(top_users):
    kb = InlineKeyboardMarkup(row_width=1)
    for i, u in enumerate(top_users):
        uname = f"@{u['username']}" if u.get('username') else u.get('first_name', str(u['user_id']))
        kb.add(InlineKeyboardButton(f"#{i+1} {uname} — ${u['total_usd']:,.0f}", callback_data=f"adm_inspect_{u['user_id']}"))
    kb.add(InlineKeyboardButton("< Back to Admin Terminal", callback_data="adm_home"))
    return kb

def get_admin_users_list_inline(users, page, total_pages):
    kb = InlineKeyboardMarkup(row_width=1)
    for u in users:
        uname = f"@{u['username']}" if u.get('username') else u.get('first_name', str(u['user_id']))
        kb.add(InlineKeyboardButton(f"👤 {uname} (${u['total_usd']:,.0f})", callback_data=f"adm_inspect_{u['user_id']}"))
    
    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"adm_users_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"Page {page}/{total_pages}", callback_data="adm_noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"adm_users_{page+1}"))
    kb.row(*nav_buttons)
    kb.add(InlineKeyboardButton("< Back to Admin Terminal", callback_data="adm_home"))
    return kb

def get_admin_user_manage_inline(user_id):
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("➕ USDT", callback_data=f"adm_grant_{user_id}_USDT"),
        InlineKeyboardButton("➕ TRX", callback_data=f"adm_grant_{user_id}_TRX"),
        InlineKeyboardButton("➕ TRAPPY", callback_data=f"adm_grant_{user_id}_TRAPPY")
    )
    kb.add(
        InlineKeyboardButton("➖ Deduct Funds", callback_data=f"adm_deduct_{user_id}"),
        InlineKeyboardButton("🔄 Zero Out", callback_data=f"adm_reset_{user_id}")
    )
    kb.add(InlineKeyboardButton("✉️ Dedicated Master Cheque", callback_data=f"adm_user_cheque_{user_id}"))
    kb.add(
        InlineKeyboardButton("👥 Users Directory", callback_data="adm_users_1"),
        InlineKeyboardButton("🏠 Admin Home", callback_data="adm_home")
    )
    return kb

def get_admin_grant_presets_inline(user_id, currency):
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("+100", callback_data=f"adm_exec_grant_{user_id}_{currency}_100"),
        InlineKeyboardButton("+500", callback_data=f"adm_exec_grant_{user_id}_{currency}_500"),
        InlineKeyboardButton("+1,000", callback_data=f"adm_exec_grant_{user_id}_{currency}_1000")
    )
    kb.add(
        InlineKeyboardButton("+5,000", callback_data=f"adm_exec_grant_{user_id}_{currency}_5000"),
        InlineKeyboardButton("+10,000", callback_data=f"adm_exec_grant_{user_id}_{currency}_10000"),
        InlineKeyboardButton("✍️ Custom", callback_data=f"adm_custom_grant_{user_id}_{currency}")
    )
    kb.add(InlineKeyboardButton("< Back to User Profile", callback_data=f"adm_inspect_{user_id}"))
    return kb

def get_admin_master_cheque_menu():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("✉️ 100 USDT", callback_data="adm_mch_exec_USDT_100"),
        InlineKeyboardButton("✉️ 500 USDT", callback_data="adm_mch_exec_USDT_500"),
        InlineKeyboardButton("✉️ 1,000 USDT", callback_data="adm_mch_exec_USDT_1000")
    )
    kb.add(
        InlineKeyboardButton("⚡ 5,000 TRAPPY", callback_data="adm_mch_exec_TRAPPY_5000"),
        InlineKeyboardButton("⚡ 50,000 TRAPPY", callback_data="adm_mch_exec_TRAPPY_50000")
    )
    kb.add(InlineKeyboardButton("✍️ Custom Amount & Winners Count", callback_data="adm_mch_custom"))
    kb.add(InlineKeyboardButton("< Back to Admin Terminal", callback_data="adm_home"))
    return kb
