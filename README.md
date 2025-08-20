# Bybit Telegram Trading Bot

A high-performance asynchronous trading bot for Bybit with full Telegram control and hedging strategy.

## Features

- **Auto & Manual Trading**
    - **Auto:** Built-in scanner monitors Bybit markets for price/volume anomalies and sends signals.
    - **Manual:** Admins can trigger trades via Telegram commands.

- **Hedging Strategy**  
  Opens a reverse position if the market moves against the main trade by a defined percentage.

- **Modular Async Architecture**
    - `Telegram Bot`: UI for managing API keys, trades, and settings.
    - `Worker`: Handles core trading logic in background processes.
    - `Message Broker`: Redis + FastStream for service communication.

- **Telegram UI**
    - User: Start/stop trading, view positions, configure keys.
    - Admin: Manage users, global trade settings, view stats.

- **Subscription System**  
  Integrated PayKassa and FreeKassa for managing user access.




---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![FastStream](https://img.shields.io/badge/FastStream-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-%23DD0031?style=for-the-badge&logo=redis&logoColor=white)
![Aiohttp](https://img.shields.io/badge/Aiohttp-2C5282?style=for-the-badge&logo=python&logoColor=white)

---

### Getting Started

### Requirements

- Python 3.10+
- PostgreSQL
- Redis
- Poetry

### Installation

```bash
git clone https://github.com/your_username/repo_name.git
cd repo_name
poetry install
```
1. **Get necessary credentials:**
  A Telegram Bot Token from [@BotFather](https://www.google.com/url?sa=E&q=https%3A%2F%2Ft.me%2FBotFather).
2. **Configure environment variables**  
   Create a `.env` file based on `app/common/config.py`.

```
# Telegram 
BOT_TOKEN=your_telegram_bot_token
# BOT MODE: only 'pooling'
BOT_MODE=pooling
ADMIN_IDS=[12345678, 87654321]  # Telegram admin user IDs 
DEV_ID=12345678                # Dev/admin notifications  
# Trading Mode: 'auto' for scanning or 'manual' for admin signals 
TRADING_MODE=auto
# PostgreSQL 
POSTGRES_HOST=localhost 
POSTGRES_PORT=5432 
POSTGRES_USER=postgres 
POSTGRES_PASSWORD=your_pg_password 
POSTGRES_DB=bybit_bot  
# Redis
REDIS_HOST=localhost 
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=1
```


3. **Run services** (in separate terminals):

```bash
poetry run python -m app.telegram.main  # Telegram interface poetry run python -m 
app.worker.main  # Background trading logic`
```

---

## Usage

- Use `/start` in Telegram to begin.

- Configure Bybit API keys under "Exchange Setup".

- Enable trading/hedging from the main menu.

- View open positions and PnL in real time.

- use '/admin' for set trade config.

---

## Roadmap

- Multi-exchange support (Binance, OKX, etc.)

- New trading strategies

- Web dashboard with analytics

- Flexible alert system

- Spot market support


---


## Contact
[GitHub](https://github.com/sotaireange/cv)
[Linkedin](https://www.linkedin.com/in/sotaireange/)
