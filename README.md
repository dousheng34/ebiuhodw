# 🤖 SheerPro Bot — SheerID Verification Telegram Bot

A Telegram bot that automatically verifies users (students, military, teachers, first responders) via the [SheerID](https://www.sheerid.com) API.

## Features

- 🎓 Student, 🪖 Military, 👨‍🏫 Teacher, 🚒 First Responder verification
- Multi-step guided form via Telegram chat
- Instant verification via SheerID API
- Document upload for manual review cases
- All verification data saved to GitHub as JSON
- Deployed and monitored on Koyeb

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome screen |
| `/verify` | Start a new verification |
| `/status` | Check your current verification status |
| `/help` | Help & instructions |
| `/cancel` | Cancel ongoing verification |

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/sheerpro-bot.git
cd sheerpro-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual tokens
```

### 4. Required tokens

| Variable | How to get |
|----------|------------|
| `TELEGRAM_BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) |
| `SHEERID_ACCESS_TOKEN` | Login to [MySheerID](https://my.sheerid.com) → API Access |
| `SHEERID_PROGRAM_ID_*` | Create programs in MySheerID portal per segment |
| `GITHUB_TOKEN` | [GitHub Settings → Tokens](https://github.com/settings/tokens) with `repo` scope |
| `GITHUB_REPO` | `username/repo-name` of a repo to store `verifications.json` |

### 5. Run locally

```bash
python bot.py
```

## Deploy to Koyeb

1. Push code to GitHub
2. Go to [Koyeb Dashboard](https://app.koyeb.com) → **Create Service**
3. Choose **GitHub** → select this repo
4. Set **Build method**: Docker
5. Add all environment variables from `.env.example`
6. Set **Port**: `8080`
7. Deploy!

### Auto-deploy

This repo includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that auto-redeploys to Koyeb on every push to `main`.

Add `KOYEB_API_KEY` to your GitHub repo secrets (Settings → Secrets → Actions).

## Data Storage

All verification records are saved to a private GitHub repository as `verifications.json`:

```json
{
  "123456789": {
    "telegram_user_id": 123456789,
    "username": "john_doe",
    "verification_type": "student",
    "verification_id": "abc123...",
    "status": "success",
    "user_data": { ... },
    "created_at": "2024-01-15T10:30:00+00:00",
    "updated_at": "2024-01-15T10:30:05+00:00"
  }
}
```

## Project Structure

```
sheerpro-bot/
├── bot.py           # Main bot + conversation handlers
├── sheerid.py       # SheerID API client
├── storage.py       # GitHub data persistence
├── config.py        # Configuration & env vars
├── requirements.txt
├── Dockerfile
├── Procfile
├── .env.example
└── .github/
    └── workflows/
        └── deploy.yml  # Auto-deploy to Koyeb
```

## License

MIT
