# Crypto Monitoring Telegram Bot

A Telegram bot that provides cryptocurrency price monitoring and forecasting capabilities.

## Features

- Real-time cryptocurrency price checking via CoinMarketCap
- Short-term price forecasts using DeepSeek AI
- Price alert subscriptions
- Asynchronous operation for better performance
- Systemd service management for reliable operation

## Prerequisites

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- CoinMarketCap API Key
- DeepSeek API Key
- Supabase account and credentials

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd crypto-monitoring-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example` and fill in your API keys:
```bash
cp .env.example .env
```

## Configuration

Edit the `.env` file with your API keys and configuration:

```
# API Keys
API_KEY=your_api_key_here
CMC_API_KEY=your_coinmarketcap_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Server
BACKEND_HOST=localhost
BACKEND_PORT=8000
```

## Running the Application

### Development Mode

1. Start the FastAPI backend:
```bash
python run_backend.py
```

2. In a separate terminal, start the Telegram bot:
```bash
python run_bot.py
```

### Production Mode (Systemd Services)

1. Copy service files to systemd:
```bash
sudo cp crypto-monitor-backend.service /etc/systemd/system/
sudo cp crypto-monitor-bot.service /etc/systemd/system/
```

2. Reload systemd and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable crypto-monitor-backend
sudo systemctl enable crypto-monitor-bot
sudo systemctl start crypto-monitor-backend
sudo systemctl start crypto-monitor-bot
```

3. Check service status:
```bash
sudo systemctl status crypto-monitor-backend
sudo systemctl status crypto-monitor-bot
```

## Usage

1. Start a chat with your bot on Telegram
2. Available commands:
   - `/start` - Show welcome message and available commands
   - `/rate` - Get current price of a cryptocurrency
   - `/forecast` - Get short-term forecast for a cryptocurrency
   - `/subscribe` - Subscribe to price alerts
   - `/unsubscribe` - Unsubscribe from alerts
   - `/mysubs` - View your active subscriptions
   - `/history` - View price history
   - `/notifications` - View your recent notifications

## Project Structure

```
.
├── bot/                    # Telegram bot implementation
│   ├── __init__.py
│   └── bot.py
├── backend/               # FastAPI backend
│   ├── __init__.py
│   ├── app.py
│   ├── migrations/       # Database migrations
│   └── services/         # Business logic services
│       ├── __init__.py
│       ├── cmc_service.py
│       ├── deepseek_service.py
│       └── subscription_service.py
├── run_bot.py            # Bot entry point
├── run_backend.py        # Backend entry point
├── requirements.txt      # Python dependencies
├── crypto-monitor-backend.service  # Backend systemd service
├── crypto-monitor-bot.service      # Bot systemd service
├── deploy.sh            # Deployment script
├── .env.example         # Example environment variables
└── README.md            # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 