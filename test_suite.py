# -*- coding: utf-8 -*-
"""
Trappy Testnet  - Test Suite
Verifies:
1. 3 cryptos: USDT, TRX, TRAPPY
2. Exact wallet text formatting
3. Photo mention matching: $10 @username Comment...
4. P2P transfers & owner unlimited giveaways
"""
import unittest
import database as db
import config
from bot import MENTION_DOLLAR_PAY_REGEX, MENTION_PAY_REGEX, MENTION_GIVEAWAY_REGEX, render_wallet_text

class TestTrappyTestnet3Cryptos(unittest.TestCase):
    def setUp(self):
        db.init_db()
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users")
        cur.execute("DELETE FROM balances")
        cur.execute("DELETE FROM transfers")
        cur.execute("DELETE FROM giveaways")
        cur.execute("DELETE FROM giveaway_claims")
        cur.execute("DELETE FROM faucet_claims")
        conn.commit()
        conn.close()

    def test_three_cryptos_only(self):
        uid = 9051090063
        user = db.get_or_create_user(uid, "trappyfather", "Trappy Admin")
        self.assertIsNotNone(user)
        
        # Verify only 3 cryptos exist in config
        self.assertEqual(set(config.SUPPORTED_CRYPTOS.keys()), {'USDT', 'TRX', 'TRAPPY'})
        
        # Test adding TRAPPY token
        ok, bal = db.add_crypto(uid, 'TRAPPY', 5000.0)
        self.assertTrue(ok)
        self.assertEqual(bal, 5000.0)
        
        balances = db.get_all_balances(uid)
        self.assertEqual(balances['TRAPPY'], 5000.0)
        self.assertEqual(balances['USDT'], 0.0)
        self.assertEqual(balances['TRX'], 0.0)

    def test_exact_wallet_rendering(self):
        uid = 6666001
        db.get_or_create_user(uid, "wallet_user", "Tester")
        
        rendered = render_wallet_text(uid)
        self.assertIn("👛 <b>Wallet</b>", rendered)
        self.assertIn("<b>Tether</b>: 0 USDT", rendered)
        self.assertIn("<b>TRON</b>: 0 TRX", rendered)
        self.assertIn("<b>Trappy</b>: 0 TRAPPY", rendered)
        self.assertIn("≈ $0.00", rendered)
        
        # Ensure removed cryptos are NOT in wallet
        self.assertNotIn("Bitcoin", rendered)
        self.assertNotIn("Ethereum", rendered)
        self.assertNotIn("Dogecoin", rendered)

    def test_photo_dollar_mention_regex(self):
        # Matching user reference photo: @CryptoTestnetBot $10 @username Comment...
        text1 = "@CryptoTestnetBot $10 @username Comment..."
        m1 = MENTION_DOLLAR_PAY_REGEX.search(text1)
        self.assertIsNotNone(m1)
        self.assertEqual(m1.group(1), "10")
        self.assertEqual(m1.group(2), "username")
        self.assertEqual(m1.group(3), "Comment...")

        # Also matching @TrappyTestnet $10 @alex for pizza
        text2 = "@TrappyTestnet $10 @alex for pizza"
        m2 = MENTION_DOLLAR_PAY_REGEX.search(text2)
        self.assertIsNotNone(m2)
        self.assertEqual(m2.group(1), "10")
        self.assertEqual(m2.group(2), "alex")
        self.assertEqual(m2.group(3), "for pizza")

        # Also simple: $50 @someuser
        text3 = "$50 @someuser"
        m3 = MENTION_DOLLAR_PAY_REGEX.search(text3)
        self.assertIsNotNone(m3)
        self.assertEqual(m3.group(1), "50")
        self.assertEqual(m3.group(2), "someuser")

    def test_trappy_token_transfer(self):
        u1 = 6666002
        u2 = 6666003
        db.get_or_create_user(u1, "sender", "Sender")
        db.get_or_create_user(u2, "receiver", "Receiver")
        
        db.add_crypto(u1, 'TRAPPY', 1000.0)
        ok, res = db.transfer_crypto(u1, u2, 'TRAPPY', 400.0, note="Lunch")
        self.assertTrue(ok)
        self.assertEqual(db.get_balance(u1, 'TRAPPY'), 600.0)
        self.assertEqual(db.get_balance(u2, 'TRAPPY'), 400.0)

    def test_owner_unlimited_giveaway(self):
        owner_id = 9051090063
        normal_id = 6666004
        db.get_or_create_user(owner_id, "trappyfather", "Owner")
        db.get_or_create_user(normal_id, "normal", "Normal")
        
        # Owner creates 1,000,000 TRAPPY giveaway with 0 balance
        ok, _, gw_id = db.create_giveaway(owner_id, 'TRAPPY', 1000000.0, 10)
        self.assertTrue(ok)
        
        # Normal user cannot exceed balance
        ok2, err, _ = db.create_giveaway(normal_id, 'TRAPPY', 100.0, 2)
        self.assertFalse(ok2)
        self.assertEqual(err, "insufficient_balance")

    def test_channel_registration(self):
        db.register_channel(-1001234567890, "Test Channel", "testchannel", 9051090063)
        channels = db.get_active_channels()
        self.assertTrue(any(c['chat_id'] == -1001234567890 for c in channels))
        db.unregister_channel(-1001234567890)
        self.assertFalse(any(c['chat_id'] == -1001234567890 for c in db.get_active_channels()))

    def test_channel_message_sender_none_safe(self):
        from bot import get_message_sender
        from unittest.mock import MagicMock
        
        # Channel post mock where from_user is None
        msg = MagicMock()
        msg.from_user = None
        msg.sender_chat = MagicMock()
        msg.sender_chat.title = "Trappy Channel"
        msg.sender_chat.username = "trappytestnet"
        
        uid, uname, disp = get_message_sender(msg)
        self.assertEqual(uid, config.OWNER_IDS[0])
        self.assertEqual(uname, "trappytestnet")
        self.assertEqual(disp, "@trappytestnet")

    def test_realistic_addresses_and_cheques_invoices(self):
        u1 = 7777001
        u2 = 7777002
        user1 = db.get_or_create_user(u1, "cheque_creator", "Creator")
        user2 = db.get_or_create_user(u2, "cheque_claimer", "Claimer")
        
        # 1. Realistic TRC-20 & Trappy Native Address checks
        self.assertTrue(user1['tron_address'].startswith('T'))
        self.assertEqual(len(user1['tron_address']), 34)
        self.assertTrue(user1['trappy_address'].startswith('trp1'))
        self.assertEqual(len(user1['trappy_address']), 42)
        
        # Find user by realistic address
        self.assertEqual(db.find_user(user1['tron_address'])['user_id'], u1)
        self.assertEqual(db.find_user(user1['trappy_address'])['user_id'], u1)
        
        # 2. Cheque Engine
        db.add_crypto(u1, 'USDT', 100.0)
        ok, res, ch_id = db.create_cheque(u1, 'USDT', 50.0, 1, note="Coffee")
        self.assertTrue(ok)
        self.assertEqual(db.get_balance(u1, 'USDT'), 50.0)
        
        # Claim cheque
        ok_claim, _, amt, curr, rem = db.claim_cheque(ch_id, u2)
        self.assertTrue(ok_claim)
        self.assertEqual(amt, 50.0)
        self.assertEqual(db.get_balance(u2, 'USDT'), 50.0)
        
        # 3. Invoice Engine
        ok_iv, _, iv_id = db.create_invoice(u1, 'TRAPPY', 200.0, note="Service")
        self.assertTrue(ok_iv)
        db.add_crypto(u2, 'TRAPPY', 500.0)
        ok_pay, _, p_amt, p_curr, _ = db.pay_invoice(iv_id, u2)
        self.assertTrue(ok_pay)
        self.assertEqual(db.get_balance(u2, 'TRAPPY'), 300.0)
        self.assertEqual(db.get_balance(u1, 'TRAPPY'), 200.0)

if __name__ == '__main__':
    unittest.main()
