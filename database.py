# -*- coding: utf-8 -*-
"""
Trappy Testnet - Database Module
Ledger for USDT, TRX, and TRAPPY.
"""
import sqlite3
import time
import secrets
import threading
import hashlib
from config import DB_PATH, SUPPORTED_CRYPTOS, FAUCET_COOLDOWN_SECONDS, OWNER_IDS

db_lock = threading.Lock()

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BECH32_ALPHABET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'

def generate_tron_address(user_id):
    """
    Generates a realistic 34-character TRC-20 / TRON testnet address starting with 'T'.
    Deterministic for each user_id.
    """
    h = hashlib.sha512(f"trappy_tron_net_{user_id}".encode()).digest()
    return "T" + "".join(BASE58_ALPHABET[b % len(BASE58_ALPHABET)] for b in h[:33])

def generate_trappy_address(user_id):
    """
    Generates a realistic 42-character Layer-1 Bech32 testnet address starting with 'trp1'.
    Deterministic for each user_id.
    """
    h = hashlib.sha512(f"trappy_native_net_{user_id}".encode()).digest()
    return "trp1" + "".join(BECH32_ALPHABET[b % len(BECH32_ALPHABET)] for b in h[:38])

def generate_wallet_id(user_id):
    suffix = secrets.token_hex(2).upper()
    return f"TRP-{user_id % 10000:04d}-{suffix}"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                wallet_id TEXT UNIQUE,
                tron_address TEXT,
                trappy_address TEXT,
                joined_at REAL
            )
        ''')

        # Auto-migration for realistic addresses
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN tron_address TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN trappy_address TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Multi-currency Balances
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER,
                currency TEXT,
                amount REAL DEFAULT 0.0,
                PRIMARY KEY (user_id, currency)
            )
        ''')
        
        # Transfers / P2P Transactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                to_user_id INTEGER,
                currency TEXT,
                amount REAL,
                note TEXT DEFAULT '',
                created_at REAL
            )
        ''')
        
        # Giveaways Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS giveaways (
                id TEXT PRIMARY KEY,
                creator_id INTEGER,
                currency TEXT,
                total_amount REAL,
                amount_per_user REAL,
                winners_count INTEGER,
                claimed_count INTEGER DEFAULT 0,
                required_channel TEXT DEFAULT 'trappytestnet',
                status TEXT DEFAULT 'active',
                is_unlimited_owner INTEGER DEFAULT 0,
                created_at REAL
            )
        ''')
        
        # Giveaway Claims
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS giveaway_claims (
                giveaway_id TEXT,
                user_id INTEGER,
                amount REAL,
                claimed_at REAL,
                PRIMARY KEY (giveaway_id, user_id)
            )
        ''')

        # Cheques Table (1-to-1 or multi-user cheques)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cheques (
                id TEXT PRIMARY KEY,
                creator_id INTEGER,
                currency TEXT,
                total_amount REAL,
                amount_per_user REAL,
                winners_count INTEGER DEFAULT 1,
                claimed_count INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                is_unlimited_owner INTEGER DEFAULT 0,
                created_at REAL
            )
        ''')
        
        # Cheque Claims Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cheque_claims (
                cheque_id TEXT,
                user_id INTEGER,
                amount REAL,
                claimed_at REAL,
                PRIMARY KEY (cheque_id, user_id)
            )
        ''')
        
        # Invoices / Pay Requests Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                creator_id INTEGER,
                currency TEXT,
                amount REAL,
                note TEXT DEFAULT '',
                paid_by INTEGER,
                status TEXT DEFAULT 'active',
                created_at REAL,
                paid_at REAL
            )
        ''')
        
        # Faucet Claims
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faucet_claims (
                user_id INTEGER,
                currency TEXT,
                last_claim_time REAL,
                PRIMARY KEY (user_id, currency)
            )
        ''')
        
        # Connected Channels Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                username TEXT,
                added_by INTEGER,
                message_after_pay INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                added_at REAL
            )
        ''')

        # Populate realistic addresses for existing users if missing
        cursor.execute("SELECT user_id, tron_address, trappy_address FROM users")
        for u in cursor.fetchall():
            uid = u['user_id']
            if not u['tron_address'] or not u['trappy_address']:
                t_addr = u['tron_address'] or generate_tron_address(uid)
                trp_addr = u['trappy_address'] or generate_trappy_address(uid)
                cursor.execute("UPDATE users SET tron_address = ?, trappy_address = ? WHERE user_id = ?", (t_addr, trp_addr, uid))
        
        try:
            cursor.execute("ALTER TABLE channels ADD COLUMN message_after_pay INTEGER DEFAULT 1")
        except Exception:
            pass
        conn.commit()
        conn.close()

def get_or_create_user(user_id, username='', first_name=''):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        now = time.time()
        clean_user = (username or '').lower().lstrip('@')
        clean_name = first_name or 'Trappist'
        
        if row is None:
            wallet_id = generate_wallet_id(user_id)
            tron_addr = generate_tron_address(user_id)
            trp_addr = generate_trappy_address(user_id)
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, wallet_id, tron_address, trappy_address, joined_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, clean_user, clean_name, wallet_id, tron_addr, trp_addr, now))
            
            for curr in SUPPORTED_CRYPTOS:
                cursor.execute('''
                    INSERT OR IGNORE INTO balances (user_id, currency, amount)
                    VALUES (?, ?, 0.0)
                ''', (user_id, curr))
                
            conn.commit()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = dict(cursor.fetchone())
            conn.close()
            user['is_new'] = True
            return user
        else:
            # Ensure realistic addresses exist on row
            t_addr = row['tron_address'] or generate_tron_address(user_id)
            trp_addr = row['trappy_address'] or generate_trappy_address(user_id)
            cursor.execute('''
                UPDATE users SET username = ?, first_name = ?, tron_address = ?, trappy_address = ? WHERE user_id = ?
            ''', (clean_user or row['username'], clean_name or row['first_name'], t_addr, trp_addr, user_id))
            conn.commit()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = dict(cursor.fetchone())
            conn.close()
            user['is_new'] = False
            return user

def get_user(user_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

def find_user(identifier):
    if not identifier:
        return None
    raw = str(identifier).strip().lstrip('@')
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Telegram ID
        if raw.isdigit():
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (int(raw),))
            row = cursor.fetchone()
            if row:
                conn.close()
                return dict(row)
                
        # 2. Telegram Username
        cursor.execute('SELECT * FROM users WHERE LOWER(username) = ?', (raw.lower(),))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)
            
        # 3. Legacy Wallet ID (TRP-...)
        cursor.execute('SELECT * FROM users WHERE LOWER(wallet_id) = ?', (raw.lower(),))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)

        # 4. Realistic TRON / TRC-20 Address (Starts with 'T', 34 chars)
        cursor.execute('SELECT * FROM users WHERE tron_address = ?', (raw,))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)

        # 5. Realistic Trappy Native Address (Starts with 'trp1', 42 chars)
        cursor.execute('SELECT * FROM users WHERE LOWER(trappy_address) = ?', (raw.lower(),))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

def get_balance(user_id, currency):
    currency = currency.upper()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT amount FROM balances WHERE user_id = ? AND currency = ?', (user_id, currency))
        row = cursor.fetchone()
        conn.close()
        return float(row['amount']) if row else 0.0

def get_all_balances(user_id):
    balances = {curr: 0.0 for curr in SUPPORTED_CRYPTOS}
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT currency, amount FROM balances WHERE user_id = ?', (user_id,))
        for r in cursor.fetchall():
            if r['currency'] in SUPPORTED_CRYPTOS:
                balances[r['currency']] = float(r['amount'])
        conn.close()
    return balances

def calculate_usd_total(balances):
    total_usd = 0.0
    for curr, amt in balances.items():
        if curr in SUPPORTED_CRYPTOS:
            rate = SUPPORTED_CRYPTOS[curr]['usd_price']
            total_usd += amt * rate
    return total_usd

def add_crypto(user_id, currency, amount):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS:
        return False, "Unsupported currency"
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO balances (user_id, currency, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        ''', (user_id, currency, amount, amount))
        conn.commit()
        conn.close()
    return True, get_balance(user_id, currency)

def transfer_crypto(from_user_id, to_user_id, currency, amount, note=""):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS:
        return False, "Unsupported currency"
    if amount <= 0:
        return False, "Invalid amount"
    if from_user_id == to_user_id:
        return False, "Cannot send to yourself"
        
    is_owner = from_user_id in OWNER_IDS
    now = time.time()
    
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        if not is_owner:
            cursor.execute('SELECT amount FROM balances WHERE user_id = ? AND currency = ?', (from_user_id, currency))
            row = cursor.fetchone()
            curr_bal = float(row['amount']) if row else 0.0
            if curr_bal < amount:
                conn.close()
                return False, "insufficient_balance"
                
            cursor.execute('''
                UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?
            ''', (amount, from_user_id, currency))
        else:
            cursor.execute('''
                INSERT INTO balances (user_id, currency, amount)
                VALUES (?, ?, 0.0)
                ON CONFLICT(user_id, currency) DO NOTHING
            ''', (from_user_id, currency))
            cursor.execute('''
                UPDATE balances SET amount = MAX(0.0, amount - ?) WHERE user_id = ? AND currency = ?
            ''', (amount, from_user_id, currency))
            
        cursor.execute('''
            INSERT INTO balances (user_id, currency, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        ''', (to_user_id, currency, amount, amount))
        
        cursor.execute('''
            INSERT INTO transfers (from_user_id, to_user_id, currency, amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (from_user_id, to_user_id, currency, amount, note, now))
        
        conn.commit()
        conn.close()
        
    return True, "success"

def create_giveaway(creator_id, currency, total_amount, winners_count, channel="trappytestnet"):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS:
        return False, "Unsupported currency", None
    if total_amount <= 0 or winners_count <= 0:
        return False, "Invalid amount or winners count", None
        
    is_owner = creator_id in OWNER_IDS
    amount_per_user = total_amount / float(winners_count)
    gw_id = "gw_" + secrets.token_hex(4)
    now = time.time()
    
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        if not is_owner:
            cursor.execute('SELECT amount FROM balances WHERE user_id = ? AND currency = ?', (creator_id, currency))
            row = cursor.fetchone()
            curr_bal = float(row['amount']) if row else 0.0
            if curr_bal < total_amount:
                conn.close()
                return False, "insufficient_balance", None
                
            cursor.execute('''
                UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?
            ''', (total_amount, creator_id, currency))
            
        cursor.execute('''
            INSERT INTO giveaways (
                id, creator_id, currency, total_amount, amount_per_user,
                winners_count, claimed_count, required_channel, status, is_unlimited_owner, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'active', ?, ?)
        ''', (gw_id, creator_id, currency, total_amount, amount_per_user, winners_count, channel, 1 if is_owner else 0, now))
        
        conn.commit()
        conn.close()
        
    return True, "success", gw_id

def get_giveaway(gw_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.*, u.username as creator_username, u.first_name as creator_first_name
            FROM giveaways g
            LEFT JOIN users u ON g.creator_id = u.user_id
            WHERE g.id = ?
        ''', (gw_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

def claim_giveaway(gw_id, user_id):
    now = time.time()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM giveaways WHERE id = ?', (gw_id,))
        gw = cursor.fetchone()
        if not gw:
            conn.close()
            return False, "not_found", 0, "", 0
            
        if gw['status'] != 'active' or gw['claimed_count'] >= gw['winners_count']:
            conn.close()
            return False, "completed", 0, gw['currency'], 0
            
        cursor.execute('SELECT * FROM giveaway_claims WHERE giveaway_id = ? AND user_id = ?', (gw_id, user_id))
        if cursor.fetchone():
            conn.close()
            return False, "already_claimed", 0, gw['currency'], 0
            
        amount = gw['amount_per_user']
        currency = gw['currency']
        new_claimed = gw['claimed_count'] + 1
        new_status = 'completed' if new_claimed >= gw['winners_count'] else 'active'
        
        cursor.execute('''
            INSERT INTO balances (user_id, currency, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        ''', (user_id, currency, amount, amount))
        
        cursor.execute('''
            INSERT INTO giveaway_claims (giveaway_id, user_id, amount, claimed_at)
            VALUES (?, ?, ?, ?)
        ''', (gw_id, user_id, amount, now))
        
        cursor.execute('''
            UPDATE giveaways 
            SET claimed_count = ?, status = ?
            WHERE id = ?
        ''', (new_claimed, new_status, gw_id))
        
        conn.commit()
        conn.close()
        
        remaining = gw['winners_count'] - new_claimed
        return True, "success", amount, currency, remaining

def claim_faucet(user_id, currency):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS:
        return False, "Unsupported currency", 0, 0
        
    now = time.time()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT last_claim_time FROM faucet_claims WHERE user_id = ? AND currency = ?', (user_id, currency))
        row = cursor.fetchone()
        
        if row:
            elapsed = now - row['last_claim_time']
            if elapsed < FAUCET_COOLDOWN_SECONDS:
                remaining_secs = int(FAUCET_COOLDOWN_SECONDS - elapsed)
                mins = remaining_secs // 60
                conn.close()
                return False, "cooldown", mins, 0
                
        amount = SUPPORTED_CRYPTOS[currency]['faucet_amount']
        
        cursor.execute('''
            INSERT INTO balances (user_id, currency, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        ''', (user_id, currency, amount, amount))
        
        cursor.execute('''
            INSERT INTO faucet_claims (user_id, currency, last_claim_time)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET last_claim_time = ?
        ''', (user_id, currency, now, now))
        
        conn.commit()
        conn.close()
        
    return True, "success", amount, 0

def get_stats():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM giveaways')
        gw_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM transfers')
        tx_count = cursor.fetchone()[0]
        conn.close()
        return {'users': users_count, 'giveaways': gw_count, 'transfers': tx_count}

def register_channel(chat_id, title, username="", added_by=None):
    now = time.time()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO channels (chat_id, title, username, added_by, status, added_at)
            VALUES (?, ?, ?, ?, 'active', ?)
            ON CONFLICT(chat_id) DO UPDATE SET title = ?, username = ?, status = 'active'
        ''', (chat_id, title or '', (username or '').lstrip('@'), added_by, now, title or '', (username or '').lstrip('@')))
        conn.commit()
        conn.close()

def unregister_channel(chat_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE channels SET status = 'left' WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()

def get_active_channels():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE status = 'active'")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

# ==============================================================================
# CHEQUES ENGINE (SINGLE-USER & MULTI-USER CLAIMABLE CHEQUES)
# ==============================================================================
def create_cheque(creator_id, currency, total_amount, winners_count=1, note='', custom_id=None):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS:
        return False, "unsupported_currency", None
    if total_amount <= 0 or winners_count <= 0:
        return False, "invalid_amount", None
        
    is_owner = creator_id in OWNER_IDS
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        if not is_owner:
            cursor.execute('SELECT amount FROM balances WHERE user_id = ? AND currency = ?', (creator_id, currency))
            row = cursor.fetchone()
            bal = float(row['amount']) if row else 0.0
            if bal < total_amount:
                conn.close()
                return False, "insufficient_balance", None
            cursor.execute('UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?',
                           (total_amount, creator_id, currency))
                           
        amt_per_user = total_amount / float(winners_count)
        cheque_id = custom_id if custom_id else f"c_{secrets.token_hex(4)}"
        now = time.time()
        
        cursor.execute('''
            INSERT INTO cheques (
                id, creator_id, currency, total_amount, amount_per_user,
                winners_count, claimed_count, note, status, is_unlimited_owner, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'active', ?, ?)
        ''', (cheque_id, creator_id, currency, total_amount, amt_per_user, winners_count, note, 1 if is_owner else 0, now))
        
        conn.commit()
        conn.close()
        return True, "success", cheque_id

def get_cheque(cheque_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cheques WHERE id = ?', (cheque_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

def claim_cheque(cheque_id, user_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cheques WHERE id = ?', (cheque_id,))
        ch = cursor.fetchone()
        if not ch:
            conn.close()
            return False, "not_found", 0.0, "", 0
            
        if ch['status'] != 'active':
            conn.close()
            return False, "completed", 0.0, ch['currency'], 0
            
        cursor.execute('SELECT 1 FROM cheque_claims WHERE cheque_id = ? AND user_id = ?', (cheque_id, user_id))
        if cursor.fetchone():
            conn.close()
            return False, "already_claimed", 0.0, ch['currency'], ch['winners_count'] - ch['claimed_count']
            
        if ch['claimed_count'] >= ch['winners_count']:
            cursor.execute("UPDATE cheques SET status = 'completed' WHERE id = ?", (cheque_id,))
            conn.commit()
            conn.close()
            return False, "completed", 0.0, ch['currency'], 0
            
        claim_amt = float(ch['amount_per_user'])
        now = time.time()
        
        cursor.execute('INSERT INTO cheque_claims (cheque_id, user_id, amount, claimed_at) VALUES (?, ?, ?, ?)',
                       (cheque_id, user_id, claim_amt, now))
        cursor.execute('''
            INSERT INTO balances (user_id, currency, amount) VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        ''', (user_id, ch['currency'], claim_amt, claim_amt))
        
        new_claimed = ch['claimed_count'] + 1
        new_status = 'completed' if new_claimed >= ch['winners_count'] else 'active'
        cursor.execute('UPDATE cheques SET claimed_count = ?, status = ? WHERE id = ?', (new_claimed, new_status, cheque_id))
        
        # Record transfer
        cursor.execute('''
            INSERT INTO transfers (from_user_id, to_user_id, currency, amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ch['creator_id'], user_id, ch['currency'], claim_amt, f"Cheque {cheque_id}" + (f": {ch['note']}" if ch['note'] else ""), now))
        
        conn.commit()
        remaining = ch['winners_count'] - new_claimed
        conn.close()
        return True, "success", claim_amt, ch['currency'], remaining

# ==============================================================================
# INVOICES / PAYMENT REQUESTS ENGINE
# ==============================================================================
def create_invoice(creator_id, currency, amount, note='', custom_id=None):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS:
        return False, "unsupported_currency", None
    if amount <= 0:
        return False, "invalid_amount", None
        
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        invoice_id = custom_id if custom_id else f"iv_{secrets.token_hex(4)}"
        now = time.time()
        
        cursor.execute('''
            INSERT INTO invoices (id, creator_id, currency, amount, note, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?)
        ''', (invoice_id, creator_id, currency, amount, note, now))
        
        conn.commit()
        conn.close()
        return True, "success", invoice_id

def get_invoice(invoice_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

def pay_invoice(invoice_id, payer_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        iv = cursor.fetchone()
        if not iv:
            conn.close()
            return False, "not_found", 0.0, "", None
            
        if iv['status'] != 'active':
            conn.close()
            return False, "already_paid", 0.0, iv['currency'], iv['creator_id']
            
        if iv['creator_id'] == payer_id:
            conn.close()
            return False, "cannot_pay_self", 0.0, iv['currency'], iv['creator_id']
            
        amount = float(iv['amount'])
        currency = iv['currency']
        
        # Check payer balance
        cursor.execute('SELECT amount FROM balances WHERE user_id = ? AND currency = ?', (payer_id, currency))
        row = cursor.fetchone()
        payer_bal = float(row['amount']) if row else 0.0
        if payer_bal < amount:
            conn.close()
            return False, "insufficient_balance", amount, currency, iv['creator_id']
            
        now = time.time()
        cursor.execute('UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?', (amount, payer_id, currency))
        cursor.execute('''
            INSERT INTO balances (user_id, currency, amount) VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        ''', (iv['creator_id'], currency, amount, amount))
        
        cursor.execute('UPDATE invoices SET status = "paid", paid_by = ?, paid_at = ? WHERE id = ?', (payer_id, now, invoice_id))
        cursor.execute('''
            INSERT INTO transfers (from_user_id, to_user_id, currency, amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (payer_id, iv['creator_id'], currency, amount, f"Invoice {invoice_id}" + (f": {iv['note']}" if iv['note'] else ""), now))
        
        conn.commit()
        conn.close()
        return True, "success", amount, currency, iv['creator_id']

def cancel_invoice(invoice_id, user_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        iv = cursor.fetchone()
        if not iv:
            conn.close()
            return False, "not_found"
        if iv['creator_id'] != user_id and user_id not in OWNER_IDS:
            conn.close()
            return False, "unauthorized"
        if iv['status'] != 'active':
            conn.close()
            return False, "already_closed"
        cursor.execute('UPDATE invoices SET status = "cancelled" WHERE id = ?', (invoice_id,))
        conn.commit()
        conn.close()
        return True, "success"


def claim_all_faucets(user_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        for curr, info in SUPPORTED_CRYPTOS.items():
            amt = info['faucet_amount']
            cursor.execute('''
                INSERT INTO balances (user_id, currency, amount)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
            ''', (user_id, curr, amt, amt))
        conn.commit()
        conn.close()
    return True, "success"


def get_top_richest_users(limit=10):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name, tron_address, trappy_address, wallet_id FROM users")
        users = [dict(r) for r in cursor.fetchall()]
        for u in users:
            uid = u['user_id']
            cursor.execute("SELECT currency, amount FROM balances WHERE user_id = ?", (uid,))
            bal_map = {row['currency']: float(row['amount']) for row in cursor.fetchall()}
            u['balances'] = {
                'USDT': bal_map.get('USDT', 0.0),
                'TRX': bal_map.get('TRX', 0.0),
                'TRAPPY': bal_map.get('TRAPPY', 0.0)
            }
            u['total_usd'] = round(
                u['balances']['USDT'] * 1.0 +
                u['balances']['TRX'] * 0.16 +
                u['balances']['TRAPPY'] * 0.25,
                2
            )
        conn.close()
    users.sort(key=lambda x: x['total_usd'], reverse=True)
    return users[:limit]

def get_all_users_paginated(page=1, per_page=8):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_count = cursor.fetchone()[0]
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT user_id, username, first_name, wallet_id, tron_address, trappy_address, joined_at
            FROM users
            ORDER BY joined_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        users = [dict(r) for r in cursor.fetchall()]
        for u in users:
            uid = u['user_id']
            cursor.execute("SELECT currency, amount FROM balances WHERE user_id = ?", (uid,))
            bal_map = {row['currency']: float(row['amount']) for row in cursor.fetchall()}
            u['balances'] = {
                'USDT': bal_map.get('USDT', 0.0),
                'TRX': bal_map.get('TRX', 0.0),
                'TRAPPY': bal_map.get('TRAPPY', 0.0)
            }
            u['total_usd'] = round(
                u['balances']['USDT'] * 1.0 +
                u['balances']['TRX'] * 0.16 +
                u['balances']['TRAPPY'] * 0.25,
                2
            )
        conn.close()
    return users, total_count, total_pages

def admin_add_crypto(user_id, currency, amount):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS or amount <= 0:
        return False, 0.0
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO balances (user_id, currency, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?
        """, (user_id, currency, amount, amount))
        cursor.execute("""
            INSERT INTO transfers (from_user_id, to_user_id, currency, amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (9051090063, user_id, currency, amount, "Admin Allocation", time.time()))
        conn.commit()
        cursor.execute("SELECT amount FROM balances WHERE user_id = ? AND currency = ?", (user_id, currency))
        new_bal = cursor.fetchone()['amount']
        conn.close()
    return True, new_bal

def admin_deduct_crypto(user_id, currency, amount):
    currency = currency.upper()
    if currency not in SUPPORTED_CRYPTOS or amount <= 0:
        return False, 0.0
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT amount FROM balances WHERE user_id = ?", (user_id,))
        cursor.execute("""
            UPDATE balances SET amount = MAX(0.0, amount - ?) WHERE user_id = ? AND currency = ?
        """, (amount, user_id, currency))
        cursor.execute("""
            INSERT INTO transfers (from_user_id, to_user_id, currency, amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, 9051090063, currency, amount, "Admin Deduction", time.time()))
        conn.commit()
        cursor.execute("SELECT amount FROM balances WHERE user_id = ? AND currency = ?", (user_id, currency))
        new_bal = cursor.fetchone()['amount']
        conn.close()
    return True, new_bal

def admin_reset_user_balances(user_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        for c in SUPPORTED_CRYPTOS:
            cursor.execute("UPDATE balances SET amount = 0.0 WHERE user_id = ? AND currency = ?", (user_id, c))
        conn.commit()
        conn.close()
    return True

def create_master_cheque(currency, amount, winners_count=1, note="", creator_id=9051090063):
    import secrets
    currency = currency.upper()
    ch_id = f"mc_{secrets.token_hex(4)}"
    amount_per_user = amount / float(winners_count)
    now = time.time()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cheques (id, creator_id, currency, total_amount, amount_per_user, winners_count, claimed_count, note, status, is_unlimited_owner, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'active', 1, ?)
        """, (ch_id, creator_id, currency, amount, amount_per_user, winners_count, note, now))
        conn.commit()
        conn.close()
    return True, ch_id

def get_system_telemetry():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        users_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM channels WHERE status = 'active'")
        chans_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cheques WHERE status = 'active'")
        cheques_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE status = 'active'")
        invoices_cnt = cursor.fetchone()[0]
        
        totals = {'USDT': 0.0, 'TRX': 0.0, 'TRAPPY': 0.0}
        for c in totals:
            cursor.execute("SELECT SUM(amount) FROM balances WHERE currency = ?", (c,))
            res = cursor.fetchone()[0]
            totals[c] = float(res) if res else 0.0
        conn.close()
    tot_usd = totals['USDT'] * 1.0 + totals['TRX'] * 0.16 + totals['TRAPPY'] * 0.25
    return {
        'users': users_cnt,
        'channels': chans_cnt,
        'cheques': cheques_cnt,
        'invoices': invoices_cnt,
        'circulating': totals,
        'total_usd': tot_usd
    }

def register_channel_gateway(chat_id, title, username, added_by):
    now = time.time()
    clean_un = (username or '').lstrip('@').lower()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO channels (chat_id, title, username, added_by, message_after_pay, status, added_at)
            VALUES (?, ?, ?, ?, 1, 'active', ?)
            ON CONFLICT(chat_id) DO UPDATE SET title = ?, username = ?, status = 'active'
        """, (chat_id, title or "Channel", clean_un, added_by, now, title or "Channel", clean_un))
        conn.commit()
        conn.close()
    return True

def get_channel_gateway(chat_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
    return dict(row) if row else None

def toggle_channel_message_after_pay(chat_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT message_after_pay FROM channels WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        current = int(row['message_after_pay']) if row and row['message_after_pay'] is not None else 1
        new_val = 0 if current == 1 else 1
        cursor.execute("UPDATE channels SET message_after_pay = ? WHERE chat_id = ?", (new_val, chat_id))
        conn.commit()
        conn.close()
    return new_val

def find_channel_by_target(target_str):
    if not target_str:
        return None
    clean = str(target_str).strip().lstrip('@').lower()
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        if clean.lstrip('-').isdigit():
            cursor.execute("SELECT * FROM channels WHERE chat_id = ?", (int(clean),))
            row = cursor.fetchone()
            if row:
                conn.close()
                return dict(row)
        cursor.execute("SELECT * FROM channels WHERE LOWER(username) = ?", (clean,))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)
        conn.close()
    return None
