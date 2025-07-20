"""
Simple entry point for local development
"""
import uvicorn
import os

# Existing code block
# ...deleted...

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    
    print("🚀 Starting development server...")
    print(f"📍 Server: http://{host}:{port}")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
