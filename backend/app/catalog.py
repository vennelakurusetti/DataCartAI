"""
DataCartAI — Product Catalog
Rich dataset of phones, laptops, earbuds, watches.
"""
from __future__ import annotations
import re
from typing import List, Dict, Any

# ─────────────────────────────────────────────────────────────
# PHONES
# ─────────────────────────────────────────────────────────────
PHONES: List[Dict[str, Any]] = [
    {"id": "p001", "name": "Redmi 13C", "brand": "Xiaomi", "category": "Phone", "price": 8999, "ram": "4GB", "storage": "128GB", "battery": "5000 mAh", "camera": "50MP Triple", "display": '6.74" IPS LCD', "processor": "MediaTek Helio G85", "os": "MIUI 14", "connectivity": "4G", "rating": 4.1},
    {"id": "p002", "name": "Realme C55", "brand": "Realme", "category": "Phone", "price": 9999, "ram": "6GB", "storage": "128GB", "battery": "5000 mAh", "camera": "64MP Dual", "display": '6.72" IPS 90Hz', "processor": "MediaTek Helio G88", "os": "Realme UI 4", "connectivity": "4G", "rating": 4.2},
    {"id": "p003", "name": "Samsung Galaxy A04", "brand": "Samsung", "category": "Phone", "price": 7999, "ram": "4GB", "storage": "64GB", "battery": "5000 mAh", "camera": "50MP Dual", "display": '6.5" PLS TFT', "processor": "Exynos 850", "os": "Android 12", "connectivity": "4G", "rating": 3.9},
    {"id": "p004", "name": "Poco C65", "brand": "Poco", "category": "Phone", "price": 8499, "ram": "6GB", "storage": "128GB", "battery": "5000 mAh", "camera": "50MP Triple", "display": '6.74" IPS LCD', "processor": "MediaTek Helio G85", "os": "MIUI 14", "connectivity": "4G", "rating": 4.0},
    {"id": "p005", "name": "Infinix Hot 30i", "brand": "Infinix", "category": "Phone", "price": 6999, "ram": "4GB", "storage": "64GB", "battery": "5000 mAh", "camera": "13MP Dual", "display": '6.56" IPS', "processor": "MediaTek Helio G37", "os": "XOS 12", "connectivity": "4G", "rating": 3.8},
    {"id": "p006", "name": "Tecno Spark 20", "brand": "Tecno", "category": "Phone", "price": 9499, "ram": "8GB", "storage": "128GB", "battery": "5000 mAh", "camera": "50MP Dual", "display": '6.56" IPS 90Hz', "processor": "MediaTek Helio G85", "os": "HiOS 13", "connectivity": "4G", "rating": 4.1},
    {"id": "p007", "name": "Lava Blaze 2 5G", "brand": "Lava", "category": "Phone", "price": 9999, "ram": "4GB", "storage": "128GB", "battery": "4500 mAh", "camera": "50MP Dual", "display": '6.5" IPS', "processor": "Dimensity 700", "os": "Android 13", "connectivity": "5G", "rating": 3.9},
    {"id": "p008", "name": "Motorola Moto E13", "brand": "Motorola", "category": "Phone", "price": 7499, "ram": "4GB", "storage": "64GB", "battery": "5000 mAh", "camera": "13MP Single", "display": '6.5" IPS', "processor": "Unisoc T606", "os": "Android 13 Go", "connectivity": "4G", "rating": 3.8},
    {"id": "p009", "name": "Redmi A2+", "brand": "Xiaomi", "category": "Phone", "price": 6499, "ram": "2GB", "storage": "32GB", "battery": "5000 mAh", "camera": "8MP Single", "display": '6.52" IPS', "processor": "MediaTek Helio G36", "os": "MIUI Go", "connectivity": "4G", "rating": 3.6},
    {"id": "p010", "name": "Redmi Note 12 5G", "brand": "Xiaomi", "category": "Phone", "price": 14999, "ram": "4GB", "storage": "128GB", "battery": "5000 mAh", "camera": "48MP Triple", "display": '6.67" AMOLED 120Hz', "processor": "Snapdragon 4 Gen 1", "os": "MIUI 13", "connectivity": "5G", "rating": 4.3},
    {"id": "p011", "name": "Realme Narzo N55", "brand": "Realme", "category": "Phone", "price": 11999, "ram": "4GB", "storage": "64GB", "battery": "5000 mAh", "camera": "64MP Dual", "display": '6.72" IPS 90Hz', "processor": "MediaTek Helio G88", "os": "Realme UI 4", "connectivity": "4G", "rating": 4.3},
    {"id": "p012", "name": "iQOO Z7 5G", "brand": "iQOO", "category": "Phone", "price": 18999, "ram": "6GB", "storage": "128GB", "battery": "4400 mAh", "camera": "64MP Dual", "display": '6.38" AMOLED 90Hz', "processor": "Dimensity 920", "os": "FunTouchOS 13", "connectivity": "5G", "rating": 4.4},
    {"id": "p013", "name": "Samsung Galaxy M14 5G", "brand": "Samsung", "category": "Phone", "price": 13490, "ram": "4GB", "storage": "128GB", "battery": "6000 mAh", "camera": "50MP Triple", "display": '6.6" PLS', "processor": "Exynos 1330", "os": "Android 13", "connectivity": "5G", "rating": 4.2},
    {"id": "p014", "name": "OnePlus Nord CE 3 Lite 5G", "brand": "OnePlus", "category": "Phone", "price": 19999, "ram": "8GB", "storage": "128GB", "battery": "5000 mAh", "camera": "108MP Triple", "display": '6.72" IPS 120Hz', "processor": "Snapdragon 695", "os": "OxygenOS 13", "connectivity": "5G", "rating": 4.3},
    {"id": "p015", "name": "Nothing Phone (1)", "brand": "Nothing", "category": "Phone", "price": 19999, "ram": "8GB", "storage": "128GB", "battery": "4500 mAh", "camera": "50MP Dual", "display": '6.55" AMOLED 120Hz', "processor": "Snapdragon 778G+", "os": "Nothing OS", "connectivity": "5G", "rating": 4.4},
    {"id": "p016", "name": "Poco X5 Pro 5G", "brand": "Poco", "category": "Phone", "price": 22999, "ram": "6GB", "storage": "128GB", "battery": "5000 mAh", "camera": "108MP Triple", "display": '6.67" AMOLED 120Hz', "processor": "Snapdragon 778G", "os": "MIUI 14", "connectivity": "5G", "rating": 4.4},
    {"id": "p017", "name": "Samsung Galaxy A34 5G", "brand": "Samsung", "category": "Phone", "price": 30999, "ram": "8GB", "storage": "128GB", "battery": "5000 mAh", "camera": "48MP Triple", "display": '6.6" SuperAMOLED 120Hz', "processor": "Dimensity 1080", "os": "Android 13", "connectivity": "5G", "rating": 4.4},
    {"id": "p018", "name": "Realme GT 3", "brand": "Realme", "category": "Phone", "price": 34999, "ram": "8GB", "storage": "256GB", "battery": "4600 mAh 240W", "camera": "50MP Triple", "display": '6.74" AMOLED 144Hz', "processor": "Snapdragon 8+ Gen 1", "os": "Realme UI 4", "connectivity": "5G", "rating": 4.5},
]

LAPTOPS: List[Dict[str, Any]] = [
    {"id": "l001", "name": "Lenovo IdeaPad Slim 3", "brand": "Lenovo", "category": "Laptop", "price": 29990, "ram": "8GB", "storage": "512GB SSD", "display": '15.6" FHD IPS', "processor": "Ryzen 5 5500U", "os": "Windows 11 Home", "battery": "45Wh", "weight": "1.65kg", "rating": 4.2},
    {"id": "l002", "name": "HP 15s Ryzen Edition", "brand": "HP", "category": "Laptop", "price": 33000, "ram": "8GB", "storage": "512GB SSD", "display": '15.6" FHD IPS', "processor": "Ryzen 5 5500U", "os": "Windows 11 Home", "battery": "41Wh", "weight": "1.75kg", "rating": 4.1},
    {"id": "l003", "name": "ASUS VivoBook 15", "brand": "ASUS", "category": "Laptop", "price": 35990, "ram": "16GB", "storage": "512GB SSD", "display": '15.6" FHD 144Hz', "processor": "Ryzen 5 5600H", "os": "Windows 11 Home", "battery": "50Wh", "weight": "1.8kg", "rating": 4.3},
    {"id": "l004", "name": "Acer Aspire Lite", "brand": "Acer", "category": "Laptop", "price": 27990, "ram": "8GB", "storage": "512GB SSD", "display": '15.6" FHD IPS', "processor": "Core i3-1215U", "os": "Windows 11 Home", "battery": "48Wh", "weight": "1.7kg", "rating": 4.0},
    {"id": "l005", "name": "Dell Inspiron 15", "brand": "Dell", "category": "Laptop", "price": 39990, "ram": "8GB", "storage": "512GB SSD", "display": '15.6" FHD IPS', "processor": "Core i5-1235U", "os": "Windows 11 Home", "battery": "54Wh", "weight": "1.75kg", "rating": 4.2},
    {"id": "l006", "name": "Xiaomi Redmibook 15", "brand": "Xiaomi", "category": "Laptop", "price": 38990, "ram": "8GB", "storage": "512GB SSD", "display": '15.6" FHD IPS', "processor": "Core i5-1155G7", "os": "Windows 11 Home", "battery": "46Wh", "weight": "1.8kg", "rating": 4.1},
]

EARBUDS: List[Dict[str, Any]] = [
    {"id": "e001", "name": "boAt Airdopes 141", "brand": "boAt", "category": "Earbuds", "price": 999, "battery": "42H total", "rating": 4.1, "display": "N/A"},
    {"id": "e002", "name": "Noise Air Buds Pro 2", "brand": "Noise", "category": "Earbuds", "price": 1599, "battery": "36H total", "rating": 4.0, "display": "N/A"},
    {"id": "e003", "name": "JBL Wave Flex", "brand": "JBL", "category": "Earbuds", "price": 2999, "battery": "32H total", "rating": 4.3, "display": "N/A"},
    {"id": "e004", "name": "OnePlus Nord Buds 2", "brand": "OnePlus", "category": "Earbuds", "price": 2499, "battery": "38H total", "rating": 4.2, "display": "N/A"},
    {"id": "e005", "name": "Realme Buds T100", "brand": "Realme", "category": "Earbuds", "price": 1299, "battery": "28H total", "rating": 3.9, "display": "N/A"},
]

WATCHES: List[Dict[str, Any]] = [
    {"id": "w001", "name": "Noise ColorFit Ultra 3", "brand": "Noise", "category": "Watch", "price": 2999, "battery": "7 days", "display": '1.96" AMOLED', "rating": 4.1},
    {"id": "w002", "name": "boAt Lunar Prime", "brand": "boAt", "category": "Watch", "price": 3499, "battery": "7 days", "display": '1.78" AMOLED', "rating": 4.0},
    {"id": "w003", "name": "Fastrack Limitless FS1", "brand": "Fastrack", "category": "Watch", "price": 4499, "battery": "10 days", "display": '1.96" AMOLED', "rating": 4.2},
    {"id": "w004", "name": "Amazfit Bip 3", "brand": "Amazfit", "category": "Watch", "price": 4999, "battery": "14 days", "display": '1.69" TFT', "rating": 4.1},
]

ALL_PRODUCTS = PHONES + LAPTOPS + EARBUDS + WATCHES


def search(query: str) -> List[Dict[str, Any]]:
    """Parse natural language query and return matching products."""
    q = query.lower().strip()

    budget = float("inf")
    for pattern in [r"under\s*₹?\s*(\d[\d,]*)\s*k", r"under\s*₹?\s*(\d[\d,]*000)", r"below\s*₹?\s*(\d[\d,]*)\s*k", r"₹?\s*(\d[\d,]*)\s*k\s*(budget|limit|max)?", r"(\d[\d,]*)\s*rupees?"]:
        m = re.search(pattern, q)
        if m:
            val = int(m.group(1).replace(",", ""))
            if "k" in pattern and val < 1000:
                val *= 1000
            budget = val
            break
    if budget == float("inf"):
        m = re.search(r"\b(\d{4,6})\b", q)
        if m:
            budget = int(m.group(1))

    if any(w in q for w in ["laptop", "notebook", "pc", "computer"]):
        pool = LAPTOPS
    elif any(w in q for w in ["earbud", "earphone", "headphone", "tws", "airpods"]):
        pool = EARBUDS
    elif any(w in q for w in ["watch", "smartwatch", "wearable", "band"]):
        pool = WATCHES
    else:
        pool = PHONES

    results = [p for p in pool if p["price"] <= budget]
    results.sort(key=lambda p: (p.get("rating", 0) * budget / max(p["price"], 1)), reverse=True)
    return results
def add_images(products):
    for p in products:
        name = p["name"].replace(" ", "+")
        p["image"] = f"https://source.unsplash.com/300x300/?{name}"
    return products

# apply to each category
PHONES = add_images(PHONES)
LAPTOPS = add_images(LAPTOPS)
EARBUDS = add_images(EARBUDS)
WATCHES = add_images(WATCHES)

# combine
ALL_PRODUCTS = PHONES + LAPTOPS + EARBUDS + WATCHES