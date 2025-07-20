# Vercel serverless function entry point
from app import app

# Export the FastAPI app for Vercel
handler = app
