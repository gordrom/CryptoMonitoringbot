import asyncio
from bot.bot import CryptoBot
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    bot = CryptoBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main()) 