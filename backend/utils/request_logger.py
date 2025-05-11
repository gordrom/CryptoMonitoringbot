from typing import Optional
from datetime import datetime
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_KEY", "")
)

async def log_request(
    user_id: Optional[int],
    endpoint: str,
    ticker: Optional[str] = None,
    price: Optional[float] = None,
    forecast: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None
):
    """
    Log an API request to the database
    
    Args:
        user_id: The ID of the user making the request
        endpoint: The API endpoint being called
        ticker: The cryptocurrency ticker (if applicable)
        price: The price data (if applicable)
        forecast: The forecast data (if applicable)
        status: The status of the request (success/error)
        error_message: Any error message (if applicable)
    """
    try:
        log_data = {
            "user_id": user_id,
            "endpoint": endpoint,
            "ticker": ticker,
            "price": price,
            "forecast": forecast,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "error_message": error_message
        }
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        await supabase.table('request_logs').insert(log_data).execute()
    except Exception as e:
        print(f"Error logging request: {str(e)}") 