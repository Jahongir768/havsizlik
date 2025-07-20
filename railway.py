"""
Railway deployment entry point
"""
import os
import uvicorn
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("🚀 Starting Railway deployment...")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
