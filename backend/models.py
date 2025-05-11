from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class PriceResponse(BaseModel):
    ticker: str = Field(..., description="Cryptocurrency ticker symbol")
    price: float = Field(..., description="Current price of the cryptocurrency")
    change_24h: float = Field(..., description="24-hour price change percentage")
    trend: str = Field(..., description="Price trend (up/down/neutral)")
    message: str = Field(..., description="Formatted message with price information")
    timestamp: int = Field(..., description="Unix timestamp of the price")

class ForecastResponse(BaseModel):
    ticker: str = Field(..., description="Cryptocurrency ticker symbol")
    forecast: str = Field(..., description="Short-term price forecast")
    message: str = Field(..., description="Formatted message with forecast information")
    confidence: float = Field(..., description="Confidence score of the forecast")
    timestamp: int = Field(..., description="Unix timestamp of the forecast")

class SubscriptionRequest(BaseModel):
    user_id: int = Field(..., description="Telegram user ID")
    threshold: float = Field(..., description="Price change threshold percentage")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Service uptime in seconds")

class RequestLog(Base):
    __tablename__ = 'request_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_preferences.user_id'))
    endpoint = Column(String, nullable=False)
    ticker = Column(String)
    price = Column(Float)
    forecast = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)
    error_message = Column(Text) 