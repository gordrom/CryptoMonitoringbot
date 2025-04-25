# Crypto Monitoring Telegram Bot

A Telegram bot that provides cryptocurrency price monitoring and forecasting capabilities.

## Features

- Real-time cryptocurrency price checking via CoinMarketCap
- Short-term price forecasts using GPT
- Price alert subscriptions
- Asynchronous operation for better performance

## Prerequisites

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- CoinMarketCap API Key
- OpenAI API Key

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
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username
CMC_API_KEY=your_coinmarketcap_api_key
OPENAI_API_KEY=your_openai_api_key
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_DEBUG=True
```

## Running the Application

1. Start the FastAPI backend:
```bash
python run_backend.py
```

2. In a separate terminal, start the Telegram bot:
```bash
python run_bot.py
```

## Usage

1. Start a chat with your bot on Telegram
2. Available commands:
   - `/start` - Show welcome message and available commands
   - `/rate` - Get current price of a cryptocurrency
   - `/forecast` - Get short-term forecast for a cryptocurrency
   - `/subscribe` - Subscribe to price alerts
   - `/unsubscribe` - Unsubscribe from alerts

## Project Structure

```
.
├── bot/                    # Telegram bot implementation
│   ├── __init__.py
│   └── bot.py
├── backend/               # FastAPI backend
│   ├── __init__.py
│   ├── app.py
│   └── services/         # Business logic services
│       ├── __init__.py
│       ├── cmc_service.py
│       ├── gpt_service.py
│       └── subscription_service.py
├── run_bot.py            # Bot entry point
├── run_backend.py        # Backend entry point
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
└── README.md            # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 