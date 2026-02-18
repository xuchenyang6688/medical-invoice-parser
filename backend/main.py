"""
Medical Invoice PDF Parser — FastAPI Backend
Entry point for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import convert

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Medical Invoice Parser API",
    description="Parses Chinese medical electronic invoices (医疗电子票据) from PDF into structured JSON",
    version="0.1.0",
)

# CORS configuration — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(convert.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
