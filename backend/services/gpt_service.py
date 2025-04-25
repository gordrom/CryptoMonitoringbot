import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    async def get_forecast(self, ticker: str) -> str:
        prompt = f"""Based on recent market trends and technical analysis, provide a short-term (24-hour) forecast for {ticker}.
        Focus on key factors that might influence the price movement. Keep the response concise and professional."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional cryptocurrency analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Failed to generate forecast: {str(e)}") 