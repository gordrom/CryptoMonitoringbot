from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from .services.cmc_service import CMCService
from .services.deepseek_service import DeepSeekService
from .services.subscription_service import SubscriptionService
from .models import (
    PriceResponse,
    ForecastResponse,
    SubscriptionRequest,
    ErrorResponse,
    HealthResponse
)
import os
import time
from dotenv import load_dotenv
import logging
from typing import Annotated
import json
from datetime import datetime, UTC

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Monitor API",
    description="API for cryptocurrency price monitoring and forecasting",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: Annotated[str, Depends(api_key_header)]):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key

# Initialize services
cmc_service = CMCService()
deepseek_service = DeepSeekService()
subscription_service = SubscriptionService()

# Store startup time for uptime calculation
startup_time = time.time()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Get request details
    timestamp = datetime.now(UTC).isoformat()
    method = request.method
    url = str(request.url)
    
    # Extract endpoint and parameters
    path = request.url.path
    query_params = dict(request.query_params)
    
    # Get request body if it exists
    body = None
    if method in ["POST", "PUT"]:
        try:
            body = await request.json()
        except:
            body = None
    
    # Process request
    start_time = time.time()
    try:
        response = await call_next(request)
        status = "success"
        error_message = None
    except Exception as e:
        status = "error"
        error_message = str(e)
        raise
    finally:
        processing_time = time.time() - start_time
        
        # Extract relevant data based on endpoint
        log_data = {
            "timestamp": timestamp,
            "endpoint": path,
            "status": status,
            "error_message": error_message
        }
        
        # Add specific data based on endpoint
        if "/api/price/" in path:
            ticker = path.split("/")[-1]
            log_data.update({
                "ticker": ticker,
                "price": body.get("price") if body else None
            })
        elif "/api/forecast/" in path:
            ticker = path.split("/")[-1]
            log_data.update({
                "ticker": ticker,
                "forecast": body.get("forecast") if body else None
            })
        elif "/api/subscriptions" in path:
            if body:
                log_data.update({
                    "user_id": body.get("user_id"),
                    "ticker": body.get("ticker")
                })
            elif query_params:
                log_data.update({
                    "user_id": query_params.get("user_id"),
                    "ticker": query_params.get("ticker")
                })
        
        # Store log
        try:
            await subscription_service.log_request(log_data)
        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")
    
    return response

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=time.time() - startup_time
    )

@app.get("/api/price/{ticker}", response_model=PriceResponse, responses={400: {"model": ErrorResponse}})
async def get_price(ticker: str, api_key: str = Depends(get_api_key)):
    try:
        data = await cmc_service.get_price(ticker)
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
            message=message,
            timestamp=int(time.time())
        )
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/forecast/{ticker}")
async def get_forecast(ticker: str, api_key: str = Depends(get_api_key)):
    try:
        # Get price history for the last 24 hours
        price_history = await subscription_service.get_price_history(ticker, hours=24)
        
        if not price_history:
            raise HTTPException(status_code=400, detail="No price history available for forecasting")
        
        # Get forecast from DeepSeek
        forecast, confidence = await deepseek_service.get_forecast(ticker, price_history)
        
        # Store the forecast in history
        await subscription_service._store_forecast_history(ticker, forecast, confidence)
        
        return {
            "forecast": forecast,
            "confidence": confidence,
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating forecast")

@app.post("/api/subscriptions", response_model=dict, responses={400: {"model": ErrorResponse}})
async def subscribe(request: SubscriptionRequest, api_key: str = Depends(get_api_key)):
    try:
        # Get current price for confirmation message
        data = await cmc_service.get_price(request.ticker)
        current_price = data["quote"]["USD"]["price"]
        
        await subscription_service.add_subscription(request.user_id, request.ticker, request.threshold)
        return {
            "message": f"Subscription added successfully! You will be notified when {request.ticker} changes by {request.threshold}% from ${current_price:.2f}"
        }
    except Exception as e:
        logger.error(f"Error subscribing {request.user_id} to {request.ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/subscriptions", response_model=dict, responses={400: {"model": ErrorResponse}})
async def unsubscribe(user_id: int, ticker: str, api_key: str = Depends(get_api_key)):
    try:
        await subscription_service.remove_subscription(user_id, ticker)
        return {
            "message": f"Successfully unsubscribed from {ticker} price alerts"
        }
    except Exception as e:
        logger.error(f"Error unsubscribing {user_id} from {ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/subscriptions", response_model=dict, responses={400: {"model": ErrorResponse}})
async def get_subscriptions(user_id: int, api_key: str = Depends(get_api_key)):
    try:
        subscriptions = await subscription_service.get_user_subscriptions(user_id)
        if not subscriptions:
            return {"message": "You have no active subscriptions"}
        
        response = []
        for sub in subscriptions:
            data = await cmc_service.get_price(sub["ticker"])
            current_price = data["quote"]["USD"]["price"]
            change = ((current_price - sub["last_price"]) / sub["last_price"]) * 100 if sub["last_price"] else 0
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
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/price/history/{ticker}", response_model=dict, responses={400: {"model": ErrorResponse}})
async def get_price_history(ticker: str, hours: int = 24, api_key: str = Depends(get_api_key)):
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
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/notifications", response_model=dict, responses={400: {"model": ErrorResponse}})
async def get_notifications(user_id: int, limit: int = 10, api_key: str = Depends(get_api_key)):
    try:
        notifications = await subscription_service.get_user_notifications(user_id, limit)
        if not notifications:
            return {"message": "No notifications found"}
        
        return {"notifications": notifications}
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 