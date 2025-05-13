from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize DeepSeek client
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_forecast(self, ticker: str) -> str:
        """Get price forecast for a cryptocurrency using DeepSeek"""
        try:
            prompt = f"""Analyze the current market conditions and provide a price forecast for {ticker}.
            Consider:
            1. Recent price trends
            2. Market sentiment
            3. Technical indicators
            4. Market news and events
            
            Provide a concise but comprehensive analysis in 2-3 paragraphs."""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a cryptocurrency market analyst. Provide clear, data-driven analysis and forecasts."},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )

            forecast = response.choices[0].message.content
            self.logger.info(f"Successfully generated forecast for {ticker}")
            return forecast

        except Exception as e:
            self.logger.error(f"Error generating forecast for {ticker}: {str(e)}")
            raise 