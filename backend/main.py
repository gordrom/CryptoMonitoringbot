from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from services.subscription_service import SubscriptionService
import logging
import httpx
import openai
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI(title="Crypto Monitoring API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
subscription_service = SubscriptionService()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class SubscriptionRequest(BaseModel):
    ticker: str
    threshold: float

class UserPreferences(BaseModel):
    default_currency: str = "USD"
    notification_enabled: bool = True
    notification_timezone: str = "UTC"

class PriceResponse(BaseModel):
    ticker: str
    price: float
    change_24h: float
    trend: str
    message: str

class ForecastResponse(BaseModel):
    ticker: str
    forecast: str
    confidence: float
    timestamp: datetime

# Authentication
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Helper functions
async def get_crypto_data(ticker: str) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
            headers={"X-CMC_PRO_API_KEY": os.getenv("COINMARKETCAP_API_KEY")},
            params={"symbol": ticker}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch price")
        return response.json()["data"][ticker]

async def generate_forecast(ticker: str, price_history: List[Dict]) -> str:
    try:
        # Prepare historical data for analysis
        history_text = "\n".join([
            f"{h['timestamp']}: ${h['price']}"
            for h in price_history
        ])
        
        # Generate forecast using OpenAI
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a cryptocurrency market analyst. Analyze the price history and provide a short-term forecast."},
                {"role": "user", "content": f"Analyze this price history for {ticker} and provide a forecast for the next 24 hours:\n{history_text}"}
            ]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}")
        return "Unable to generate forecast at this time."

# Endpoints
@app.post("/api/subscriptions", dependencies=[Depends(verify_api_key)])
async def add_subscription(user_id: int, subscription: SubscriptionRequest):
    try:
        # Validate ticker exists
        await get_crypto_data(subscription.ticker)
        
        # Add subscription
        await subscription_service.add_subscription(user_id, subscription.ticker, subscription.threshold)
        
        # Get current price for confirmation message
        data = await get_crypto_data(subscription.ticker)
        current_price = data["quote"]["USD"]["price"]
        
        return {
            "message": f"Subscription added successfully! You will be notified when {subscription.ticker} changes by {subscription.threshold}% from ${current_price:.2f}"
        }
    except Exception as e:
        logger.error(f"Error adding subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/subscriptions", dependencies=[Depends(verify_api_key)])
async def remove_subscription(user_id: int, ticker: str):
    try:
        await subscription_service.remove_subscription(user_id, ticker)
        return {"message": f"Subscription for {ticker} removed successfully"}
    except Exception as e:
        logger.error(f"Error removing subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/subscriptions", dependencies=[Depends(verify_api_key)])
async def get_subscriptions(user_id: int):
    try:
        subscriptions = await subscription_service.get_user_subscriptions(user_id)
        if not subscriptions:
            return {"message": "You have no active subscriptions"}
        
        response = []
        for sub in subscriptions:
            data = await get_crypto_data(sub["ticker"])
            current_price = data["quote"]["USD"]["price"]
            change = ((current_price - sub["last_price"]) / sub["last_price"]) * 100
            response.append({
                "ticker": sub["ticker"],
                "threshold": sub["threshold"],
                "current_price": current_price,
                "last_price": sub["last_price"],
                "change_since_subscription": f"{change:.2f}%"
            })
        
        return {"subscriptions": response}
    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/price/{ticker}", dependencies=[Depends(verify_api_key)])
async def get_price(ticker: str):
    try:
        data = await get_crypto_data(ticker)
        price = data["quote"]["USD"]["price"]
        change_24h = data["quote"]["USD"]["percent_change_24h"]
        trend = await subscription_service._calculate_price_trend(ticker)
        
        message = f"Current price of {ticker}: ${price:.2f}\n"
        message += f"24h change: {change_24h:.2f}%\n"
        message += f"Trend: {trend}"
        
        return PriceResponse(
            ticker=ticker,
            price=price,
            change_24h=change_24h,
            trend=trend,
            message=message
        )
    except Exception as e:
        logger.error(f"Error getting price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast/{ticker}", dependencies=[Depends(verify_api_key)])
async def get_forecast(ticker: str):
    try:
        logger.info(f"Generating forecast for {ticker}")
        
        # Get price history
        history = await subscription_service.get_price_history(ticker, hours=24)
        logger.info(f"Found {len(history)} price history entries for {ticker}")
        
        # Generate forecast
        forecast = await generate_forecast(ticker, history)
        logger.info(f"Generated forecast for {ticker}: {forecast[:100]}...")
        
        # Store forecast for accuracy tracking
        await subscription_service.store_forecast(ticker, forecast)
        logger.info(f"Successfully stored forecast for {ticker}")
        
        response = ForecastResponse(
            ticker=ticker,
            forecast=forecast,
            confidence=0.8,  # Placeholder for confidence score
            timestamp=datetime.utcnow()
        )
        logger.info(f"Returning forecast response for {ticker}")
        return response
    except Exception as e:
        logger.error(f"Error getting forecast for {ticker}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/price/history/{ticker}", dependencies=[Depends(verify_api_key)])
async def get_price_history(ticker: str, hours: int = 24):
    try:
        history = await subscription_service.get_price_history(ticker, hours)
        if not history:
            return {"message": f"No price history available for {ticker}"}
        
        # Format history for better readability
        formatted_history = [
            {
                "timestamp": h["timestamp"],
                "price": f"${h['price']:.2f}",
                "change_24h": f"{h.get('change_24h', 0):.2f}%"
            }
            for h in history
        ]
        
        return {"history": formatted_history}
    except Exception as e:
        logger.error(f"Error getting price history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/preferences", dependencies=[Depends(verify_api_key)])
async def update_preferences(user_id: int, preferences: UserPreferences):
    try:
        await subscription_service.update_user_preferences(user_id, preferences.dict())
        return {"message": "Preferences updated successfully"}
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications", dependencies=[Depends(verify_api_key)])
async def get_notifications(user_id: int, limit: int = 10):
    try:
        notifications = await subscription_service.get_user_notifications(user_id, limit)
        if not notifications:
            return {"message": "No notifications found"}
        
        return {"notifications": notifications}
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("BACKEND_PORT", 8000))) 