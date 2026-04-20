"""
DataCartAI — API Routes
Endpoints: search, best-price, fit, enrich
"""
from fastapi import APIRouter, Query
from typing import Optional
import math
import random

from app.catalog import search as catalog_search, ALL_PRODUCTS

router = APIRouter()


@router.get("/search")
async def search_products(q: str = Query(..., description="Natural language query")):
    results = catalog_search(q)
    # Ensure images are added to all products in the result
    from app.catalog import add_images
    results = add_images(results)
    return {"query": q, "count": len(results), "products": results}


@router.get("/best-price")
async def best_price(name: str = Query(...), price: Optional[int] = Query(None)):
    base = price or 15000
    stores = [
        {"store": "Amazon", "icon": "🛒", "discount": 0.08, "tag": "Prime Deal", "base_url": f"https://www.amazon.in/s?k={name.replace(' ','+')}"},
        {"store": "Flipkart", "icon": "🛍️", "discount": 0.06, "tag": "Big Saving Days", "base_url": f"https://www.flipkart.com/search?q={name.replace(' ','+')}"},
        {"store": "Croma", "icon": "🏪", "discount": 0.03, "tag": "Store Price", "base_url": f"https://www.croma.com/searchB?q={name.replace(' ','+')}"},
        {"store": "Reliance Digital", "icon": "📦", "discount": 0.01, "tag": "EMI Available", "base_url": f"https://www.reliancedigital.in/search?q={name.replace(' ','+')}"},
        {"store": "Vijay Sales", "icon": "🏬", "discount": 0.04, "tag": "Exchange Offer", "base_url": f"https://www.vijaysales.com/search/{name.replace(' ','-')}"},
    ]
    results = [
        {
            "store": s["store"],
            "icon": s["icon"],
            "price": math.floor(base * (1 - s["discount"])),
            "tag": s["tag"],
            "url": s["base_url"],
        }
        for s in stores
    ]
    results.sort(key=lambda r: r["price"])
    return {"product": name, "results": results}


@router.get("/fit")
async def product_fit(
    name: str = Query(...),
    use: str = Query("social"),
    priority: str = Query("balance"),
    price: Optional[int] = Query(None),
):
    product_price = price or 10000
    use_map = {
        "gaming": ("gaming & performance", ["processor", "ram"], "🎮"),
        "camera": ("photography", ["camera"], "📸"),
        "work": ("productivity & work", ["ram", "storage", "display"], "💼"),
        "social": ("social media & daily use", ["display", "camera"], "📱"),
        "battery": ("long battery life", ["battery"], "🔋"),
    }
    ctx_label, ctx_keys, ctx_emoji = use_map.get(use, use_map["social"])
    product = next((p for p in ALL_PRODUCTS if name.lower() in p["name"].lower()), None)
    score_parts = []
    if product:
        for k in ctx_keys:
            if product.get(k):
                score_parts.append(f"{k.title()}: **{product[k]}**")

    verdict = f"{ctx_emoji} **{name}** for {ctx_label}:\n\n"
    if score_parts:
        verdict += "✅ Key specs: " + " | ".join(score_parts) + "\n\n"

    if priority == "very" and product_price > 15000:
        verdict += "💡 **Budget tip:** You might find better value in the ₹10k–12k range. Consider Redmi 13C or Realme C55 for similar daily use."
    elif priority == "premium":
        verdict += "🚀 **Premium tip:** If features matter more than price, look at ₹20k+ options like iQOO Z7 5G or Nothing Phone 1 for AMOLED displays and faster chips."
    else:
        verdict += "✅ **Verdict:** Great value-for-money pick! Well-balanced specs for the price."

    return {"product": name, "use": use, "priority": priority, "verdict": verdict}


@router.get("/enrich")
async def enrich_dataset(q: Optional[str] = Query(None), prompt: Optional[str] = Query(None)):
    base_results = catalog_search(q or "phones under 20000")
    enriched = []
    for p in base_results:
        ep = dict(p)
        ep["weight"] = f"{random.randint(160, 210)}g"
        ep["colors"] = random.choice(["Black, Blue", "Black, White, Green", "Midnight Blue, Arctic White", "Phantom Black, Ice Blue"])
        ep["5g_ready"] = "Yes" if ep.get("connectivity") == "5G" else "No"
        ep["release_year"] = random.choice([2022, 2023, 2024])
        ep["warranty"] = "1 Year Manufacturer"
        enriched.append(ep)
    return {"products": enriched, "enriched_columns": ["weight", "colors", "5g_ready", "release_year", "warranty"]}


@router.get("/health")
async def health():
    return {"status": "ok", "products_loaded": len(ALL_PRODUCTS)}
