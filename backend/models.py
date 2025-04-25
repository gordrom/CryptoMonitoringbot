from pydantic import BaseModel, Field
from typing import Optional

class PriceResponse(BaseModel):
    price: float = Field(..., description="Current price of the cryptocurrency")
    timestamp: int = Field(..., description="Unix timestamp of the price")

class ForecastResponse(BaseModel):
    forecast: str = Field(..., description="Short-term price forecast")
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