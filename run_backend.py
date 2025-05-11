import uvicorn
import os
from dotenv import load_dotenv
import sys

# Check Python version
if sys.version_info < (3, 12):
    print("Error: This application requires Python 3.12 or higher")
    sys.exit(1)

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", 8000)),
        reload=False,  # Disable reload in production
        workers=int(os.getenv("WORKERS", 4))  # Add worker configuration
    ) 