# -*- coding: utf-8 -*-
"""
Trappy Testnet  - Bilingual Localization (English & Russian)
Authentic 2022-2024 Telegram prime crypto earning bot aesthetics.
"""

TEXTS = {
    'en': {
        'welcome': (
            "🔥 <b>Welcome to Trappy Testnet !</b> 🔥\n\n"
            "The legendary Telegram earning bot is back with refreshed mechanics!\n"
            "Earn <b>Testnet USDT</b> by mining, claiming daily bonuses, completing quests, and inviting friends.\n\n"
            "💎 <b>Exchange Rate:</b> 1,000 Testnet = <b>$0.01 Real USDT</b>\n"
            "⚡ Fast withdrawals directly to your TON / BSC / TRC-20 wallet!\n\n"
            "📢 <b>Official Channel:</b> @trappytg\n"
            "🤖 <b>Ecosystem Bot:</b> @trappyb0t\n\n"
            "Use the menu below to start earning!"
        ),
        'welcome_ref': (
            "\n🎁 <i>You were invited by a friend! +{bonus} Testnet USDT welcome gift added to your balance!</i>"
        ),
        'main_menu': (
            "🚀 <b>TRAPPY TESTNET  DASHBOARD</b>\n\n"
            "👤 <b>User:</b> {first_name} (<code>{user_id}</code>)\n"
            "⚡ <b>Testnet Balance:</b> <code>{testnet:,.2f}</code> Testnet\n"
            "💵 <b>Real USDT Balance:</b> <code>${usdt:,.4f}</code> USDT\n"
            "📈 <b>Exchange Rate:</b> 1,000 Testnet = $0.01 USDT\n"
            "🔋 <b>Energy:</b> {energy}/{max_energy} ⚡\n\n"
            "Select an action from the keyboard below:"
        ),
        'btn_mine': "⛏️ Mine / Tap",
        'btn_balance': "💼 Balance & Wallet",
        'btn_exchange': "🔄 Exchange (1k = $0.01)",
        'btn_withdraw': "💸 Withdraw",
        'btn_bonus': "🎁 Daily Bonus",
        'btn_referral': "👥 Referrals",
        'btn_tasks': "🎯 Tasks & Quests",
        'btn_games': "🎲 Mini-Games",
        'btn_leaderboard': "🏆 Leaderboard",
        'btn_settings': "⚙️ Settings & Info",
        
        # Mine / Tap
        'mine_title': (
            "⛏️ <b>TRAPPY MINING RIG </b>\n\n"
            "Choose your mining method:\n\n"
            "1️⃣ <b>Passive Mining Rig:</b> Claim {amount} Testnet every {cooldown_mins} minutes.\n"
            "2️⃣ <b>Turbo Tapper:</b> Tap to mine {tap_reward} Testnet per tap using your Energy!\n\n"
            "🔋 <b>Current Energy:</b> {energy}/{max_energy} (Recharges 1⚡ / min)\n"
            "⏳ <b>Mining Rig Status:</b> {rig_status}"
        ),
        'mine_rig_ready': "✅ Ready to claim!",
        'mine_rig_cooling': "⏳ Cooling down: {mins}m {secs}s",
        'mine_success': "🎉 <b>Mining Success!</b>\nYou extracted <b>+{amount} Testnet USDT</b>!",
        'mine_cooldown': "⏳ Mining rig is cooling down. Please wait <b>{mins}m {secs}s</b>.",
        'tap_success': "⚡ <b>Tap!</b> +{reward} Testnet USDT! (Energy: {energy}/{max_energy})",
        'tap_no_energy': "⚠️ Out of energy! Wait a few minutes for energy to recharge.",
        
        # Balance
        'balance_info': (
            "💼 <b>YOUR WALLET & ASSETS</b>\n\n"
            "🪙 <b>Testnet USDT:</b> <code>{testnet:,.2f}</code>\n"
            "   └ <i>Estimated value:</i> <code>${est_value:,.4f} USDT</code>\n\n"
            "💵 <b>Exchangeable Real USDT:</b> <code>${usdt:,.4f}</code>\n"
            "   └ <i>Ready for payout!</i>\n\n"
            "📍 <b>Payout Wallet:</b> <code>{wallet}</code>\n"
            "🌐 <b>Network:</b> {network}\n\n"
            "📊 <b>Lifetime Stats:</b>\n"
            "• Total Mined: <code>{total_mined:,.0f}</code> Testnet\n"
            "• Total Exchanged: <code>{total_exchanged:,.0f}</code> Testnet\n"
            "• Total Paid Out: <code>${total_withdrawn:,.4f}</code> USDT\n"
            "• Referrals: <code>{ref_count}</code> users"
        ),
        'btn_set_wallet': "💳 Set / Change Wallet",
        'enter_wallet_prompt': "✍️ <b>Enter your crypto wallet address:</b>\n(e.g., TON address or BSC / TRC-20 USDT address)",
        'wallet_saved': "✅ <b>Wallet saved!</b>\nAddress: <code>{wallet}</code>\nNetwork: {network}",
        
        # Exchange
        'exchange_info': (
            "🔄 <b>TRAPPY TESTNET SWAP </b>\n\n"
            "Convert your Testnet tokens into Real USDT at the official rate:\n"
            "💎 <b>1,000 Testnet USDT = $0.01 Real USDT</b>\n"
            "<i>(10,000 Testnet = $0.10 USDT | 100,000 Testnet = $1.00 USDT)</i>\n\n"
            "🪙 <b>Your Testnet Balance:</b> <code>{testnet:,.2f}</code>\n"
            "💵 <b>Your Real USDT Balance:</b> <code>${usdt:,.4f}</code>\n\n"
            "Minimum exchange amount: <b>1,000 Testnet</b> ($0.01 USDT).\n"
            "Choose an amount to swap instantly:"
        ),
        'exchange_success': (
            "✅ <b>Exchange Successful!</b>\n\n"
            "Swapped: <b>{amount:,.0f} Testnet</b>\n"
            "Received: <b>+${usdt:,.4f} Real USDT</b>\n\n"
            "New Real USDT Balance: <code>${new_usdt:,.4f}</code>\n"
            "Remaining Testnet: <code>{new_testnet:,.2f}</code>"
        ),
        'exchange_not_enough': "❌ You don't have enough Testnet USDT! Minimum swap is 1,000 Testnet.",
        'btn_swap_1k': "Swap 1,000 Testnet ($0.01)",
        'btn_swap_5k': "Swap 5,000 Testnet ($0.05)",
        'btn_swap_10k': "Swap 10,000 Testnet ($0.10)",
        'btn_swap_all': "Swap All Testnet",
        
        # Withdraw
        'withdraw_info': (
            "💸 <b>REQUEST CRYPTO WITHDRAWAL</b>\n\n"
            "Real USDT balance: <b>${usdt:,.4f} USDT</b>\n"
            "Minimum withdrawal: <b>${min_withdraw:,.2f} USDT</b>\n"
            "Wallet: <code>{wallet}</code> ({network})\n\n"
            "{wallet_warning}"
            "Withdrawals are processed manually or via batch transfer by @trappyfather."
        ),
        'withdraw_no_wallet': "⚠️ Please set your wallet address first via Balance menu!",
        'withdraw_low_balance': "❌ Your real USDT balance is below the minimum ${min_withdraw:,.2f} USDT.",
        'withdraw_pending_exists': "⚠️ You already have a pending withdrawal request! Please wait for it to be processed.",
        'withdraw_confirm_prompt': (
            "⚠️ <b>Confirm Withdrawal:</b>\n\n"
            "Amount: <b>${amount:,.4f} USDT</b>\n"
            "Destination: <code>{wallet}</code>\n"
            "Network: <b>{network}</b>\n\n"
            "Are you sure you want to submit this request?"
        ),
        'withdraw_submitted': (
            "🚀 <b>Withdrawal Request Submitted!</b>\n\n"
            "Amount: <b>${amount:,.4f} USDT</b>\n"
            "Wallet: <code>{wallet}</code> ({network})\n"
            "Status: ⏳ <b>Pending Admin Approval</b>\n\n"
            "You will be notified once the transaction is broadcasted!"
        ),
        
        # Bonus
        'bonus_title': (
            "🎁 <b>DAILY STREAK BONUS</b>\n\n"
            "Log in and claim your reward every 24 hours to build your streak!\n\n"
            "📅 <b>Your Current Streak:</b> Day {streak} / 7\n\n"
            "Reward Table:\n"
            "• Day 1: 50 Testnet\n"
            "• Day 2: 100 Testnet\n"
            "• Day 3: 200 Testnet\n"
            "• Day 4: 350 Testnet\n"
            "• Day 5: 500 Testnet\n"
            "• Day 6: 750 Testnet\n"
            "• Day 7+: <b>1,000 Testnet</b> 🔥\n\n"
            "{bonus_status}"
        ),
        'bonus_claimed': "🎉 <b>Daily Bonus Claimed!</b>\nDay {streak} reward: <b>+{reward} Testnet USDT</b> added!",
        'bonus_already_claimed': "⏳ You already claimed today's bonus! Next claim available in <b>{hours}h {mins}m</b>.",
        'btn_claim_bonus': "🎁 Claim Daily Bonus",
        
        # Referrals
        'referral_info': (
            "👥 <b>INVITE & EARN PROGRAM</b>\n\n"
            "Spread the word about Trappy Testnet  and earn massive rewards!\n\n"
            "🎁 <b>Referral Rewards:</b>\n"
            "• <b>+{bonus} Testnet USDT</b> instantly for every friend who joins!\n"
            "• <b>{commission}% Lifetime Commission</b> on all friends' mining claims & swaps!\n"
            "• Your friend receives <b>+{friend_bonus} Testnet USDT</b> as a welcome gift!\n\n"
            "📊 <b>Your Referral Stats:</b>\n"
            "• Friends Invited: <b>{count}</b>\n"
            "• Total Referral Earnings: <b>{earnings:,.2f} Testnet</b>\n\n"
            "🔗 <b>Your Exclusive Referral Link:</b>\n"
            "<code>{ref_link}</code>"
        ),
        'btn_share_ref': "📲 Share with Friends",
        
        # Tasks
        'tasks_title': (
            "🎯 <b>COMMUNITY TASKS & BOUNTIES</b>\n\n"
            "Complete official tasks to earn big Testnet rewards instantly!"
        ),
        'task_done': "✅ Completed",
        'task_claim': "Claim +{reward} Testnet",
        'task_completed_msg': "🎉 Task completed! <b>+{reward} Testnet USDT</b> credited to your balance!",
        'task_not_joined': "❌ Verification failed. Please make sure you have joined @trappytg first!",
        
        # Mini-games
        'games_title': (
            "🎲 <b>TESTNET MINI-CASINO</b>\n\n"
            "Multiply your Testnet USDT with fun instant games:\n\n"
            "1️⃣ <b>🎲 Lucky Dice:</b> Roll 4, 5, or 6 to DOUBLE your bet! (2x payout)\n"
            "2️⃣ <b>🪙 Coin Flip:</b> Pick Heads or Tails for a 50/50 double! (2x payout)\n"
            "3️⃣ <b>🎰 Slot Machine:</b> Spin the telegram slot reels! (Up to 5x jackpot!)\n\n"
            "Select a game below:"
        ),
        'bet_prompt': "Choose your bet amount:",
        'game_win': "🎉 <b>YOU WON!</b> +{win_amount} Testnet USDT!",
        'game_lose': "😢 <b>You lost!</b> Better luck next time!",
        'game_not_enough': "❌ You don't have enough Testnet USDT to place this bet!",
        
        # Leaderboard
        'leaderboard_title': (
            "🏆 <b>TRAPPY TOP HOLDERS LEADERBOARD</b>\n\n"
            "The top 10 richest Trappy Testnet tycoons:\n\n"
            "{rankings}\n\n"
            "Keep mining and inviting to reach the top!"
        ),
        
        # Settings & Help
        'settings_title': (
            "⚙️ <b>SETTINGS & COMMUNITY</b>\n\n"
            "🤖 <b>Bot Version:</b> Trappy Testnet \n"
            "⚡ <b>Architecture:</b> High-speed Python SQLite Engine\n"
            "👑 <b>Founder:</b> @trappyfather\n\n"
            "🔗 <b>Official Links:</b>\n"
            "• Main Channel: @trappytg\n"
            "• Ecosystem Bot: @trappyb0t\n\n"
            "🌐 Choose your preferred language below:"
        ),
        'btn_lang_en': "🇬🇧 English",
        'btn_lang_ru': "🇷🇺 Русский",
        'lang_switched': "✅ Language updated to English!",
        
        # Admin
        'admin_only': "⛔ This command is restricted to the bot owner.",
        'admin_dashboard': (
            "👑 <b>TRAPPY TESTNET  - ADMIN DASHBOARD</b>\n\n"
            "📊 <b>Total Users:</b> <code>{total_users}</code>\n"
            "⛏️ <b>Total Testnet Minted:</b> <code>{total_testnet:,.2f}</code>\n"
            "💵 <b>Total Real USDT Balance:</b> <code>${total_usdt:,.4f}</code>\n"
            "⏳ <b>Pending Withdrawals:</b> <code>{pending_count}</code> (${pending_amount:,.4f} USDT)\n"
            "💸 <b>Total Paid Out:</b> <code>${total_paid:,.4f}</code> USDT\n\n"
            "Select an administrative tool below:"
        ),
        'btn_admin_withdrawals': "💳 Review Withdrawals ({count})",
        'btn_admin_broadcast': "📢 Broadcast Message",
        'btn_admin_stats': "📊 Detailed Stats"
    },
    
    'ru': {
        'welcome': (
            "🔥 <b>Добро пожаловать в Trappy Testnet !</b> 🔥\n\n"
            "Легендарный Telegram-бот эпохи расцвета вернулся с обновленной механикой!\n"
            "Зарабатывай <b>Testnet USDT</b> на майнинге, ежедневных бонусах, квестах и приглашении друзей.\n\n"
            "💎 <b>Курс обмена:</b> 1,000 Testnet = <b>$0.01 Real USDT</b>\n"
            "⚡ Быстрый вывод прямо на твой TON / BSC / TRC-20 кошелек!\n\n"
            "📢 <b>Официальный канал:</b> @trappytg\n"
            "🤖 <b>Экосистема бота:</b> @trappyb0t\n\n"
            "Используй меню ниже, чтобы начать зарабатывать прямо сейчас!"
        ),
        'welcome_ref': (
            "\n🎁 <i>Вы пришли по приглашению друга! +{bonus} Testnet USDT приветственный бонус начислен!</i>"
        ),
        'main_menu': (
            "🚀 <b>TRAPPY TESTNET  — ГЛАВНОЕ МЕНЮ</b>\n\n"
            "👤 <b>Пользователь:</b> {first_name} (<code>{user_id}</code>)\n"
            "⚡ <b>Баланс Testnet:</b> <code>{testnet:,.2f}</code> Testnet\n"
            "💵 <b>Баланс Real USDT:</b> <code>${usdt:,.4f}</code> USDT\n"
            "📈 <b>Курс обмена:</b> 1,000 Testnet = $0.01 USDT\n"
            "🔋 <b>Энергия:</b> {energy}/{max_energy} ⚡\n\n"
            "Выбери нужный раздел на клавиатуре:"
        ),
        'btn_mine': "⛏️ Майнинг / Тап",
        'btn_balance': "💼 Баланс и Кошелек",
        'btn_exchange': "🔄 Обмен (1k = $0.01)",
        'btn_withdraw': "💸 Вывод средств",
        'btn_bonus': "🎁 Ежедневный бонус",
        'btn_referral': "👥 Рефералы",
        'btn_tasks': "🎯 Задания и Квесты",
        'btn_games': "🎲 Мини-игры",
        'btn_leaderboard': "🏆 Топ лидеров",
        'btn_settings': "⚙️ Настройки и Инфо",
        
        # Mine / Tap
        'mine_title': (
            "⛏️ <b>МАЙНИНГ-ФЕРМА TRAPPY </b>\n\n"
            "Выбери способ добычи:\n\n"
            "1️⃣ <b>Пассивная ферма:</b> Забирай {amount} Testnet каждые {cooldown_mins} мин.\n"
            "2️⃣ <b>Турбо-Тапер:</b> Тапай и получай {tap_reward} Testnet за клик за счёт энергии!\n\n"
            "🔋 <b>Текущая энергия:</b> {energy}/{max_energy} (Восстановление 1⚡ / мин)\n"
            "⏳ <b>Статус фермы:</b> {rig_status}"
        ),
        'mine_rig_ready': "✅ Готово к сбору!",
        'mine_rig_cooling': "⏳ Остывает: {mins}м {secs}с",
        'mine_success': "🎉 <b>Успешный сбор!</b>\nВы добыли <b>+{amount} Testnet USDT</b>!",
        'mine_cooldown': "⏳ Ферма перезаряжается. Подождите <b>{mins}м {secs}с</b>.",
        'tap_success': "⚡ <b>Тап!</b> +{reward} Testnet USDT! (Энергия: {energy}/{max_energy})",
        'tap_no_energy': "⚠️ Закончилась энергия! Подождите пару минут для восстановления.",
        
        # Balance
        'balance_info': (
            "💼 <b>ВАШ КОШЕЛЕК И АКТИВЫ</b>\n\n"
            "🪙 <b>Testnet USDT:</b> <code>{testnet:,.2f}</code>\n"
            "   └ <i>Примерная стоимость:</i> <code>${est_value:,.4f} USDT</code>\n\n"
            "💵 <b>Доступно к выводу (Real USDT):</b> <code>${usdt:,.4f}</code>\n"
            "   └ <i>Готово к выплате на кошелек!</i>\n\n"
            "📍 <b>Кошелек для вывода:</b> <code>{wallet}</code>\n"
            "🌐 <b>Сеть:</b> {network}\n\n"
            "📊 <b>Ваша статистика:</b>\n"
            "• Всего намайнено: <code>{total_mined:,.0f}</code> Testnet\n"
            "• Всего обменяно: <code>{total_exchanged:,.0f}</code> Testnet\n"
            "• Всего выведено: <code>${total_withdrawn:,.4f}</code> USDT\n"
            "• Приглашено друзей: <code>{ref_count}</code> чел."
        ),
        'btn_set_wallet': "💳 Указать / Сменить кошелек",
        'enter_wallet_prompt': "✍️ <b>Введите адрес вашего криптокошелька:</b>\n(например, TON адрес или BSC / TRC-20 USDT адрес)",
        'wallet_saved': "✅ <b>Кошелек сохранен!</b>\nАдрес: <code>{wallet}</code>\nСеть: {network}",
        
        # Exchange
        'exchange_info': (
            "🔄 <b>ОБМЕННИК TRAPPY TESTNET </b>\n\n"
            "Конвертируйте заработанные токены Testnet в реальный USDT по легендарному курсу:\n"
            "💎 <b>1,000 Testnet USDT = $0.01 Real USDT</b>\n"
            "<i>(10,000 Testnet = $0.10 USDT | 100,000 Testnet = $1.00 USDT)</i>\n\n"
            "🪙 <b>Ваш баланс Testnet:</b> <code>{testnet:,.2f}</code>\n"
            "💵 <b>Ваш баланс Real USDT:</b> <code>${usdt:,.4f}</code>\n\n"
            "Минимальная сумма обмена: <b>1,000 Testnet</b> ($0.01 USDT).\n"
            "Выберите сумму для мгновенного обмена:"
        ),
        'exchange_success': (
            "✅ <b>Обмен успешно выполнен!</b>\n\n"
            "Обменяно: <b>{amount:,.0f} Testnet</b>\n"
            "Получено: <b>+${usdt:,.4f} Real USDT</b>\n\n"
            "Новый баланс USDT: <code>${new_usdt:,.4f}</code>\n"
            "Остаток Testnet: <code>{new_testnet:,.2f}</code>"
        ),
        'exchange_not_enough': "❌ Недостаточно Testnet USDT! Минимальный обмен — 1,000 Testnet.",
        'btn_swap_1k': "Обменять 1,000 Testnet ($0.01)",
        'btn_swap_5k': "Обменять 5,000 Testnet ($0.05)",
        'btn_swap_10k': "Обменять 10,000 Testnet ($0.10)",
        'btn_swap_all': "Обменять всё доступное",
        
        # Withdraw
        'withdraw_info': (
            "💸 <b>ЗАПРОС НА ВЫВОД КРИПТОВАЛЮТЫ</b>\n\n"
            "Баланс Real USDT: <b>${usdt:,.4f} USDT</b>\n"
            "Минимум для вывода: <b>${min_withdraw:,.2f} USDT</b>\n"
            "Кошелек: <code>{wallet}</code> ({network})\n\n"
            "{wallet_warning}"
            "Заявки обрабатываются создателем бота @trappyfather."
        ),
        'withdraw_no_wallet': "⚠️ Сначала укажите адрес кошелька в разделе Баланс!",
        'withdraw_low_balance': "❌ Баланс ниже минимальной суммы вывода ${min_withdraw:,.2f} USDT.",
        'withdraw_pending_exists': "⚠️ У вас уже есть активная заявка на вывод! Дождитесь её обработки.",
        'withdraw_confirm_prompt': (
            "⚠️ <b>Подтверждение заявки на вывод:</b>\n\n"
            "Сумма: <b>${amount:,.4f} USDT</b>\n"
            "Кошелек: <code>{wallet}</code>\n"
            "Сеть: <b>{network}</b>\n\n"
            "Отправить заявку администратору?"
        ),
        'withdraw_submitted': (
            "🚀 <b>Заявка на вывод отправлена!</b>\n\n"
            "Сумма: <b>${amount:,.4f} USDT</b>\n"
            "Кошелек: <code>{wallet}</code> ({network})\n"
            "Статус: ⏳ <b>Ожидает подтверждения администратором</b>\n\n"
            "Вы получите уведомление, как только средства будут отправлены!"
        ),
        
        # Bonus
        'bonus_title': (
            "🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС ЗА СТРИК</b>\n\n"
            "Заходи в бот каждый день и забирай растущий бонус!\n\n"
            "📅 <b>Твой текущий стрик:</b> День {streak} / 7\n\n"
            "Таблица наград:\n"
            "• День 1: 50 Testnet\n"
            "• День 2: 100 Testnet\n"
            "• День 3: 200 Testnet\n"
            "• День 4: 350 Testnet\n"
            "• День 5: 500 Testnet\n"
            "• День 6: 750 Testnet\n"
            "• День 7+: <b>1,000 Testnet</b> 🔥\n\n"
            "{bonus_status}"
        ),
        'bonus_claimed': "🎉 <b>Ежедневный бонус получен!</b>\nНаграда за День {streak}: <b>+{reward} Testnet USDT</b>!",
        'bonus_already_claimed': "⏳ Вы уже забрали бонус за сегодня! Следующий доступен через <b>{hours}ч {mins}м</b>.",
        'btn_claim_bonus': "🎁 Забрать ежедневный бонус",
        
        # Referrals
        'referral_info': (
            "👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n\n"
            "Приглашай друзей в Trappy Testnet  и зарабатывай вместе с ними!\n\n"
            "🎁 <b>Условия программы:</b>\n"
            "• <b>+{bonus} Testnet USDT</b> сразу за каждого приглашенного друга!\n"
            "• <b>{commission}% пожизненная комиссия</b> со всех сборов и обменов рефералов!\n"
            "• Твой друг получает <b>+{friend_bonus} Testnet USDT</b> приветственного подарка!\n\n"
            "📊 <b>Твоя статистика:</b>\n"
            "• Приглашено друзей: <b>{count}</b>\n"
            "• Заработано с рефералов: <b>{earnings:,.2f} Testnet</b>\n\n"
            "🔗 <b>Твоя реферальная ссылка:</b>\n"
            "<code>{ref_link}</code>"
        ),
        'btn_share_ref': "📲 Поделиться ссылкой",
        
        # Tasks
        'tasks_title': (
            "🎯 <b>ЗАДАНИЯ И НАГРАДЫ СООБЩЕСТВА</b>\n\n"
            "Выполняй официальные задания и получай крупные награды Testnet мгновенно!"
        ),
        'task_done': "✅ Выполнено",
        'task_claim': "Получить +{reward} Testnet",
        'task_completed_msg': "🎉 Задание выполнено! <b>+{reward} Testnet USDT</b> зачислено на баланс!",
        'task_not_joined': "❌ Проверка не пройдена. Убедитесь, что вы подписались на @trappytg!",
        
        # Mini-games
        'games_title': (
            "🎲 <b>МИНИ-КАЗИНО TESTNET</b>\n\n"
            "Испытай удачу и умножь свои Testnet токены в мгновенных играх:\n\n"
            "1️⃣ <b>🎲 Кости (Dice):</b> Выброси 4, 5 или 6 и УДВОЙ ставку! (x2)\n"
            "2️⃣ <b>🪙 Орёл или Решка:</b> Угадай сторону и забери x2!\n"
            "3️⃣ <b>🎰 Слот-Машина:</b> Испытай удачу в барабанах! (Джекпот до x5!)\n\n"
            "Выбери игру:"
        ),
        'bet_prompt': "Выбери размер ставки:",
        'game_win': "🎉 <b>ПОБЕДА!</b> +{win_amount} Testnet USDT!",
        'game_lose': "😢 <b>Не повезло!</b> Попробуй ещё раз!",
        'game_not_enough': "❌ Недостаточно Testnet USDT для этой ставки!",
        
        # Leaderboard
        'leaderboard_title': (
            "🏆 <b>ТОП-10 БОГАЧЕЙ TRAPPY TESTNET</b>\n\n"
            "Самые успешные майнеры и холдеры:\n\n"
            "{rankings}\n\n"
            "Майни активнее и приглашай друзей, чтобы занять 1 место!"
        ),
        
        # Settings & Help
        'settings_title': (
            "⚙️ <b>НАСТРОЙКИ И СООБЩЕСТВО</b>\n\n"
            "🤖 <b>Версия бота:</b> Trappy Testnet \n"
            "⚡ <b>Движок:</b> High-speed Python SQLite Engine\n"
            "👑 <b>Создатель:</b> @trappyfather\n\n"
            "🔗 <b>Официальные ссылки:</b>\n"
            "• Главный канал: @trappytg\n"
            "• Экосистема: @trappyb0t\n\n"
            "🌐 Выберите язык интерфейса:"
        ),
        'btn_lang_en': "🇬🇧 English",
        'btn_lang_ru': "🇷🇺 Русский",
        'lang_switched': "✅ Язык переключен на русский!",
        
        # Admin
        'admin_only': "⛔ Эта команда доступна только создателю бота.",
        'admin_dashboard': (
            "👑 <b>TRAPPY TESTNET  — ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
            "📊 <b>Всего пользователей:</b> <code>{total_users}</code>\n"
            "⛏️ <b>Всего Testnet эмитировано:</b> <code>{total_testnet:,.2f}</code>\n"
            "💵 <b>Общий баланс Real USDT:</b> <code>${total_usdt:,.4f}</code>\n"
            "⏳ <b>Ожидают вывода:</b> <code>{pending_count}</code> (${pending_amount:,.4f} USDT)\n"
            "💸 <b>Всего выплачено:</b> <code>${total_paid:,.4f}</code> USDT\n\n"
            "Инструменты управления:"
        ),
        'btn_admin_withdrawals': "💳 Заявки на вывод ({count})",
        'btn_admin_broadcast': "📢 Рассылка всем",
        'btn_admin_stats': "📊 Детальная статистика"
    }
}

def get_text(lang, key, **kwargs):
    lang_dict = TEXTS.get(lang, TEXTS['en'])
    text = lang_dict.get(key, TEXTS['en'].get(key, f'[{key}]'))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
