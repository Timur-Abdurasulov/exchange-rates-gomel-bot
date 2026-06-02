# Gomel Currency Rate Telegram Bot

Sends the best USD and EUR exchange rates from myfin.by/currency/gomel to your Telegram channel every day at 05:00 UTC.

---

## STEP 1 — Create your Telegram Bot

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts (give it a name and username).
3. BotFather will give you a **token** that looks like `7123456789:AAF...` — save it.

---

## STEP 2 — Add the bot to your channel and get the Channel ID

1. Open your Telegram channel settings → **Administrators** → Add your new bot as an admin (needs permission to **Post Messages**).
2. To get the channel ID:
   - If it's a public channel: use `@your_channel_username` directly (e.g. `@gomelrates`).
   - If it's a private channel:
     - Forward any message from the channel to **@userinfobot**.
     - It will show a number like `-1001234567890` — that's your channel ID.

---

## STEP 3 — Install Python & dependencies on your server/PC

You need **Python 3.11+**. On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip -y
```

Clone or copy the bot files to your server, then:

```bash
cd currency_bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser (one-time)
playwright install chromium
playwright install-deps chromium
```

---

## STEP 4 — Configure credentials

```bash
cp .env.example .env
nano .env
```

Fill in:
```
BOT_TOKEN=7123456789:AAF_your_actual_token
CHANNEL_ID=@gomelrates
```

Save with `Ctrl+O`, exit with `Ctrl+X`.

---

## STEP 5 — Test the bot manually

```bash
source venv/bin/activate

# Test the scraper first:
python scraper.py
# Should print: {'USD': {'buy': 2.85, 'sell': 2.84}, 'EUR': {'buy': 3.32, 'sell': 3.305}}

# Then test the full send (uncomment the test line in bot.py first):
# In bot.py, uncomment: # await send_rates()
python bot.py
# Check your Telegram channel for the message
```

---

## STEP 6 — Run as a background service (Linux systemd)

```bash
# Copy and edit the service file
sudo cp currency-bot.service /etc/systemd/system/

# Replace YOUR_LINUX_USERNAME with your actual username
sudo nano /etc/systemd/system/currency-bot.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable currency-bot
sudo systemctl start currency-bot

# Check status
sudo systemctl status currency-bot

# View logs live
journalctl -u currency-bot -f
```

---

## Alternative: Run with screen (simpler, no root needed)

```bash
sudo apt install screen -y
screen -S currencybot
source venv/bin/activate
python bot.py
# Press Ctrl+A then D to detach
# To reattach: screen -r currencybot
```

---

## Message Format

The bot sends messages like:

```
📅 02.06.2025

💵 USD
  Купить: 2.8500 BYN
  Продать: 2.8400 BYN

💶 EUR
  Купить: 3.3200 BYN
  Продать: 3.3050 BYN

_Лучшие курсы Гомеля по данным myfin.by_
```

**Buy** = best rate to sell your USD/EUR to a bank (you get the most BYN).  
**Sell** = best rate to buy USD/EUR from a bank (you pay the least BYN).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `playwright._impl._errors.Error: Executable doesn't exist` | Run `playwright install chromium` |
| `Unauthorized` from Telegram | Check BOT_TOKEN in .env |
| `Chat not found` | Make sure the bot is an admin of the channel; double-check CHANNEL_ID |
| Rates show 0.0 | The site structure may have changed — open `scraper.py` and update selectors |
| Bot stops after server reboot | Use systemd (Step 6) or add to crontab |
