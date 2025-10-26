# 🤖 Telegram Bot (PTB v21+)

A modular **Telegram bot** built with [python-telegram-bot v21+](https://docs.python-telegram-bot.org/).  
This project demonstrates skills in Python, API integration, and bot architecture design.

---

## 🧠 About

This bot provides several features:
- 🌤 Weather forecast (via OpenWeatherMap API)
- ♈ Daily horoscope
- 💱 Currency exchange rates
- 🔮 Random daily prediction
- 🐞 Simple bug report system

It was created as a **personal pet project** to practice:
- Python development and async programming  
- Working with APIs and environment variables  
- Designing modular project architecture  
- Managing dependencies via `pyproject.toml` and `uv`

---

## ⚙️ Tech Stack

| Category | Technologies |
|-----------|---------------|
| Language | Python 3.10+ |
| Framework | python-telegram-bot v21 |
| Database | SQLite |
| APIs | OpenWeatherMap, Ninjas API |
| Tools | uv / pip, dotenv, logging, pytest |

---

## 🛠️ Installation

```bash
git clone https://github.com/Tol4es/my_bot.git
cd my_bot
uv pip install -e .
cp .env.example .env
# then add your TELEGRAM_TOKEN and API keys
