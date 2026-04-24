"""
DataCartAI — FastAPI main entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.ml.model_loader import load_all_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("  DataCartAI API starting...")
    load_all_models()
    print("  Server ready!")
    print("=" * 50)
    yield
    print("Server shutting down.")


app = FastAPI(
    title       = "DataCartAI API",
    description = "Real-time product scraping + ML-powered recommendations",
    version     = "5.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

app.include_router(router, prefix="/api", tags=["DataCartAI"])


@app.get("/")
async def root():
    return {
        "status": "running",
        "endpoints": {
            "search":        "GET  /api/search?q=gaming+phone+under+15000",
            "compare_prices":"GET  /api/compare?name=Poco+X5+Pro",
            "health":        "GET  /api/health",
            "api_docs":      "GET  /docs",
        },
    }