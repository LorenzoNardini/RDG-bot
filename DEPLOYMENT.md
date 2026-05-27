# RDG Bot — Deployment Guide

## Quick Start (Local Development)

```bash
cd "RDG Bot"
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your BOT_TOKEN from @BotFather
python data/seed.py    # One-time: load recipes
python main.py         # Start polling
```

## Getting a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow prompts
3. Copy the token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Paste into `.env` as `BOT_TOKEN=...`

## Deployment Options

### Option 1: VPS / Dedicated Server (Recommended for reliability)

```bash
# 1. SSH into server
ssh user@your.server.com

# 2. Clone project
git clone https://github.com/your-repo/rdg-bot.git
cd rdg-bot

# 3. Create Python venv
python3.12 -m venv venv
source venv/bin/activate

# 4. Install & configure
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real BOT_TOKEN

# 5. Seed database
python data/seed.py

# 6. Run with supervisor (for auto-restart)
pip install supervisor
# Configure supervisor.conf and start
supervisorctl start rdg-bot

# Or use tmux for manual session
tmux new-session -d -s rdg-bot "python main.py"
```

### Option 2: Railway.app (Easiest)

```bash
# 1. Create account at railway.app
# 2. Connect GitHub repo
# 3. Add environment variables:
#    BOT_TOKEN=<your-token>
#    DATABASE_URL=postgresql://...  (Railway provides free postgres)
# 4. Deploy on push
```

### Option 3: Render.com

```bash
# 1. Create account at render.com
# 2. Create new "Web Service"
# 3. Connect GitHub repo
# 4. Build: pip install -r requirements.txt
# 5. Start: python main.py
# 6. Add env vars (BOT_TOKEN, DATABASE_URL)
```

### Option 4: Fly.io

```bash
# 1. Install fly CLI
# 2. Run: flyctl launch
# 3. Configure fly.toml with PORT=8000
# 4. Set env vars with: flyctl secrets set BOT_TOKEN=...
# 5. Deploy: flyctl deploy
```

### Option 5: Raspberry Pi (Home server)

```bash
# 1. Install Python 3.12+ on Pi
# 2. Follow VPS setup above
# 3. Use systemd service for auto-start:

sudo tee /etc/systemd/system/rdg-bot.service > /dev/null <<EOF
[Unit]
Description=RDG Telegram Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rdg-bot
ExecStart=/home/pi/rdg-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable rdg-bot
sudo systemctl start rdg-bot
```

## Production Considerations

### Database

For production, use PostgreSQL instead of SQLite:

```bash
# 1. Install PostgreSQL
sudo apt install postgresql

# 2. Create database
sudo -u postgres createdb rdg_bot

# 3. Update .env
DATABASE_URL=postgresql://postgres:password@localhost/rdg_bot

# 4. Run seed
python data/seed.py
```

### Logging

Add to `main.py` for better debugging:

```python
logging.basicConfig(
    filename='rdg_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Backups

```bash
# Backup SQLite database
cp rdg_bot.db rdg_bot.db.backup

# Or backup PostgreSQL
pg_dump rdg_bot > backup.sql
```

### Monitoring

Add periodic checks:

```bash
# Monitor bot health with a health check script
# Run every 5 minutes via cron

*/5 * * * * /home/user/rdg-bot/health_check.sh
```

## Troubleshooting Deployment

### Bot doesn't start

```bash
# Check for errors
python main.py

# Look for:
# - BOT_TOKEN not set
# - Database connection error
# - Module import error
```

### Database issues

```bash
# Reset database (WARNING: deletes all data)
rm rdg_bot.db
python data/seed.py
```

### Memory issues on small servers

- Switch from polling to webhooks (advanced)
- Use PostgreSQL instead of SQLite
- Reduce log verbosity

## Monitoring & Alerts

### Simple health check

```bash
#!/bin/bash
# health_check.sh

LOGFILE="/var/log/rdg-bot/bot.log"
ERROR_COUNT=$(tail -100 $LOGFILE | grep -c "ERROR")

if [ "$ERROR_COUNT" -gt 5 ]; then
    echo "Bot has errors, restarting..."
    systemctl restart rdg-bot
fi
```

### Use monitoring service

- **Uptime Robot** (free): Monitor HTTP endpoint
- **New Relic**: Full APM
- **DataDog**: Distributed tracing

## Updating the Bot

```bash
# 1. Pull latest code
git pull origin main

# 2. Install new dependencies (if any)
pip install -r requirements.txt

# 3. Run migrations/updates
python data/seed.py  # Safe to run multiple times

# 4. Restart bot
systemctl restart rdg-bot
```

## Scaling

For multiple users/high load:

1. Switch to PostgreSQL with connection pooling (pgBouncer)
2. Use Kubernetes (Fly.io, EKS) for auto-scaling
3. Add caching layer (Redis) for recipe queries
4. Use webhook instead of polling for faster response

## Cost Estimates

| Platform | Cost | Notes |
|----------|------|-------|
| VPS (Linode/DigitalOcean) | $5-10/month | Most reliable, full control |
| Railway | $5/month free tier | Easy to deploy, auto-scales |
| Render | Free tier available | Sleeps after 15 min inactivity |
| Fly.io | Free tier available | Fast, global deployment |
| Raspberry Pi | $50 one-time | Home server option |

## Questions?

- Check logs: `tail -f rdg_bot.log`
- Verify token: Works with `curl https://api.telegram.org/botTOKEN/getMe`
- Test locally first: `python main.py` on your machine
