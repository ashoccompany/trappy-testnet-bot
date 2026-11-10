@echo off
title Trappy Testnet v1.1.5 Localhost Runner
echo ==================================================================
echo             TRAPPY TESTNET v1.1.5 LOCALHOST RUNNER
echo ==================================================================
echo Bot: @TrappyTestnetBot
echo Channel: https://t.me/trappytestnet
echo Mini App: http://127.0.0.1:8088
echo Owner TG ID: 9051090063
echo ==================================================================
cd /d "%~dp0"
python bot.py
pause
