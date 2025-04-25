from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
from typing import Dict, Set, Optional, List
import httpx
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

class SubscriptionService:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.setup_jobs()
        self.logger = logging.getLogger(__name__)
        self.http_client = httpx.AsyncClient()

    def setup_jobs(self):
        # Price check job
        self.scheduler.add_job(
            self.check_price_changes,
            IntervalTrigger(minutes=5),
            id='price_check'
        )
        # Data cleanup job
        self.scheduler.add_job(
            self.cleanup_old_data,
            IntervalTrigger(hours=24),
            id='data_cleanup'
        )
        # Analytics job
        self.scheduler.add_job(
            self.update_analytics,
            IntervalTrigger(hours=1),
            id='analytics'
        )

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
            cutoff = datetime.utcnow() - timedelta(days=30)
            self.supabase.table("price_history")\
                .delete()\
                .lt("timestamp", cutoff.isoformat())\
                .execute()

            # Cleanup old notifications (keep last 90 days)
            cutoff = datetime.utcnow() - timedelta(days=90)
            self.supabase.table("notification_logs")\
                .delete()\
                .lt("sent_at", cutoff.isoformat())\
                .execute()

            # Cleanup inactive subscriptions (no updates in 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)
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
                        "updated_at": datetime.utcnow().isoformat()
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
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
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
                "updated_at": datetime.utcnow().isoformat()
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
                "timestamp": datetime.utcnow().isoformat()
            }
            self.supabase.table("price_history").insert(data).execute()
        except Exception as e:
            self.logger.error(f"Error storing price history: {str(e)}")

    async def _store_notification(self, user_id: int, ticker: str, message: str, notification_type: str):
        try:
            data = {
                "user_id": user_id,
                "ticker": ticker,
                "notification_type": notification_type,
                "message": message,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent"
            }
            self.supabase.table("notification_logs").insert(data).execute()
        except Exception as e:
            self.logger.error(f"Error storing notification: {str(e)}")

    async def check_price_changes(self):
        try:
            subscriptions = await self.get_subscriptions()
            for user_id, user_subs in subscriptions.items():
                for ticker, threshold in user_subs.items():
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                f"http://{os.getenv('BACKEND_HOST')}:{os.getenv('BACKEND_PORT')}/api/price/{ticker}"
                            )
                            if response.status_code == 200:
                                current_price = response.json()['price']
                                await self._check_price_change(user_id, ticker, current_price, threshold)
                    except Exception as e:
                        self.logger.error(f"Error checking price for {ticker}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error in check_price_changes: {str(e)}")

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
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            result = self.supabase.table("price_history")\
                .select("*")\
                .eq("ticker", ticker)\
                .gte("timestamp", cutoff_time.isoformat())\
                .order("timestamp")\
                .execute()
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