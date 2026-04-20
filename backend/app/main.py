"""
DataCartAI — FastAPI main entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="DataCartAI API",
    description="Smart product discovery API — phones, laptops, earbuds under budget",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"message": "DataCartAI API v2.0 is running", "docs": "/docs"}
