import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()

class CMCService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv("CMC_API_KEY")
        if not self.api_key:
            raise ValueError("CMC_API_KEY environment variable is not set")
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        # Create client with timeout settings
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),  # 10 seconds total, 5 seconds for connection
            limits=httpx.Limits(max_retries=3)  # Retry failed requests up to 3 times
        )

    async def get_price(self, ticker: str) -> dict:
        try:
            self.logger.info(f"Fetching price for {ticker}")
            response = await self.http_client.get(
                f"{self.base_url}/cryptocurrency/quotes/latest",
                params={"symbol": ticker},
                headers={"X-CMC_PRO_API_KEY": self.api_key}
            )
            
            if response.status_code == 401:
                error_msg = "Invalid or expired API key for CoinMarketCap"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            elif response.status_code == 429:
                error_msg = "Rate limit exceeded for CoinMarketCap API"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            elif response.status_code != 200:
                error_msg = f"Failed to fetch price for {ticker}: {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            data = response.json()
            if not data.get("data") or ticker not in data["data"]:
                error_msg = f"No data found for {ticker}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            return data["data"][ticker]
        except httpx.TimeoutException:
            error_msg = f"Request timed out while fetching price for {ticker}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Network error while fetching price for {ticker}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker}: {str(e)}")
            raise Exception(f"Failed to fetch price for {ticker}") 