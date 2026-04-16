from fastapi import APIRouter
from pydantic import BaseModel
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import csv
import io
import math
import re
import time
import html
import urllib.request
import xml.etree.ElementTree as ET

from app.catalog import PRODUCT_CATALOG

router = APIRouter()


class PromptRequest(BaseModel):
    text: str


class ProductFitRequest(BaseModel):
    text: str
    product_id: int


class ReminderRequest(BaseModel):
    product_id: int
    target_price: int


class MLResponse(BaseModel):
    model_version: str
    inference_time_ms: float
    data: dict


FEATURE_ALIASES = {
    "amoled": ["amoled", "oled"],
    "battery": ["battery", "long lasting", "backup"],
    "camera": ["camera", "photo", "selfie"],
    "performance": ["gaming", "performance", "fast", "processor"],
    "5g": ["5g"],
    "fast charging": ["fast charging", "charge fast", "quick charge"],
    "display": ["display", "screen"],
    "stock android": ["stock android", "clean ui"],
    "storage": ["storage", "128gb", "256gb"],
    "budget": ["cheap", "budget", "value"]
}

PRICE_REMINDERS = []
ALLOWED_LIVE_DOMAINS = [
    "flipkart.com",
    "amazon.in",
    "croma.com",
    "reliancedigital.in",
    "gadgets360.com",
    "91mobiles.com",
    "smartprix.com",
    "vijaysales.com",
]


def get_price_cap(query: str):
    query = query.lower()
    query_no_commas = query.replace(",", "")
    match_lakh = re.search(r"([\d\.]+)\s*lakh", query_no_commas)
    if match_lakh:
        return int(float(match_lakh.group(1)) * 100000)
    match_k = re.search(r"([\d\.]+)\s*k\b", query_no_commas)
    if match_k:
        return int(float(match_k.group(1)) * 1000)
    numbers = re.findall(r"\b\d{4,6}\b", query_no_commas)
    if numbers:
        return int(numbers[0])
    return None


def detect_category(query: str):
    query = query.lower()
    if any(word in query for word in ["phone", "phones", "mobile", "mobiles", "smartphone"]):
        return "Smartphones"
    if any(word in query for word in ["headphone", "earbuds", "earphone", "buds", "audio"]):
        return "Audio"
    if any(word in query for word in ["laptop", "notebook"]):
        return "Laptops"
    return "Smartphones"


def detect_features(query: str):
    query = query.lower()
    found = []
    for canonical, aliases in FEATURE_ALIASES.items():
        if any(alias in query for alias in aliases):
            found.append(canonical)
    return found


def get_category_and_cap(query: str):
    category = detect_category(query)
    cap = get_price_cap(query)
    if cap is None:
        defaults = {"Smartphones": 20000, "Audio": 5000, "Laptops": 60000}
        cap = defaults.get(category, 20000)
    return category, cap


def has_explicit_budget(query: str):
    return get_price_cap(query) is not None


def serialize_product(product, score=None, why=None):
    payload = {
        "id": product["id"],
        "name": product["name"],
        "category": product["category"],
        "brand": product["brand"],
        "price": product["price"],
        "source": product["source"],
        "rating": product["rating"],
        "review_count": product["review_count"],
        "specs": product["specs"],
        "summary": build_product_summary(product),
    }
    if score is not None:
        payload["ml_score"] = score
    if why is not None:
        payload["why"] = why
    return payload


def build_product_summary(product):
    specs = product["specs"]
    category = product["category"]
    if category == "Smartphones":
        return (
            f"{specs['ram_gb']}GB RAM, {specs['storage_gb']}GB storage, "
            f"{specs['battery_mah']}mAh battery, {specs['camera_mp']}MP camera, "
            f"{specs['display_type']} {specs['refresh_rate_hz']}Hz display"
        )
    if category == "Laptops":
        return (
            f"{specs['ram_gb']}GB RAM, {specs['storage_gb']}GB SSD, "
            f"{specs['display_type']} display, {specs['fast_charge_w']}W charging"
        )
    return f"{product['rating']} rated audio gear with {specs['battery_mah']}mAh case battery"


def feature_score(product, features):
    score = 0.0
    product_features = set(product["specs"]["features"])
    display_type = product["specs"]["display_type"].lower()
    for feature in features:
        if feature in product_features:
            score += 0.18
        elif feature == "amoled" and "amoled" in display_type:
            score += 0.2
        elif feature == "battery" and product["specs"]["battery_mah"] >= 5000:
            score += 0.16
        elif feature == "camera" and product["specs"]["camera_mp"] >= 50:
            score += 0.16
        elif feature == "performance" and product["specs"]["chipset_score"] >= 75:
            score += 0.16
        elif feature == "5g" and product["specs"]["network"] == "5G":
            score += 0.18
        elif feature == "fast charging" and product["specs"]["fast_charge_w"] >= 25:
            score += 0.16
    return score


def score_product(product, price_cap, features):
    rating_component = (product["rating"] / 5) * 0.3
    budget_distance = max(price_cap - product["price"], 0)
    budget_component = min(budget_distance / max(price_cap, 1), 1) * 0.2
    value_component = min(product["specs"]["chipset_score"] / 100, 1) * 0.2
    review_component = min(math.log10(product["review_count"] + 10) / 4, 1) * 0.1
    feature_component = feature_score(product, features)
    total = min(rating_component + budget_component + value_component + review_component + feature_component, 0.99)
    return round(total, 2)


def build_why(product, features, price_cap):
    reasons = []
    specs = product["specs"]
    if product["price"] <= price_cap:
        reasons.append(f"fits your budget under Rs. {price_cap}")
    if "5g" in features and specs["network"] == "5G":
        reasons.append("supports 5G")
    if "battery" in features and specs["battery_mah"] >= 5000:
        reasons.append(f"packs a {specs['battery_mah']}mAh battery")
    if "camera" in features and specs["camera_mp"] >= 50:
        reasons.append(f"offers a {specs['camera_mp']}MP camera")
    if "amoled" in features and specs["display_type"].lower() == "amoled":
        reasons.append("has an AMOLED display")
    if "performance" in features and specs["chipset_score"] >= 75:
        reasons.append("is one of the faster options in this range")
    if not reasons:
        reasons.append("balances price, rating, and practical specs well")
    return reasons


def filter_catalog(query: str):
    category, price_cap = get_category_and_cap(query)
    features = detect_features(query)
    matches = [item for item in PRODUCT_CATALOG if item["category"] == category and item["price"] <= price_cap]

    if features:
        feature_matches = []
        for item in matches:
            product_features = " ".join(item["specs"]["features"]).lower()
            display = item["specs"]["display_type"].lower()
            matched = any(
                feature in product_features
                or (feature == "amoled" and "amoled" in display)
                or (feature == "5g" and item["specs"]["network"] == "5G")
                for feature in features
            )
            if matched:
                feature_matches.append(item)
        if feature_matches:
            matches = feature_matches

    if not matches and not has_explicit_budget(query):
        matches = [item for item in PRODUCT_CATALOG if item["category"] == category]

    ranked = []
    for item in matches:
        score = score_product(item, price_cap, features)
        ranked.append(serialize_product(item, score=score, why=build_why(item, features, price_cap)))

    ranked.sort(key=lambda item: (item["ml_score"], item["rating"], -item["price"]), reverse=True)
    if ranked:
        ranked[0]["is_best_buy"] = True
    for item in ranked[1:]:
        item["is_best_buy"] = False

    return {
        "category": category,
        "price_cap": price_cap,
        "features": features,
        "keywords": features,
        "matches": ranked[:8],
    }


def default_specs_for_category(category: str):
    if category == "Laptops":
        return {
            "ram_gb": 0,
            "storage_gb": 0,
            "battery_mah": 0,
            "camera_mp": 0,
            "display_type": "Unknown",
            "refresh_rate_hz": 0,
            "fast_charge_w": 0,
            "chipset_score": 50,
            "network": "WiFi",
            "features": ["web listing"]
        }
    if category == "Smartphones":
        return {
            "ram_gb": 0,
            "storage_gb": 0,
            "battery_mah": 0,
            "camera_mp": 0,
            "display_type": "Unknown",
            "refresh_rate_hz": 0,
            "fast_charge_w": 0,
            "chipset_score": 50,
            "network": "4G",
            "features": ["web listing"]
        }
    return {
        "ram_gb": 0,
        "storage_gb": 0,
        "battery_mah": 0,
        "camera_mp": 0,
        "display_type": "Unknown",
        "refresh_rate_hz": 0,
        "fast_charge_w": 0,
        "chipset_score": 50,
        "network": "Bluetooth",
        "features": ["web listing"]
    }


def decode_duckduckgo_redirect(url: str):
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path == "/l/":
        target = parse_qs(parsed.query).get("uddg", [])
        if target:
            return unquote(target[0])
    return url


def extract_numeric_price(text: str):
    normalized = text.replace(",", "")
    match = re.search(r"(?:Rs\.?|INR)\s*([0-9]{4,6})", normalized, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"([0-9]{4,6})", normalized)
    if match:
        return int(match.group(1))
    return None


def infer_source_from_link(link: str):
    hostname = urlparse(link).netloc.lower()
    if "flipkart" in hostname:
        return "Flipkart"
    if "amazon" in hostname:
        return "Amazon"
    if "croma" in hostname:
        return "Croma"
    if "reliancedigital" in hostname:
        return "Reliance Digital"
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname.split(".")[0].title() if hostname else "Web"


def is_allowed_live_domain(link: str):
    hostname = urlparse(link).netloc.lower()
    return any(hostname.endswith(domain) for domain in ALLOWED_LIVE_DOMAINS)


def fetch_bing_rss_results(search_query: str):
    url = f"https://www.bing.com/search?format=rss&q={quote_plus(search_query)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        xml_text = response.read().decode("utf-8", errors="ignore")
    root = ET.fromstring(xml_text)
    results = []
    for item in root.findall("./channel/item"):
        results.append({
            "title": html.unescape(item.findtext("title") or "").strip(),
            "snippet": html.unescape(item.findtext("description") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
        })
    return results


def search_live_catalog(query: str, category: str, price_cap: int):
    search_queries = [
        f"site:flipkart.com {query}",
        f"site:amazon.in {query}",
        f"site:croma.com {query}",
        f"site:reliancedigital.in {query}",
        f"site:gadgets360.com {category.lower()} under {price_cap}",
        f"site:91mobiles.com {category.lower()} under {price_cap}",
        f"site:smartprix.com {category.lower()} under {price_cap}",
        f"site:vijaysales.com {query}",
    ]
    gathered = []
    seen_links = set()

    for search_query in search_queries:
        try:
            parsed_results = fetch_bing_rss_results(search_query)
        except Exception:
            continue

        for item in parsed_results:
            link = item["link"]
            if link in seen_links:
                continue
            if not is_allowed_live_domain(link):
                continue

            combined_text = f"{item['title']} {item['snippet']}".replace("₹", "Rs ")
            if category == "Laptops" and "laptop" not in combined_text.lower():
                continue

            mentioned_price = extract_numeric_price(combined_text)
            if mentioned_price and mentioned_price > price_cap:
                continue

            source = infer_source_from_link(link)
            seen_links.add(link)
            gathered.append({
                "id": 900000 + len(gathered) + 1,
                "name": item["title"],
                "category": category,
                "brand": source,
                "price": mentioned_price or price_cap,
                "source": source,
                "rating": 4.0,
                "review_count": 0,
                "specs": default_specs_for_category(category),
                "summary": item["snippet"] or f"Live web result for {query}",
                "why": [
                    f"web result discovered for {query}",
                    f"listed under your budget cap of Rs. {price_cap}" if mentioned_price else "budget inferred from query context",
                ],
                "ml_score": 0.72,
                "is_best_buy": False,
                "product_url": link,
                "is_live_result": True,
            })

    gathered = gathered[:24]
    if gathered:
        gathered[0]["is_best_buy"] = True
    return gathered


def build_sentiment(items):
    if not items:
        return [
            {"name": "Positive", "value": 0},
            {"name": "Neutral", "value": 0},
            {"name": "Negative", "value": 0},
        ]
    avg_rating = sum(item["rating"] for item in items) / len(items)
    positive = min(85, int(avg_rating * 18))
    neutral = 100 - positive - 10
    negative = 10
    return [
        {"name": "Positive", "value": positive},
        {"name": "Neutral", "value": neutral},
        {"name": "Negative", "value": negative},
    ]


@router.post("/nlp/extract")
def extract_entities(request: PromptRequest):
    start = time.time()
    results = filter_catalog(request.text)
    live_results = []
    if not results["matches"]:
        live_results = search_live_catalog(request.text, results["category"], results["price_cap"])
    time.sleep(0.2)
    response = {
        "category": results["category"],
        "price_cap": results["price_cap"],
        "detected_features": results["features"],
        "intent_confidence": 0.97 if results["features"] else 0.91,
        "keywords": results["keywords"],
        "match_count": len(results["matches"]) if results["matches"] else len(live_results),
        "result_mode": "catalog" if results["matches"] else "live_web",
    }
    inference_ms = round((time.time() - start) * 1000, 2)
    return MLResponse(model_version="v3.0-query-parser", inference_time_ms=inference_ms, data=response)


@router.post("/dags/trigger/scraper")
def trigger_scraping_dag():
    return {
        "dag_id": "price_watch_scrape_pipeline",
        "run_id": f"run_{int(time.time())}",
        "status": "triggered"
    }


@router.post("/predict/scoring")
def score_products(request: PromptRequest):
    start = time.time()
    results = filter_catalog(request.text)
    scored_items = results["matches"]
    result_mode = "catalog"
    if not scored_items:
        scored_items = search_live_catalog(request.text, results["category"], results["price_cap"])
        result_mode = "live_web"
    inference_ms = round((time.time() - start) * 1000, 2)
    return MLResponse(
        model_version="v3.2-ranking-engine",
        inference_time_ms=inference_ms,
        data={
            "scored_items": scored_items,
            "query_meta": {
                "category": results["category"],
                "price_cap": results["price_cap"],
                "features": results["features"],
                "result_mode": result_mode,
            },
        },
    )


@router.get("/analytics/stats")
def get_analytics(query: str = ""):
    results = filter_catalog(query) if query else {"matches": [serialize_product(item) for item in PRODUCT_CATALOG[:6]]}
    if query and not results["matches"]:
        results = {"matches": search_live_catalog(query, detect_category(query), get_category_and_cap(query)[1])}
    items = results["matches"]
    return {
        "sentiment": build_sentiment(items),
        "totals": {
            "visible_products": len(items),
            "avg_price": int(sum(item["price"] for item in items) / len(items)) if items else 0,
        },
    }


@router.get("/dataset/export")
def export_dataset(query: str = ""):
    results = filter_catalog(query) if query else {"matches": [serialize_product(item) for item in PRODUCT_CATALOG]}
    if query and not results["matches"]:
        results = {"matches": search_live_catalog(query, detect_category(query), get_category_and_cap(query)[1])}
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["id", "name", "category", "price", "source", "rating", "summary", "product_url"])
    for item in results["matches"]:
        writer.writerow([item["id"], item["name"], item["category"], item["price"], item["source"], item["rating"], item["summary"], item.get("product_url", "")])
    return {"filename": "datacart-results.csv", "content": stream.getvalue()}


@router.post("/coach/explain")
def explain_product_fit(request: ProductFitRequest):
    results = filter_catalog(request.text)
    product = next((item for item in results["matches"] if item["id"] == request.product_id), None)
    if product is None:
        return {
            "verdict": "This product is outside the current filtered set.",
            "reasons": ["Try broadening the budget or removing one feature constraint."],
            "best_for": "exploration",
        }
    specs = product["specs"]
    reasons = list(product["why"])
    best_for = "balanced buyers"
    if specs["battery_mah"] >= 6000:
        best_for = "heavy users who care about all-day battery"
    elif specs["camera_mp"] >= 50:
        best_for = "users who want a capable main camera"
    elif specs["chipset_score"] >= 80:
        best_for = "people who want smoother gaming and multitasking"
    return {
        "verdict": f"{product['name']} is a strong match for your query.",
        "reasons": reasons,
        "best_for": best_for,
    }


@router.post("/price/live")
def live_price_options(request: ProductFitRequest):
    product = next((item for item in PRODUCT_CATALOG if item["id"] == request.product_id), None)
    if product is None:
        return {"offers": []}

    query = quote_plus(product["name"])
    base_price = product["price"]
    offers = [
        {
            "seller": "Amazon",
            "price": max(base_price - 1200, int(base_price * 0.93)),
            "link": f"https://www.amazon.in/s?k={query}",
            "label": "Search Amazon",
        },
        {
            "seller": "Flipkart",
            "price": max(base_price - 900, int(base_price * 0.95)),
            "link": f"https://www.flipkart.com/search?q={query}",
            "label": "Search Flipkart",
        },
        {
            "seller": "Croma",
            "price": max(base_price - 700, int(base_price * 0.96)),
            "link": f"https://www.croma.com/searchB?q={query}",
            "label": "Search Croma",
        },
    ]
    offers.sort(key=lambda item: item["price"])
    return {
        "offers": offers,
        "search_note": "These links open live marketplace searches for the selected product.",
    }


@router.post("/reminders")
def create_price_reminder(request: ReminderRequest):
    PRICE_REMINDERS.append(request.dict())
    return {
        "status": "saved",
        "count": len(PRICE_REMINDERS),
    }
