import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.logger = logging.getLogger(__name__)

    async def get_forecast(self, ticker: str) -> dict:
        if not os.getenv('OPENAI_API_KEY'):
            raise Exception("OpenAI API key not configured")

        prompt = f"""Based on recent market trends and technical analysis, provide a short-term (24-hour) forecast for {ticker}.
        Focus on key factors that might influence the price movement. Keep the response concise and professional.
        Format the response in a clear, structured way with bullet points."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional cryptocurrency analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            
            forecast = response.choices[0].message.content
            # Calculate a confidence score based on the response length and structure
            confidence = min(0.8, 0.3 + (len(forecast) / 500))
            
            return {
                "forecast": forecast,
                "confidence": confidence
            }
        except Exception as e:
            self.logger.error(f"Failed to generate forecast: {str(e)}")
            raise Exception(f"Failed to generate forecast: {str(e)}") 