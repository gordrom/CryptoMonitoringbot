import os
from openai import OpenAI
import logging
from dotenv import load_dotenv

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = "deepseek/deepseek-prover-v2:free"

    async def get_forecast(self, ticker: str, price_history: list) -> tuple[str, float]:
        try:
            # Prepare the prompt with price history
            price_history_text = "\n".join([
                f"Price at {entry['timestamp']}: ${entry['price']:.2f}"
                for entry in price_history
            ])

            prompt = f"""Based on the following price history for {ticker}, provide a short-term price forecast (next 24 hours):
            {price_history_text}
            
            Please provide:
            1. A brief analysis of the price trend
            2. A prediction for the next 24 hours
            3. Key factors that might influence the price
            Keep the response concise and focused on actionable insights."""

            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://github.com/gordrom/CryptoMonitoringbot",
                    "X-Title": "Crypto Monitoring Bot",
                },
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            forecast = completion.choices[0].message.content
            # For now, we'll use a fixed confidence score since the free model doesn't provide one
            confidence = 0.7

            return forecast, confidence

        except Exception as e:
            self.logger.error(f"Error getting forecast from DeepSeek: {str(e)}")
            return "Unable to generate forecast at this time.", 0.0 