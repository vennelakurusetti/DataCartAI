"""
DataCartAI — All API Routes (v5 Final)
Scrape → ML Recommend → Sentiment → Price Compare
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import re, time, json, os
from pathlib import Path

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# Lazy imports so server starts even if selenium not installed
# ─────────────────────────────────────────────────────────────
def _get_scraper():
    from app.scraper.selenium_scraper import scrape_stage1, scrape_stage2
    return scrape_stage1, scrape_stage2

def _get_recommender():
    from app.ml.recommender import recommend
    return recommend

def _get_sentiment():
    from app.ml.sentiment_scorer import score_sentiment
    return score_sentiment

def _get_parser():
    from app.ml.intent_parser import parse_query
    return parse_query


# ─────────────────────────────────────────────────────────────
# ROUTE 1 — Full pipeline (what frontend calls)
# ─────────────────────────────────────────────────────────────
@router.get("/search")
async def search(
    q:      str = Query(..., description="Natural language query"),
    budget: int = Query(0,   description="Max price in rupees"),
):
    """
    Main search endpoint.
    1. Parse query (NLP)
    2. Scrape live products
    3. Run ML recommendation model
    Returns ranked products with explanations.
    """
    if not q.strip():
        raise HTTPException(400, "Query cannot be empty")

    # Step 1: parse query
    parse_query = _get_parser()
    parsed      = parse_query(q)
    intent      = parsed.get("intent") or "general"
    budget      = budget or parsed.get("budget") or 999999

    # Step 2: scrape
    try:
        scrape_stage1, _ = _get_scraper()
        scraped = scrape_stage1(q, budget)
    except Exception as e:
        scraped = []

    # Step 3: ML recommend
    try:
        recommend = _get_recommender()
        ranked    = recommend(scraped, intent, budget)
    except Exception:
        ranked = scraped   # fallback: return scraped without ranking

    return {
        "query":   q,
        "parsed":  parsed,
        "intent":  intent,
        "budget":  budget,
        "count":   len(ranked),
        "products":ranked,
    }


@router.get("/compare")
async def compare(name: str = Query(..., description="Product name")):
    """Stage 2 — price comparison across stores."""
    try:
        _, scrape_stage2 = _get_scraper()
        prices = scrape_stage2(name)
        return {"product": name, "prices": prices}
    except Exception as e:
        raise HTTPException(500, f"Scraper error: {e}")


@router.post("/recommend")
async def recommend_api(body: dict):
    """Run ML model on a list of products."""
    products = body.get("products", [])
    intent   = body.get("intent", "general")
    budget   = body.get("budget", 999999)
    recommend = _get_recommender()
    ranked    = recommend(products, intent, budget)
    return {"count": len(ranked), "products": ranked}


@router.get("/health")
async def health():
    from app.ml.model_loader import model_is_loaded, model_type
    return {
        "status":    "ok",
        "ml_model":  "loaded" if model_is_loaded() else "fallback",
        "model_type": model_type(),
        "intent_parser": "regex-based",
    }