import os
from typing import Optional, Dict
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import httpx
import logging
from backend.services.subscription_service import SubscriptionService
from backend.services.cmc_service import CMCService
from backend.services.deepseek_service import DeepSeekService

load_dotenv()

class BotStates(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_threshold = State()

class CryptoBot:
    def __init__(
        self,
        subscription_service: Optional[SubscriptionService] = None,
        cmc_service: Optional[CMCService] = None,
        deepseek_service: Optional[DeepSeekService] = None
    ):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.dp = Dispatcher()
        self.backend_url = f"http://{os.getenv('BACKEND_HOST')}:{os.getenv('BACKEND_PORT')}"
        self.api_key = os.getenv('API_KEY')
        self.user_states: Dict[int, Dict[str, str]] = {}  # user_id -> {"state": command, "ticker": ticker}
        
        # Initialize services
        self.subscription_service = subscription_service or SubscriptionService()
        self.cmc_service = cmc_service or CMCService()
        self.deepseek_service = deepseek_service or DeepSeekService()
        
        self.setup_handlers()
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def start_handler(message: Message):
            await message.answer(
                "Welcome to Crypto Monitor Bot! 🚀\n\n"
                "Available commands:\n"
                "/rate - Get current cryptocurrency price and trend\n"
                "/forecast - Get short-term price forecast\n"
                "/subscribe - Subscribe to price alerts\n"
                "/unsubscribe - Unsubscribe from alerts\n"
                "/mysubs - View your active subscriptions\n"
                "/history - View price history\n"
                "/notifications - View your recent notifications"
            )

        @self.dp.message(Command("rate"))
        async def rate_handler(message: Message):
            await message.answer("Please enter the cryptocurrency ticker (e.g., BTC):")
            self.user_states[message.from_user.id] = {"state": "rate"}

        @self.dp.message(Command("forecast"))
        async def forecast_handler(message: Message):
            await message.answer("Please enter the cryptocurrency ticker (e.g., BTC):")
            self.user_states[message.from_user.id] = {"state": "forecast"}

        @self.dp.message(Command("subscribe"))
        async def subscribe_handler(message: Message):
            await message.answer("Please enter the cryptocurrency ticker (e.g., BTC):")
            self.user_states[message.from_user.id] = {"state": "subscribe_ticker"}

        @self.dp.message(Command("unsubscribe"))
        async def unsubscribe_handler(message: Message):
            await message.answer("Please enter the cryptocurrency ticker (e.g., BTC):")
            self.user_states[message.from_user.id] = {"state": "unsubscribe"}

        @self.dp.message(Command("mysubs"))
        async def mysubs_handler(message: Message):
            await self._handle_mysubs(message)

        @self.dp.message(Command("history"))
        async def history_handler(message: Message):
            await message.answer("Please enter the cryptocurrency ticker (e.g., BTC):")
            self.user_states[message.from_user.id] = {"state": "history"}

        @self.dp.message(Command("notifications"))
        async def notifications_handler(message: Message):
            await self._handle_notifications(message)

        @self.dp.message()
        async def handle_message(message: Message):
            user_id = message.from_user.id
            if user_id not in self.user_states:
                await message.answer("Please use one of the available commands: /start, /rate, /forecast, /subscribe, /unsubscribe, /mysubs, /history, /notifications")
                return

            state = self.user_states[user_id]["state"]

            # Only validate ticker when the state expects a ticker
            if state in ["rate", "forecast", "subscribe_ticker", "unsubscribe", "history"]:
                ticker = message.text.upper()
                if not self._is_valid_ticker(ticker):
                    await message.answer("Invalid ticker format. Please use 2-5 uppercase letters (e.g., BTC).")
                    return

            if state == "rate":
                await self._handle_rate_ticker(message, ticker)
            elif state == "forecast":
                await self._handle_forecast_ticker(message, ticker)
            elif state == "subscribe_ticker":
                self.user_states[user_id] = {
                    "state": "subscribe_threshold",
                    "ticker": ticker
                }
                await message.answer("Please enter the price change threshold percentage (e.g., 5):")
            elif state == "subscribe_threshold":
                try:
                    threshold = float(message.text)
                    ticker = self.user_states[user_id]["ticker"]
                    await self._handle_subscribe(message, ticker, threshold)
                except ValueError:
                    await message.answer("Invalid threshold. Please enter a number (e.g., 5).")
                    return
            elif state == "unsubscribe":
                await self._handle_unsubscribe(message, ticker)
            elif state == "history":
                await self._handle_history(message, ticker)

            if state not in ["subscribe_ticker", "subscribe_threshold"]:
                del self.user_states[user_id]

    def _is_valid_ticker(self, ticker: str) -> bool:
        return 2 <= len(ticker) <= 5 and ticker.isalpha() and ticker.isupper()

    async def _handle_rate_ticker(self, message: Message, ticker: str):
        try:
            async with httpx.AsyncClient() as client:
                self.logger.info(f"Fetching price for {ticker} from {self.backend_url}/api/price/{ticker}")
                response = await client.get(
                    f"{self.backend_url}/api/price/{ticker}",
                    headers={"X-API-Key": self.api_key}
                )
                self.logger.info(f"Response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    await message.answer(data["message"])
                else:
                    error_msg = f"Error fetching price. Status code: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f", Details: {error_data.get('detail', 'No details')}"
                    except:
                        error_msg += f", Response: {response.text}"
                    self.logger.error(error_msg)
                    await message.answer("Error fetching price. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_rate_ticker: {str(e)}", exc_info=True)
            await message.answer("An error occurred. Please try again later.")

    async def _handle_forecast_ticker(self, message: Message, ticker: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/api/forecast/{ticker}",
                    headers={"X-API-Key": self.api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    await message.answer(
                        f"📊 Forecast for {ticker}:\n\n"
                        f"{data['forecast']}\n\n"
                        f"Confidence: {data['confidence']*100:.1f}%"
                    )
                else:
                    await message.answer("Error generating forecast. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_forecast_ticker: {str(e)}")
            await message.answer("An error occurred. Please try again later.")

    async def _handle_subscribe(self, message: Message, ticker: str, threshold: float):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/api/subscriptions",
                    headers={"X-API-Key": self.api_key},
                    json={
                        "user_id": message.from_user.id,
                        "ticker": ticker,
                        "threshold": threshold
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    await message.answer(data["message"])
                else:
                    await message.answer("Error subscribing to alerts. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_subscribe: {str(e)}")
            await message.answer("An error occurred. Please try again later.")

    async def _handle_unsubscribe(self, message: Message, ticker: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.backend_url}/api/subscriptions",
                    headers={"X-API-Key": self.api_key},
                    params={
                        "user_id": message.from_user.id,
                        "ticker": ticker
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    await message.answer(data["message"])
                else:
                    await message.answer("Error unsubscribing from alerts. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_unsubscribe: {str(e)}")
            await message.answer("An error occurred. Please try again later.")

    async def _handle_mysubs(self, message: Message):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/api/subscriptions",
                    headers={"X-API-Key": self.api_key},
                    params={"user_id": message.from_user.id}
                )
                if response.status_code == 200:
                    data = response.json()
                    if "message" in data:
                        await message.answer(data["message"])
                    else:
                        subs_text = "Your active subscriptions:\n\n"
                        for sub in data["subscriptions"]:
                            subs_text += (
                                f"📈 {sub['ticker']}\n"
                                f"Threshold: {sub['threshold']}%\n"
                                f"Current price: ${sub['current_price']:.2f}\n"
                                f"Change since subscription: {sub['change_since_subscription']}\n\n"
                            )
                        await message.answer(subs_text)
                else:
                    await message.answer("Error fetching subscriptions. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_mysubs: {str(e)}")
            await message.answer("An error occurred. Please try again later.")

    async def _handle_history(self, message: Message, ticker: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/api/price/history/{ticker}",
                    headers={"X-API-Key": self.api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    if "message" in data:
                        await message.answer(data["message"])
                    else:
                        history_text = f"Price history for {ticker} (last 24 hours):\n\n"
                        for entry in data["history"]:
                            history_text += f"{entry['timestamp']}: {entry['price']} ({entry['change_24h']})\n"
                        await message.answer(history_text)
                else:
                    await message.answer("Error fetching price history. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_history: {str(e)}")
            await message.answer("An error occurred. Please try again later.")

    async def _handle_notifications(self, message: Message):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/api/notifications",
                    headers={"X-API-Key": self.api_key},
                    params={"user_id": message.from_user.id}
                )
                if response.status_code == 200:
                    data = response.json()
                    if "message" in data:
                        await message.answer(data["message"])
                    else:
                        notif_text = "Your recent notifications:\n\n"
                        for notif in data["notifications"]:
                            notif_text += f"📢 {notif['message']}\n"
                            notif_text += f"Time: {notif['sent_at']}\n\n"
                        await message.answer(notif_text)
                else:
                    await message.answer("Error fetching notifications. Please try again.")
        except Exception as e:
            self.logger.error(f"Error in _handle_notifications: {str(e)}")
            await message.answer("An error occurred. Please try again later.")

    async def start(self):
        await self.dp.start_polling(self.bot) 