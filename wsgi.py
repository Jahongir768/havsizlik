"""
WSGI entry point for Vercel deployment
"""
import os
import threading
import asyncio
from app import app

# Start bot in background thread for production
def start_bot_background():
    """Start bot in background thread"""
    try:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
    except Exception as e:
        print(f"Error starting bot: {e}")

# Start bot when module is imported
start_bot_background()

# Export the FastAPI app for Vercel
handler = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
