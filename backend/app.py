from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from .services.cmc_service import CMCService
from .services.gpt_service import GPTService
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

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key

# Initialize services
cmc_service = CMCService()
gpt_service = GPTService()
subscription_service = SubscriptionService()

# Store startup time for uptime calculation
startup_time = time.time()

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
        price = await cmc_service.get_price(ticker)
        return PriceResponse(price=price, timestamp=int(time.time()))
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/forecast/{ticker}", response_model=ForecastResponse, responses={400: {"model": ErrorResponse}})
async def get_forecast(ticker: str, api_key: str = Depends(get_api_key)):
    try:
        forecast = await gpt_service.get_forecast(ticker)
        return ForecastResponse(forecast=forecast, timestamp=int(time.time()))
    except Exception as e:
        logger.error(f"Error generating forecast for {ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/subscribe/{ticker}", response_model=dict, responses={400: {"model": ErrorResponse}})
async def subscribe(ticker: str, request: SubscriptionRequest, api_key: str = Depends(get_api_key)):
    try:
        await subscription_service.add_subscription(request.user_id, ticker, request.threshold)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error subscribing {request.user_id} to {ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/unsubscribe/{ticker}", response_model=dict, responses={400: {"model": ErrorResponse}})
async def unsubscribe(ticker: str, user_id: int, api_key: str = Depends(get_api_key)):
    try:
        await subscription_service.remove_subscription(user_id, ticker)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error unsubscribing {user_id} from {ticker}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 