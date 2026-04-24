"""
DataCartAI — Intent Parser
============================
Parses a natural-language shopping query into structured intent.
Uses ONLY regex — no spaCy, no ML model needed for this step.

Examples:
  "gaming phone under 15000"
    → { category:"phone", budget:15000, intent:"gaming" }

  "water based serum under 700"
    → { category:"serum", budget:700, intent:"water_based_skincare" }

  "sunscreen with spf 50 under 500"
    → { category:"sunscreen", budget:500, intent:"spf_protection" }

  "long wear lipstick under 800"
    → { category:"lipstick", budget:800, intent:"long_wear_makeup" }
"""
from __future__ import annotations
import re
from typing import Optional


# ─────────────────────────────────────────────────────────────
# CATEGORY KEYWORDS
# ─────────────────────────────────────────────────────────────

CATEGORY_MAP: dict[str, list[str]] = {
    # Electronics
    "phone":      ["phone","mobile","smartphone","handset"],
    "laptop":     ["laptop","notebook","ultrabook"],
    "earbuds":    ["earbuds","tws","airpods","earphones","earphone"],
    "headphone":  ["headphone","headset","over ear","over-ear"],
    "watch":      ["watch","smartwatch","wearable","fitness band"],
    "speaker":    ["speaker","bluetooth speaker","soundbar"],
    "tablet":     ["tablet","ipad"],

    # Skincare
    "sunscreen":    ["sunscreen","sunblock","spf cream","sun cream","uv protect"],
    "serum":        ["serum","face serum","vitamin c serum","niacinamide serum",
                     "hyaluronic serum","water serum"],
    "moisturizer":  ["moisturizer","moisturiser","face cream","day cream",
                     "night cream","face lotion","hydrating cream"],
    "face_wash":    ["face wash","cleanser","foaming wash","gentle wash"],
    "toner":        ["toner","face toner","skin toner"],

    # Makeup
    "lipstick":     ["lipstick","lip colour","lip color","lip gloss",
                     "lip balm","matte lip","liquid lip"],
    "foundation":   ["foundation","bb cream","cc cream","base","coverage"],
    "kajal":        ["kajal","kohl","eyeliner","eye liner"],
    "mascara":      ["mascara"],
    "blush":        ["blush","bronzer","highlighter"],
}


# ─────────────────────────────────────────────────────────────
# INTENT KEYWORDS
# Key: intent label  →  Value: keyword phrases that signal it
# ─────────────────────────────────────────────────────────────

INTENT_MAP: dict[str, list[str]] = {
    # Electronics intents
    "gaming":               ["gaming","game","gamer","pubg","bgmi","cod","esport"],
    "photography":          ["camera","photo","photography","selfie","portrait",
                             "cinematic","video"],
    "battery_life":         ["battery","long battery","backup","all day","power"],
    "work_productivity":    ["work","office","productivity","business","study",
                             "college","professional"],
    "5g_connectivity":      ["5g","five g","5g phone","5g ready"],
    "budget_pick":          ["budget","cheap","affordable","low cost","value",
                             "under","best under","cheapest"],

    # Skincare intents
    "spf_protection":       ["spf","sun protect","uv","sunscreen","uva","uvb",
                             "sun block","spf 50","spf 30"],
    "skincare_hydration":   ["hydrat","moistur","dry skin","dehydrat",
                             "hydration","moisture","glow"],
    "water_based_skincare": ["water based","water-based","oil free","oil-free",
                             "oily skin","non comedogenic","non-comedogenic",
                             "lightweight serum","gel serum"],

    # Makeup intents
    "long_wear_makeup":     ["long wear","long-wear","long lasting","all day",
                             "transfer proof","smudge proof","matte","24 hour"],

    # General
    "general":              [],
}


# ─────────────────────────────────────────────────────────────
# BUDGET EXTRACTION
# ─────────────────────────────────────────────────────────────

def _extract_budget(text: str) -> Optional[int]:
    """
    Handles patterns like:
      under 10000 / under 10k / below ₹500 / less than 20000
      upto 5k / max 15000 / ₹999 / budget of 2000
    """
    t = text.lower().replace(",", "")

    patterns = [
        r"(?:under|below|less\s*than|upto|up\s*to|within|max(?:imum)?|budget\s*of)"
        r"\s*[₹rs\.]*\s*(\d+)\s*(k)?",
        r"[₹rs\.]+\s*(\d+)\s*(k)?",
        r"\b(\d{3,6})\s*(k)?\b",
    ]

    for pat in patterns:
        m = re.search(pat, t)
        if m:
            num = int(m.group(1))
            if m.group(2) and m.group(2).lower() == "k":
                num *= 1000
            if 50 <= num <= 10_00_000:
                return num
    return None


# ─────────────────────────────────────────────────────────────
# CATEGORY EXTRACTION
# ─────────────────────────────────────────────────────────────

def _extract_category(text: str) -> Optional[str]:
    t = text.lower()
    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in t:
                return category
    return None


# ─────────────────────────────────────────────────────────────
# INTENT EXTRACTION
# ─────────────────────────────────────────────────────────────

def _extract_intent(text: str, category: Optional[str]) -> str:
    t = text.lower()

    # Check all explicit intent keywords
    for intent, keywords in INTENT_MAP.items():
        if not keywords:
            continue
        for kw in keywords:
            if kw in t:
                return intent

    # Auto-assign intent based on category when no intent keyword found
    category_default_intent: dict[str, str] = {
        "sunscreen":   "spf_protection",
        "serum":       "skincare_hydration",
        "moisturizer": "skincare_hydration",
        "toner":       "skincare_hydration",
        "face_wash":   "skincare_hydration",
        "lipstick":    "long_wear_makeup",
        "foundation":  "long_wear_makeup",
        "kajal":       "long_wear_makeup",
        "mascara":     "long_wear_makeup",
        "blush":       "long_wear_makeup",
        "laptop":      "work_productivity",
        "tablet":      "work_productivity",
    }

    if category and category in category_default_intent:
        return category_default_intent[category]

    return "general"


# ─────────────────────────────────────────────────────────────
# PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────

def parse_query(query: str) -> dict:
    """
    Parse a natural language shopping query.

    Returns:
      {
        "raw":      "gaming phone under 15000",
        "category": "phone",
        "budget":   15000,
        "intent":   "gaming",
        "method":   "regex"
      }
    """
    if not query or not query.strip():
        return {
            "raw":      query,
            "category": None,
            "budget":   None,
            "intent":   "general",
            "method":   "empty",
        }

    category = _extract_category(query)
    budget   = _extract_budget(query)
    intent   = _extract_intent(query, category)

    return {
        "raw":      query,
        "category": category,
        "budget":   budget,
        "intent":   intent,
        "method":   "regex",
    }


# ─────────────────────────────────────────────────────────────
# QUICK TEST  (run this file directly to test)
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "gaming phone under 15000",
        "best camera phone under 25000",
        "sunscreen with spf 50 under 500",
        "water based serum under 700",
        "long wear lipstick under 800",
        "work laptop under 40000",
        "moisturizer for dry skin under 400",
        "5g phone under 12000",
        "budget earbuds under 1500",
        "oily skin face wash under 300",
    ]

    print(f"\n{'Query':<45} {'Category':<15} {'Budget':>8}  Intent")
    print("─" * 95)
    for q in test_queries:
        r = parse_query(q)
        print(f"  {q:<43} {str(r['category']):<15} "
              f"{str(r['budget'] or '?'):>8}  {r['intent']}")