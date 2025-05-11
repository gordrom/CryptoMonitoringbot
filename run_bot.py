import asyncio
import logging
from dotenv import load_dotenv
from bot.bot import CryptoBot
from backend.services.subscription_service import SubscriptionService
from backend.services.cmc_service import CMCService
from backend.services.gpt_service import GPTService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    
    # Initialize services
    subscription_service = SubscriptionService()
    cmc_service = CMCService()
    gpt_service = GPTService()
    
    # Initialize bot with services
    bot = CryptoBot(
        subscription_service=subscription_service,
        cmc_service=cmc_service,
        gpt_service=gpt_service
    )
    
    try:
        # Start the scheduler after event loop is running
        await subscription_service.start_scheduler()
        
        logger.info("Starting bot...")
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        await subscription_service.stop_scheduler()
        await bot.stop()
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main()) 