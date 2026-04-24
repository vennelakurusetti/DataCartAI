"""
DataCartAI — ML Recommender
Uses the trained LightGBM/RF model to rank scraped products.
Falls back to weighted rule scoring if model not yet trained.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from typing import Optional
from app.ml.model_loader import get_recommender, get_label_encoder

FEATURE_COLS = [
    "ram_n","storage_n","battery_n","camera_mp_n","processor_score_n",
    "brand_trust_n","display_score_n","rating_n","spf_value_n",
    "skin_compat_n","is_5g","is_water_based","fragrance_free","long_wear",
    "price_n","cat_enc",
    "f_gaming","f_photography","f_battery","f_work","f_5g",
    "f_budget","f_spf","f_hydration","f_water_based","f_long_wear",
]

CAT_MAP = {"phone":0,"laptop":1,"lipstick":2,"sunscreen":3,
           "moisturizer":4,"serum":5}

def _safe(val, default=0):
    try: return float(str(val).replace("GB","").replace("mAh","")
                              .replace("MP","").replace(",","").strip())
    except: return default

def _extract_features(p: dict) -> dict:
    """Turn a raw scraped product dict into ML feature values."""
    name = (p.get("name") or "").lower()
    cat  = (p.get("category") or "phone").lower()

    ram     = _safe(p.get("ram",     p.get("RAM",     0)), 4)
    storage = _safe(p.get("storage", p.get("Storage", 0)), 64)
    battery = _safe(p.get("battery", p.get("Battery", 0)), 4000)
    if battery < 200: battery *= 80   # Wh → mAh equivalent for laptops
    camera  = _safe(p.get("camera",  p.get("Camera",  0)), 12)
    proc    = _safe(p.get("processor_score", p.get("proc_score", 0)), 5)
    brand   = _safe(p.get("brand_trust", 3), 3)
    disp    = _safe(p.get("display_score", 0), 6)
    rating  = _safe(p.get("rating",  4.0), 4.0)
    if rating > 5: rating /= 2
    spf     = _safe(p.get("spf_value", 0), 0)
    skin    = _safe(p.get("skin_compat", 0), 0)
    is_5g   = 1 if ("5g" in name or p.get("is_5g") == 1) else 0
    water   = int(p.get("is_water_based", 0))
    frag    = int(p.get("fragrance_free", 0))
    lw      = int(p.get("long_wear", 0))
    price   = _safe(p.get("price", 10000), 10000)

    return dict(ram=ram, storage=storage, battery=battery, camera_mp=camera,
                processor_score=proc, brand_trust=brand, display_score=disp,
                rating=rating, spf_value=spf, skin_compat=skin,
                is_5g=is_5g, is_water_based=water, fragrance_free=frag,
                long_wear=lw, price=price, category=cat)


def _normalise(features: dict, all_features: list[dict]) -> dict:
    """Normalise a single product's features against the whole list."""
    maxv = {}
    for f in all_features:
        for k, v in f.items():
            if isinstance(v, (int, float)):
                maxv[k] = max(maxv.get(k, 0), abs(v) + 1e-9)

    d = dict(features)
    for col in ["ram","storage","battery","camera_mp","processor_score",
                "brand_trust","display_score","rating","spf_value","skin_compat"]:
        d[f"{col}_n"] = d.get(col, 0) / maxv.get(col, 1)

    max_price = maxv.get("price", 1)
    d["price_n"] = 1 - (d.get("price", 0) / max_price)
    d["cat_enc"] = CAT_MAP.get(d.get("category","phone"), 0)

    # Intent scores
    d["f_gaming"]     = 0.35*d["processor_score_n"]+0.25*d["ram_n"]+0.20*d["display_score_n"]+0.10*d["storage_n"]+0.10*d["battery_n"]
    d["f_photography"]= 0.50*d["camera_mp_n"]+0.20*d["brand_trust_n"]+0.20*d["display_score_n"]+0.10*d["rating_n"]
    d["f_battery"]    = 0.60*d["battery_n"]+0.20*d["rating_n"]+0.10*d["brand_trust_n"]+0.10*d["processor_score_n"]
    d["f_work"]       = 0.30*d["ram_n"]+0.25*d["storage_n"]+0.20*d["battery_n"]+0.15*d["processor_score_n"]+0.10*d["brand_trust_n"]
    d["f_5g"]         = 0.55*d["is_5g"]+0.20*d["processor_score_n"]+0.15*d["rating_n"]+0.10*d["brand_trust_n"]
    d["f_budget"]     = 0.45*d["price_n"]+0.30*d["rating_n"]+0.25*d["brand_trust_n"]
    d["f_spf"]        = 0.50*d["spf_value_n"]+0.30*d["skin_compat_n"]+0.20*d["brand_trust_n"]
    d["f_hydration"]  = 0.40*d["skin_compat_n"]+0.30*d["brand_trust_n"]+0.20*d["rating_n"]+0.10*d["fragrance_free"]
    d["f_water_based"]= 0.40*d["is_water_based"]+0.30*d["skin_compat_n"]+0.20*d["fragrance_free"]+0.10*d["rating_n"]
    d["f_long_wear"]  = 0.50*d["long_wear"]+0.25*d["brand_trust_n"]+0.25*d["rating_n"]
    return d


EXPLANATIONS = {
    "gaming":             {"phone": "{processor_score}/10 processor + {ram}GB RAM built for gaming.", "laptop": "{ram}GB RAM + {processor_score}/10 processor handles heavy games.", "default": "High-performance specs for gaming."},
    "photography":        {"phone": "{camera_mp}MP camera for stunning shots. {display_score}/10 display.", "default": "Excellent camera for photography."},
    "battery_life":       {"phone": "{battery:,.0f}mAh battery for all-day use.", "default": "Exceptional battery life."},
    "work_productivity":  {"laptop": "{ram}GB RAM + {storage}GB SSD for smooth multitasking.", "default": "Optimised for professional productivity."},
    "5g_connectivity":    {"default": "5G-ready for next-gen high-speed connectivity."},
    "budget_pick":        {"default": "Best value at ₹{price:,.0f} — great specs for the price."},
    "spf_protection":     {"sunscreen": "SPF {spf_value:.0f} shields against UV rays. Skin compatibility: {skin_compat}/5.", "default": "High SPF sun protection."},
    "skincare_hydration": {"moisturizer": "Deep hydration with {skin_compat}/5 skin compatibility.", "serum": "Hydrating serum, compatibility {skin_compat}/5.", "default": "Superior skin hydration."},
    "water_based_skincare":{"serum": "Lightweight water-based formula. Fragrance-free: {'yes' if fragrance_free else 'no'}.", "moisturizer": "Water-based, non-comedogenic hydration.", "default": "Lightweight water-based formulation."},
    "long_wear_makeup":   {"lipstick": "Long-lasting colour. Brand trust: {brand_trust}/5.", "default": "Long-wear formula for all-day staying power."},
    "general":            {"default": "Rated {rating}/5 by users. Brand trust: {brand_trust}/5."},
}

def _explain(features: dict, intent: str) -> str:
    cat      = features.get("category", "")
    tmpl_set = EXPLANATIONS.get(intent, {"default": "Good match."})
    tmpl     = tmpl_set.get(cat) or tmpl_set.get("default", "Good match.")
    try:    return tmpl.format(**features)
    except: return tmpl_set.get("default", "Good match for your needs.")


def recommend(products: list[dict], intent: str = "general",
              budget: int = 0) -> list[dict]:
    if not products:
        return []

    intent = (intent or "general").lower().strip()
    model  = get_recommender()
    le     = get_label_encoder()

    # Extract and filter
    enriched = []
    for p in products:
        f = _extract_features(p)
        if budget and f["price"] > budget:
            continue
        enriched.append((p, f))

    if not enriched:
        return products

    # Normalise all together
    all_f = [f for _, f in enriched]
    normed = [_normalise(f, all_f) for f in all_f]

    # Score with ML model or fallback
    scores = []
    if model is not None and le is not None:
        try:
            import joblib
            X = np.array([[n.get(c, 0) for c in FEATURE_COLS] for n in normed], dtype=float)
            classes = list(le.classes_)
            idx     = classes.index(intent) if intent in classes else 0

            # Try LightGBM first
            try:
                probs   = model.predict(X)
                scores  = probs[:, idx].tolist()
            except Exception:
                # Fallback to sklearn predict_proba
                probs   = model.predict_proba(X)
                scores  = probs[:, idx].tolist()
        except Exception:
            scores = [n.get(f"f_{intent.split('_')[0]}", n.get("f_budget", 0)) for n in normed]
    else:
        intent_map = {
            "gaming":"f_gaming","photography":"f_photography",
            "battery_life":"f_battery","work_productivity":"f_work",
            "5g_connectivity":"f_5g","budget_pick":"f_budget",
            "spf_protection":"f_spf","skincare_hydration":"f_hydration",
            "water_based_skincare":"f_water_based","long_wear_makeup":"f_long_wear",
        }
        feat_key = intent_map.get(intent, "f_budget")
        scores   = [n.get(feat_key, 0) for n in normed]

    # Merge scores back
    result = []
    for i, (orig, _) in enumerate(enriched):
        score = scores[i] if i < len(scores) else 0
        n     = normed[i]
        result.append({
            **orig,
            "match_score": round(float(score) * 100, 1),
            "explanation": _explain(n, intent),
            "rank":        0,
        })

    # Sort by match_score then rating
    result.sort(key=lambda x: (x["match_score"], x.get("rating", 0)), reverse=True)
    for i, r in enumerate(result):
        r["rank"] = i + 1

    return result