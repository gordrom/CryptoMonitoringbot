import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()

class CMCService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv("CMC_API_KEY")
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.http_client = httpx.AsyncClient()

    async def get_price(self, ticker: str) -> dict:
        try:
            self.logger.info(f"Fetching price for {ticker}")
            response = await self.http_client.get(
                f"{self.base_url}/cryptocurrency/quotes/latest",
                params={"symbol": ticker},
                headers={"X-CMC_PRO_API_KEY": self.api_key}
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to fetch price for {ticker}: {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            data = response.json()
            if not data.get("data") or ticker not in data["data"]:
                error_msg = f"No data found for {ticker}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            return data["data"][ticker]
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker}: {str(e)}")
            raise Exception(f"Failed to fetch price for {ticker}") 