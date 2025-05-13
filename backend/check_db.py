from supabase import create_client, Client
import logging
from datetime import datetime, UTC
import time
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    # Initialize Supabase client
    supabase: Client = create_client(
        "https://wpccvufuocqusgkvyxos.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwY2N2dWZ1b2NxdXNna3Z5eG9zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDM3MTQzNywiZXhwIjoyMDU5OTQ3NDM3fQ.Odbr_dVfUzl_QRCZhKj6e4byKQ59j8XLfxaKmTNl--0"
    )

    # Use a test user ID that's unlikely to conflict
    test_user_id = 999999

    # Check and create price_history table
    try:
        # Try to insert a test record
        test_data = {
            "ticker": "TEST",
            "price": 1.0,
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "test"
        }
        result = supabase.table("price_history").insert(test_data).execute()
        logger.info("Successfully inserted test record into price_history")
        
        # Delete the test record
        supabase.table("price_history").delete().eq("ticker", "TEST").execute()
        logger.info("Successfully deleted test record from price_history")
    except Exception as e:
        logger.error(f"Error with price_history table: {str(e)}")
        raise

    # Check and create user_preferences table
    try:
        # Try to insert a test user
        test_user = {
            "user_id": test_user_id,
            "default_currency": "USD",
            "notification_enabled": True,
            "notification_timezone": "UTC",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }
        result = supabase.table("user_preferences").insert(test_user).execute()
        logger.info("Successfully inserted test user into user_preferences")
    except Exception as e:
        logger.error(f"Error with user_preferences table: {str(e)}")
        raise

    # Check and create subscriptions table
    try:
        # Try to insert a test record
        test_subscription = {
            "user_id": test_user_id,
            "ticker": "TEST",
            "threshold": 1.0,
            "last_price": 1.0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }
        result = supabase.table("subscriptions").insert(test_subscription).execute()
        logger.info("Successfully inserted test record into subscriptions")
        
        # Check and create notification_logs table
        try:
            # Try to insert a test record
            test_notification = {
                "user_id": test_user_id,
                "ticker": "TEST",
                "notification_type": "test",
                "message": "Test notification",
                "sent_at": datetime.now(UTC).isoformat(),
                "status": "test"
            }
            result = supabase.table("notification_logs").insert(test_notification).execute()
            logger.info("Successfully inserted test record into notification_logs")
            
            # Delete the test notification record
            supabase.table("notification_logs").delete().eq("ticker", "TEST").execute()
            logger.info("Successfully deleted test record from notification_logs")
        except Exception as e:
            logger.error(f"Error with notification_logs table: {str(e)}")
            raise

        # Delete the test subscription record
        supabase.table("subscriptions").delete().eq("ticker", "TEST").execute()
        logger.info("Successfully deleted test record from subscriptions")
    except Exception as e:
        logger.error(f"Error with subscriptions table: {str(e)}")
        raise

    # Check and create request_logs table
    try:
        # Try to insert a test record
        test_request_log = {
            "request_id": "test_" + str(int(time.time())),
            "timestamp": datetime.now(UTC).isoformat(),
            "method": "GET",
            "url": "http://test.com/test",
            "client_host": "127.0.0.1",
            "query_params": {"test": "test"},
            "request_body": None,
            "response_body": {"status": "ok"},
            "status_code": 200,
            "processing_time": 0.1
        }
        result = supabase.table("request_logs").insert(test_request_log).execute()
        logger.info("Successfully inserted test record into request_logs")
        
        # Delete the test record
        supabase.table("request_logs").delete().eq("request_id", test_request_log["request_id"]).execute()
        logger.info("Successfully deleted test record from request_logs")
    except Exception as e:
        logger.error(f"Error with request_logs table: {str(e)}")
        raise

    # Clean up test user
    try:
        supabase.table("user_preferences").delete().eq("user_id", test_user_id).execute()
        logger.info("Successfully deleted test user from user_preferences")
    except Exception as e:
        logger.error(f"Error cleaning up test user: {str(e)}")
        raise

    logger.info("Database schema verification completed successfully")

async def check_database():
    """Check if all required tables exist in the database"""
    try:
        # Check price_history table
        result = await supabase.table('price_history').select('*').limit(1).execute()
        print("✅ price_history table exists")

        # Check forecast_history table
        result = await supabase.table('forecast_history').select('*').limit(1).execute()
        print("✅ forecast_history table exists")

        # Check price_trends table
        result = await supabase.table('price_trends').select('*').limit(1).execute()
        print("✅ price_trends table exists")

        # Check subscriptions table
        result = await supabase.table('subscriptions').select('*').limit(1).execute()
        print("✅ subscriptions table exists")

        # Check notification_logs table
        result = await supabase.table('notification_logs').select('*').limit(1).execute()
        print("✅ notification_logs table exists")

        # Check user_preferences table
        result = await supabase.table('user_preferences').select('*').limit(1).execute()
        print("✅ user_preferences table exists")

        # Check request_logs table
        result = await supabase.table('request_logs').select('*').limit(1).execute()
        print("✅ request_logs table exists")

        return True
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        return False

if __name__ == "__main__":
    init_db() 