from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
from typing import Dict, Set, Optional, List
import httpx
import os
from supabase import create_client, Client
from datetime import datetime, timedelta, UTC
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import postgrest.exceptions

load_dotenv()

class SubscriptionService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize Supabase client with your credentials
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Verify database connection
        self._check_database_connection()

        self.scheduler = AsyncIOScheduler()
        # Don't start scheduler here, we'll do it in start_scheduler()
        self.http_client = httpx.AsyncClient()
        
        # Connection pool settings
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((postgrest.exceptions.APIError, ConnectionError))
    )
    def _check_database_connection(self):
        try:
            # Try to fetch one record to test connection
            response = self.supabase.table('price_history').select('*').limit(1).execute()
            self.logger.info("Successfully connected to Supabase database")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((postgrest.exceptions.APIError, ConnectionError))
    )
    async def _execute_db_operation(self, operation):
        """Execute a database operation with retry logic"""
        try:
            # Execute the operation and return the result
            result = operation()
            return result
        except Exception as e:
            self.logger.error(f"Database operation failed: {str(e)}")
            raise

    async def log_request(self, log_data: dict):
        """Log a request with retry logic"""
        try:
            await self._execute_db_operation(
                lambda: self.supabase.table("request_logs").insert(log_data).execute()
            )
        except Exception as e:
            self.logger.error(f"Failed to log request: {str(e)}")

    async def start_scheduler(self):
        """Start the scheduler after event loop is running"""
        if not self.scheduler.running:
            self.scheduler.start()
            self.scheduler.add_job(
                self._check_price_alerts,
                trigger=IntervalTrigger(minutes=5),
                id='price_alerts',
                replace_existing=True
            )
            self.logger.info("Price alerts scheduler started")

    async def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Price alerts scheduler stopped")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_telegram_message(self, user_id: int, message: str):
        try:
            response = await self.http_client.post(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
            )
            if response.status_code != 200:
                raise Exception(f"Failed to send message: {response.text}")
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {str(e)}")
            raise

    async def cleanup_old_data(self):
        try:
            # Cleanup old price history (keep last 30 days)
            cutoff = datetime.now(UTC) - timedelta(days=30)
            self.supabase.table("price_history")\
                .delete()\
                .lt("timestamp", cutoff.isoformat())\
                .execute()

            # Cleanup old notifications (keep last 90 days)
            cutoff = datetime.now(UTC) - timedelta(days=90)
            self.supabase.table("notification_logs")\
                .delete()\
                .lt("sent_at", cutoff.isoformat())\
                .execute()

            # Cleanup inactive subscriptions (no updates in 30 days)
            cutoff = datetime.now(UTC) - timedelta(days=30)
            self.supabase.table("subscriptions")\
                .delete()\
                .lt("updated_at", cutoff.isoformat())\
                .execute()
        except Exception as e:
            self.logger.error(f"Error in data cleanup: {str(e)}")

    async def update_analytics(self):
        try:
            # Update forecast accuracy
            forecasts = self.supabase.table("forecast_history")\
                .select("*")\
                .not_.is_("accuracy_score", "null")\
                .execute()
            
            for forecast in forecasts.data:
                if forecast["actual_price"]:
                    accuracy = self._calculate_forecast_accuracy(
                        forecast["forecast"],
                        forecast["actual_price"]
                    )
                    self.supabase.table("forecast_history")\
                        .update({"accuracy_score": accuracy})\
                        .eq("id", forecast["id"])\
                        .execute()

            # Update price trends
            for ticker in self._get_active_tickers():
                trend = await self._calculate_price_trend(ticker)
                self.supabase.table("price_trends")\
                    .upsert({
                        "ticker": ticker,
                        "trend": trend,
                        "updated_at": datetime.now(UTC).isoformat()
                    })\
                    .execute()
        except Exception as e:
            self.logger.error(f"Error updating analytics: {str(e)}")

    def _get_active_tickers(self) -> List[str]:
        try:
            result = self.supabase.table("subscriptions")\
                .select("ticker")\
                .execute()
            return list(set(sub["ticker"] for sub in result.data))
        except Exception as e:
            self.logger.error(f"Error getting active tickers: {str(e)}")
            return []

    async def _calculate_price_trend(self, ticker: str) -> str:
        try:
            history = await self.get_price_history(ticker, hours=24)
            if len(history) < 2:
                return "neutral"
            
            prices = [float(h["price"]) for h in history]
            first_price = prices[0]
            last_price = prices[-1]
            change = ((last_price - first_price) / first_price) * 100
            
            if change > 2:
                return "up"
            elif change < -2:
                return "down"
            return "neutral"
        except Exception as e:
            self.logger.error(f"Error calculating price trend: {str(e)}")
            return "neutral"

    def _calculate_forecast_accuracy(self, forecast: str, actual_price: float) -> float:
        # TODO: Implement more sophisticated forecast accuracy calculation
        return 0.0

    async def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        try:
            result = self.supabase.table("subscriptions")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            return result.data
        except Exception as e:
            self.logger.error(f"Error getting user subscriptions: {str(e)}")
            return []

    async def update_user_preferences(self, user_id: int, preferences: Dict):
        try:
            self.supabase.table("user_preferences")\
                .update(preferences)\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            self.logger.error(f"Error updating user preferences: {str(e)}")
            raise

    async def add_subscription(self, user_id: int, ticker: str, threshold: float):
        try:
            data = {
                "user_id": user_id,
                "ticker": ticker,
                "threshold": threshold,
                "last_price": None,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }
            result = self.supabase.table("subscriptions").insert(data).execute()
            if not result.data:
                raise Exception("Failed to add subscription")
            
            # Initialize user preferences if not exists
            await self._init_user_preferences(user_id)
        except Exception as e:
            self.logger.error(f"Error adding subscription: {str(e)}")
            raise

    async def _init_user_preferences(self, user_id: int):
        try:
            result = self.supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            if not result.data:
                data = {
                    "user_id": user_id,
                    "default_currency": "USD",
                    "notification_enabled": True,
                    "notification_timezone": "UTC"
                }
                self.supabase.table("user_preferences").insert(data).execute()
        except Exception as e:
            self.logger.error(f"Error initializing user preferences: {str(e)}")

    async def remove_subscription(self, user_id: int, ticker: str):
        try:
            result = self.supabase.table("subscriptions").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
            if not result.data:
                raise Exception("Failed to remove subscription")
        except Exception as e:
            self.logger.error(f"Error removing subscription: {str(e)}")
            raise

    async def get_subscriptions(self) -> Dict[int, Dict[str, float]]:
        try:
            result = self.supabase.table("subscriptions").select("*").execute()
            subscriptions = result.data
            return {
                sub["user_id"]: {
                    sub["ticker"]: sub["threshold"]
                } for sub in subscriptions
            }
        except Exception as e:
            self.logger.error(f"Error getting subscriptions: {str(e)}")
            return {}

    async def update_last_price(self, user_id: int, ticker: str, price: float):
        try:
            data = {
                "last_price": price,
                "updated_at": datetime.now(UTC).isoformat()
            }
            result = self.supabase.table("subscriptions").update(data).eq("user_id", user_id).eq("ticker", ticker).execute()
            if not result.data:
                raise Exception("Failed to update last price")

            # Store price in history
            await self._store_price_history(ticker, price)
        except Exception as e:
            self.logger.error(f"Error updating last price: {str(e)}")
            raise

    async def _store_price_history(self, ticker: str, price: float):
        try:
            data = {
                "ticker": ticker,
                "price": price,
                "timestamp": datetime.now(UTC).isoformat()
            }
            result = await self._execute_db_operation(
                lambda: self.supabase.table("price_history").insert(data).execute()
            )
            if not result or not result.data:
                raise Exception("Failed to store price history")
            self.logger.info(f"Successfully stored price history for {ticker}: {data}")
            return result.data
        except Exception as e:
            self.logger.error(f"Error storing price history: {str(e)}")
            raise

    async def _store_notification(self, user_id: int, ticker: str, message: str, notification_type: str):
        try:
            data = {
                "user_id": user_id,
                "ticker": ticker,
                "notification_type": notification_type,
                "message": message,
                "sent_at": datetime.now(UTC).isoformat(),
                "status": "sent"
            }
            self.supabase.table("notification_logs").insert(data).execute()
        except Exception as e:
            self.logger.error(f"Error storing notification: {str(e)}")

    async def _check_price_alerts(self):
        try:
            subscriptions = await self.get_subscriptions()
            for user_id, user_subs in subscriptions.items():
                for ticker, threshold in user_subs.items():
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                f"http://{os.getenv('BACKEND_HOST')}:{os.getenv('BACKEND_PORT')}/api/price/{ticker}",
                                headers={"X-API-Key": os.getenv("API_KEY")}
                            )
                            if response.status_code == 200:
                                current_price = response.json()['price']
                                await self._check_price_change(user_id, ticker, current_price, threshold)
                    except Exception as e:
                        self.logger.error(f"Error checking price for {ticker}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error in _check_price_alerts: {str(e)}")

    async def _check_price_change(self, user_id: int, ticker: str, current_price: float, threshold: float):
        try:
            result = self.supabase.table("subscriptions").select("*").eq("user_id", user_id).eq("ticker", ticker).execute()
            subscription = result.data[0] if result.data else None
            
            if subscription and subscription.get("last_price"):
                last_price = subscription["last_price"]
                price_change = abs((current_price - last_price) / last_price * 100)
                if price_change >= threshold:
                    message = f"Price alert for {ticker}: {price_change:.2f}% change (Current: ${current_price:.2f})"
                    await self._store_notification(user_id, ticker, message, "price_alert")
                    await self.send_telegram_message(user_id, message)
            
            await self.update_last_price(user_id, ticker, current_price)
        except Exception as e:
            self.logger.error(f"Error in _check_price_change: {str(e)}")

    async def get_price_history(self, ticker: str, hours: int = 24) -> List[Dict]:
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
            self.logger.info(f"Fetching price history for {ticker} since {cutoff_time}")
            
            result = await self._execute_db_operation(
                lambda: self.supabase.table("price_history")
                .select("*")
                .eq("ticker", ticker)
                .gte("timestamp", cutoff_time.isoformat())
                .order("timestamp")
                .execute()
            )
            
            if not result or not result.data:
                self.logger.info(f"No history found for {ticker}, fetching current price")
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"http://{os.getenv('BACKEND_HOST')}:{os.getenv('BACKEND_PORT')}/api/price/{ticker}",
                            headers={"X-API-Key": os.getenv("API_KEY")}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            current_price = data['price']
                            await self._store_price_history(ticker, current_price)
                            return [{
                                "ticker": ticker,
                                "price": current_price,
                                "timestamp": datetime.now(UTC).isoformat()
                            }]
                except Exception as e:
                    self.logger.error(f"Error fetching current price: {str(e)}")
                return []
            
            self.logger.info(f"Found {len(result.data)} price history entries for {ticker}")
            return result.data
            
        except Exception as e:
            self.logger.error(f"Error getting price history: {str(e)}")
            return []

    async def get_user_notifications(self, user_id: int, limit: int = 10) -> List[Dict]:
        try:
            result = self.supabase.table("notification_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("sent_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data
        except Exception as e:
            self.logger.error(f"Error getting user notifications: {str(e)}")
            return []

    async def _store_forecast_history(self, ticker: str, forecast: str, confidence: float):
        try:
            data = {
                "ticker": ticker,
                "forecast": forecast,
                "confidence": confidence,
                "timestamp": datetime.now(UTC).isoformat()
            }
            result = await self._execute_db_operation(
                lambda: self.supabase.table("forecast_history").insert(data).execute()
            )
            if not result or not result.data:
                raise Exception("Failed to store forecast history")
            self.logger.info(f"Successfully stored forecast history for {ticker}")
            return result.data
        except Exception as e:
            self.logger.error(f"Error storing forecast history: {str(e)}")
            raise 