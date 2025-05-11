import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class CMCService:
    def __init__(self):
        self.api_key = os.getenv('CMC_API_KEY')
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.headers = {
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json'
        }

    async def get_price(self, ticker: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/cryptocurrency/quotes/latest",
                headers=self.headers,
                params={'symbol': ticker}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch price for {ticker}")
            
            data = response.json()
            return data['data'][ticker] 