import os
from openai import OpenAI
import logging
from dotenv import load_dotenv
import httpx

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
            
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=httpx.Timeout(30.0, connect=10.0),  # 30 seconds total, 10 seconds for connection
            max_retries=3
        )
        self.model = "deepseek/deepseek-prover-v2:free"

    async def get_forecast(self, ticker: str, price_history: list) -> tuple[str, float]:
        try:
            if not price_history:
                raise ValueError("No price history provided for forecasting")

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

            try:
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
                    ],
                    stream=False  # Ensure we get the complete response
                )
            except Exception as api_error:
                self.logger.error(f"API error from DeepSeek: {str(api_error)}")
                if "rate limit" in str(api_error).lower():
                    raise Exception("Rate limit exceeded for DeepSeek API")
                elif "authentication" in str(api_error).lower():
                    raise Exception("Invalid or expired API key for DeepSeek")
                else:
                    raise Exception(f"DeepSeek API error: {str(api_error)}")

            # Extract the forecast from the response
            forecast = completion.choices[0].message.content
            self.logger.info(f"Generated forecast for {ticker}: {forecast}")

            # Calculate confidence based on response length and content
            # This is a simple heuristic - you might want to adjust this
            confidence = min(0.7 + (len(forecast) / 1000), 0.95)  # Cap at 0.95

            return forecast, confidence

        except ValueError as ve:
            self.logger.error(f"Validation error: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting forecast from DeepSeek: {str(e)}")
            return "Unable to generate forecast at this time.", 0.0 