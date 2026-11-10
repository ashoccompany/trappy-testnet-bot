# -*- coding: utf-8 -*-
"""
Trappy Testnet v1.1.5 - Keyboards & UI
"""
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from config import SUPPORTED_CRYPTOS, OFFICIAL_CHANNEL, MINI_APP_URL, BOT_USERNAME

ADD_TO_CHANNEL_URL = f"https://t.me/{BOT_USERNAME}?startchannel&admin=post_messages+edit_messages+delete_messages+invite_users"

def get_main_reply_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("👛 Wallet"))
    kb.add(KeyboardButton("✉️ Cheques"), KeyboardButton("💳 Invoices"))
    kb.add(KeyboardButton("🎁 Giveaways"), KeyboardButton("ℹ️ About"))
    return kb

def get_wallet_inline_keyboard(webapp_url=None):
    """
    Exact layout matching reference Photo 2:
    [ 👛 Open Wallet ]
    [ Deposit ] [ Withdraw ]
    [ < Back ]
    """
    kb = InlineKeyboardMarkup(row_width=2)
    target_url = webapp_url or MINI_APP_URL
    kb.add(InlineKeyboardButton("👛 Open Wallet", web_app=WebAppInfo(url=target_url)))
    b_deposit = InlineKeyboardButton("Deposit", callback_data="action_deposit")
    b_withdraw = InlineKeyboardButton("Withdraw", callback_data="action_withdraw")
    kb.add(b_deposit, b_withdraw)
    kb.add(InlineKeyboardButton("< Back", callback_data="action_back_main"))
    return kb

def get_deposit_inline_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for sym, info in SUPPORTED_CRYPTOS.items():
        amt = info['faucet_amount']
        amt_str = f"{int(amt):,}"
        buttons.append(InlineKeyboardButton(f"{info['icon']} +{amt_str} {sym}", callback_data=f"faucet_{sym}"))
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            kb.add(buttons[i], buttons[i+1])
        else:
            kb.add(buttons[i])
            
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

def get_withdraw_inline_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💸 Send by @username", callback_data="send_by_username"))
    kb.add(InlineKeyboardButton("⚡ Send to Testnet Address (TRC20 / Trappy)", callback_data="send_by_address"))
    kb.add(InlineKeyboardButton("🏷️ Send by Wallet ID (TRP-xxxx)", callback_data="send_by_wallet_id"))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

def get_cheque_claim_inline(cheque_id, claimed=0, winners=1, is_completed=False):
    kb = InlineKeyboardMarkup(row_width=1)
    if is_completed or claimed >= winners:
        kb.add(InlineKeyboardButton(f"✅ Cheque Claimed ({claimed}/{winners})", callback_data=f"ch_done_{cheque_id}"))
    else:
        text = "👛 Claim Cheque" if winners == 1 else f"👛 Claim Cheque ({claimed}/{winners})"
        kb.add(InlineKeyboardButton(text, callback_data=f"claim_ch_{cheque_id}"))
    kb.add(InlineKeyboardButton("👛 Open Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    return kb

def get_invoice_pay_inline(invoice_id, amount_str, currency, is_paid=False):
    kb = InlineKeyboardMarkup(row_width=1)
    if is_paid:
        kb.add(InlineKeyboardButton(f"✅ Paid {amount_str} {currency}", callback_data=f"iv_done_{invoice_id}"))
    else:
        kb.add(InlineKeyboardButton(f"💳 Pay {amount_str} {currency}", callback_data=f"pay_iv_{invoice_id}"))
    kb.add(InlineKeyboardButton("👛 Open Wallet", web_app=WebAppInfo(url=MINI_APP_URL)))
    return kb

def get_giveaway_claim_inline(gw_id, claimed, winners, is_completed=False):
    kb = InlineKeyboardMarkup(row_width=1)
    if is_completed or claimed >= winners:
        kb.add(InlineKeyboardButton(f"✅ Giveaway Completed ({winners}/{winners})", callback_data=f"gw_done_{gw_id}"))
    else:
        kb.add(InlineKeyboardButton(f"🎁 Claim Giveaway ({claimed}/{winners})", callback_data=f"claim_gw_{gw_id}"))
    kb.add(InlineKeyboardButton("📢 Channel @trappytestnet", url=OFFICIAL_CHANNEL))
    return kb

def get_hidden_owner_inline():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💵 +10,000 USDT to Me", callback_data="owner_quick_usdt"),
        InlineKeyboardButton("🔴 +50,000 TRX to Me", callback_data="owner_quick_trx")
    )
    kb.add(
        InlineKeyboardButton("⚡ +100,000 TRAPPY to Me", callback_data="owner_quick_trappy"),
        InlineKeyboardButton("🚀 Post Giveaway to @trappytestnet", callback_data="owner_post_gw")
    )
    kb.add(InlineKeyboardButton("➕ Add Bot to Channel", url=ADD_TO_CHANNEL_URL))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb

def get_channel_invite_inline():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("➕ Add Bot to Channel", url=ADD_TO_CHANNEL_URL))
    kb.add(InlineKeyboardButton("📢 Channel @trappytestnet", url=OFFICIAL_CHANNEL))
    return kb

def get_add_to_channel_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 Add to Channel (as Admin)", url=ADD_TO_CHANNEL_URL))
    kb.add(InlineKeyboardButton("👥 Add to Group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
    kb.add(InlineKeyboardButton("< Back to Wallet", callback_data="action_wallet"))
    return kb
