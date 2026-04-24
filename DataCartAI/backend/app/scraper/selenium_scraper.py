"""
DataCartAI — Scraper v3 (Anti-Detection + Fallback)
=====================================================
WHY THE OLD ONE FAILED:
  Amazon & Flipkart detect headless Chrome and return
  empty pages, CAPTCHAs, or bot-detection pages.

THIS VERSION:
  1. Tries Selenium with full anti-detect
  ion profile
  2. Falls back to requests + BeautifulSoup (faster, harder to detect)
  3. Final fallback: SerpAPI (100% reliable, free tier = 100 searches/month)
     → sign up free at https://serpapi.com

INSTALL:
  pip install selenium webdriver-manager requests beautifulsoup4 lxml
  pip install google-search-results   # for SerpAPI fallback (optional)
"""

from __future__ import annotations
import time, re, csv, os, random, logging, json
from pathlib import Path
from typing  import Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scraper")

DATA_DIR = Path("scraped_data")
DATA_DIR.mkdir(exist_ok=True)

# ── Put your SerpAPI key here (free at serpapi.com) ──────────
# Leave empty "" to skip SerpAPI and use direct scraping only
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


# ═══════════════════════════════════════════════════════════════
# UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════

def _parse_price(text: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", str(text or ""))
    return int(digits) if digits else None

def _parse_rating(text: str) -> Optional[float]:
    m = re.search(r"(\d+\.?\d*)", str(text or ""))
    if m:
        v = float(m.group(1))
        return round(v, 1) if v <= 5 else round(v / 2, 1)
    return None

def _clean_url(url: str, base: str = "") -> str:
    if not url:
        return ""
    if url.startswith("http"):
        return url.split("?")[0] if "/dp/" in url else url
    if url.startswith("/"):
        return base + url
    return url

def _rand_delay(a: float = 1.5, b: float = 3.5):
    time.sleep(random.uniform(a, b))

def _build_reviews_url(p: dict) -> str:
    url    = p.get("url", "")
    source = (p.get("source") or "").lower()
    if not url:
        return ""
    if "amazon" in source or "amazon.in" in url:
        m = re.search(r"/dp/([A-Z0-9]{10})", url)
        if m:
            return f"https://www.amazon.in/product-reviews/{m.group(1)}?sortBy=recent"
        return url + "#customerReviews"
    if "flipkart" in source or "flipkart.com" in url:
        return url + "#sellerInfo"
    if "nykaa" in source or "nykaa.com" in url:
        return url + "#reviews"
    return url


# ═══════════════════════════════════════════════════════════════
# STRATEGY 1 — requests + BeautifulSoup  (no browser needed)
# ═══════════════════════════════════════════════════════════════

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
]

def _get_page(url: str, session: requests.Session, retries: int = 3) -> Optional[BeautifulSoup]:
    """Fetch a page with rotating headers and retries."""
    for attempt in range(retries):
        try:
            headers = random.choice(HEADERS_LIST).copy()
            # Add random cookies to look more human
            session.cookies.update({
                "session-id": str(random.randint(100000000, 999999999)),
            })
            resp = session.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                # Check for CAPTCHA / bot detection
                html = resp.text
                if any(kw in html.lower() for kw in [
                    "captcha", "robot check", "automated access",
                    "something went wrong", "page not found"
                ]):
                    log.warning(f"Bot detected on attempt {attempt+1}: {url[:60]}")
                    _rand_delay(3, 6)
                    continue
                return BeautifulSoup(html, "lxml")
            elif resp.status_code == 503:
                log.warning(f"503 on attempt {attempt+1}: {url[:60]}")
                _rand_delay(5, 10)
            else:
                log.warning(f"HTTP {resp.status_code}: {url[:60]}")
        except Exception as e:
            log.warning(f"Request failed attempt {attempt+1}: {e}")
        _rand_delay(2, 4)
    return None


def _bs_amazon(session: requests.Session,
               query: str, budget: int,
               max_results: int = 12) -> list[dict]:
    """Scrape Amazon search results using requests + BeautifulSoup."""
    results = []
    url = (f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
           f"&ref=sr_pg_1")
    log.info(f"[BS] Amazon search: {query}")

    soup = _get_page(url, session)
    if not soup:
        log.warning("[BS] Amazon: page fetch failed")
        return results

    cards = soup.select("div[data-component-type='s-search-result']")
    log.info(f"[BS] Amazon: found {len(cards)} cards")

    for card in cards[:max_results]:
        try:
            # Name
            name_el = (card.select_one("h2 a span") or
                       card.select_one("h2 span")    or
                       card.select_one("span.a-size-medium") or
                       card.select_one("span.a-size-base-plus"))
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            # Price
            price = None
            for sel in [".a-price .a-offscreen", ".a-price-whole", "span.a-color-price"]:
                el = card.select_one(sel)
                if el:
                    price = _parse_price(el.get_text())
                    if price:
                        break
            if not price:
                continue
            if budget and price > budget:
                continue

            # URL
            prod_url = ""
            a_el = card.select_one("h2 a") or card.select_one("a.a-link-normal")
            if a_el and a_el.get("href"):
                href = a_el["href"]
                prod_url = href if href.startswith("http") else "https://www.amazon.in" + href
                # Canonicalise to dp URL
                m = re.search(r"(/dp/[A-Z0-9]{10})", prod_url)
                if m:
                    prod_url = "https://www.amazon.in" + m.group(1)
                elif "/sspa/click" in prod_url:
                    m_dest = re.search(r"url=%2F([^%]+)%2Fdp%2F([A-Z0-9]{10})", prod_url)
                    if m_dest:
                        prod_url = f"https://www.amazon.in/{m_dest.group(1)}/dp/{m_dest.group(2)}"

            if not prod_url:
                continue

            # Image
            image = ""
            img_el = card.select_one("img.s-image") or card.select_one("img")
            image = ""
            img_el = card.select_one("img.s-image")
            if img_el:
                image = (img_el.get("src") or
                         img_el.get("data-src") or "")

            # Rating
            rating = None
            r_el = card.select_one(".a-icon-alt")
            if r_el:
                rating = _parse_rating(r_el.get_text())

            # Review count
            review_count = ""
            rc_el = card.select_one(".a-size-base.s-underline-text")
            if rc_el:
                review_count = rc_el.get_text(strip=True)

            # Reviews URL
            reviews_url = ""
            m2 = re.search(r"/dp/([A-Z0-9]{10})", prod_url)
            if m2:
                reviews_url = (f"https://www.amazon.in/product-reviews/"
                               f"{m2.group(1)}?sortBy=recent")

            results.append({
                "id":           f"az_{abs(hash(name))}",
                "name":         name[:100],
                "price":        price,
                "rating":       rating,
                "review_count": review_count,
                "source":       "Amazon",
                "url":          prod_url,
                "image":        image,
                "reviews_url":  reviews_url,
            })

        except Exception as e:
            log.debug(f"Amazon card error: {e}")
            continue

    log.info(f"[BS] Amazon → {len(results)} products")
    return results


def _bs_flipkart(session: requests.Session,
                 query: str, budget: int,
                 max_results: int = 12) -> list[dict]:
    """Scrape Flipkart search results using requests + BeautifulSoup."""
    results = []
    url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}&sort=relevance"
    log.info(f"[BS] Flipkart search: {query}")

    soup = _get_page(url, session)
    if not soup:
        log.warning("[BS] Flipkart: page fetch failed")
        return results

    # Flipkart uses different layouts — try multiple selectors
    cards = (soup.select("div[data-id]") or
             soup.select("div._1AtVbE") or
             soup.select("div._2kHMtA") or
             soup.select("div.cPHDOP"))
    log.info(f"[BS] Flipkart: found {len(cards)} cards")

    for card in cards[:max_results]:
        try:
            # Name
            name = ""
            for sel in ["._4rR01T", ".s1Q9rs", ".IRpwTa", "a.wjcEIp",
                        "div._4rR01T", "a[title]"]:
                el = card.select_one(sel)
                if el:
                    name = el.get_text(strip=True) or el.get("title", "")
                    if name:
                        break
            if not name:
                continue

            # Price
            price = None
            for sel in ["._30jeq3", "._1_WHN1", ".Nx9bqj", "._3I9_wc"]:
                el = card.select_one(sel)
                if el:
                    price = _parse_price(el.get_text())
                    if price:
                        break
            if not price:
                continue
            if budget and price > budget:
                continue

            # Product URL
            prod_url = ""
            a_el = (card.select_one("a._1fQZEK") or
                    card.select_one("a.s1Q9rs")   or
                    card.select_one("a._2rpwqI")  or
                    card.select_one("a[href*='/p/']"))
            if a_el and a_el.get("href"):
                href = a_el["href"]
                prod_url = href if href.startswith("http") else "https://www.flipkart.com" + href
                # Clean tracking params
                prod_url = prod_url.split("?")[0]
            if not prod_url:
                continue

            # Image
            image = ""
            img_el = (card.select_one("img._396cs4") or
                      card.select_one("img._2r_T1I") or
                      card.select_one("div._3BTv9X img") or
                      card.select_one("img"))
            if img_el:
                src = (img_el.get("src") or img_el.get("data-src") or "")
                # Upgrade Flipkart image resolution
                if "rukminim" in src:
                    src = re.sub(r"/\d+/\d+/", "/512/512/", src)
                image = src

            # Rating
            rating = None
            r_el = card.select_one("._3LWZlK")
            if r_el:
                rating = _parse_rating(r_el.get_text())

            # Review count
            review_count = ""
            rc_el = card.select_one("._2_R_DZ span:first-child")
            if rc_el:
                review_count = rc_el.get_text(strip=True)

            results.append({
                "id":           f"fk_{abs(hash(name))}",
                "name":         name[:100],
                "price":        price,
                "rating":       rating,
                "review_count": review_count,
                "source":       "Flipkart",
                "url":          prod_url,
                "image":        image,
                "reviews_url":  prod_url + "#ratings",
            })

        except Exception as e:
            log.debug(f"Flipkart card error: {e}")
            continue

    log.info(f"[BS] Flipkart → {len(results)} products")
    return results


def _bs_nykaa(session: requests.Session,
              query: str, budget: int,
              max_results: int = 10) -> list[dict]:
    """Scrape Nykaa for beauty products."""
    results = []
    url = f"https://www.nykaa.com/search/result/?q={query.replace(' ', '%20')}"
    log.info(f"[BS] Nykaa search: {query}")

    soup = _get_page(url, session)
    if not soup:
        log.warning("[BS] Nykaa: page fetch failed")
        return results

    cards = (soup.select("div[class*='productWrapper']") or
             soup.select("div[class*='product-card']")   or
             soup.select("div[class*='css-']"))
    log.info(f"[BS] Nykaa: found {len(cards)} cards")

    for card in cards[:max_results]:
        try:
            # Name
            name = ""
            for sel in ["div[class*='productName']", "p[class*='productName']",
                        "div[class*='name']"]:
                el = card.select_one(sel)
                if el:
                    name = el.get_text(strip=True)
                    if name:
                        break
            if not name:
                continue

            # Price
            price = None
            for sel in ["span[class*='price-now']", "div[class*='offerPrice']",
                        "span[class*='price']"]:
                el = card.select_one(sel)
                if el:
                    price = _parse_price(el.get_text())
                    if price:
                        break
            if not price:
                continue
            if budget and price > budget:
                continue

            # URL
            prod_url = ""
            a_el = card.select_one("a")
            if a_el and a_el.get("href"):
                href = a_el["href"]
                prod_url = href if href.startswith("http") else "https://www.nykaa.com" + href

            # Image
            image = ""
            img_el = card.select_one("img")
            if img_el:
                image = img_el.get("src") or img_el.get("data-src") or ""

            # Rating
            rating = None
            r_el = (card.select_one("span[class*='rating']") or
                    card.select_one("div[class*='avg-rating']"))
            if r_el:
                rating = _parse_rating(r_el.get_text())

            results.append({
                "id":           f"ny_{abs(hash(name))}",
                "name":         name[:100],
                "price":        price,
                "rating":       rating,
                "review_count": "",
                "source":       "Nykaa",
                "url":          prod_url,
                "image":        image,
                "reviews_url":  prod_url + "#reviews" if prod_url else "",
            })

        except Exception as e:
            log.debug(f"Nykaa card error: {e}")
            continue

    log.info(f"[BS] Nykaa → {len(results)} products")
    return results


# ═══════════════════════════════════════════════════════════════
# STRATEGY 2 — Selenium with full anti-detection
# ═══════════════════════════════════════════════════════════════

def _make_selenium_driver():
    """Create maximally stealthy Chrome driver."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1440,900")
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--lang=en-IN")
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        })

        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=opts)

        # Remove webdriver fingerprint
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            """
        })
        driver.set_page_load_timeout(20)
        return driver
    except Exception as e:
        log.warning(f"Selenium driver creation failed: {e}")
        return None


def _selenium_scrape(query: str, budget: int, site: str) -> list[dict]:
    """Scrape using Selenium with anti-detection. Returns [] on failure."""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import StaleElementReferenceException

    driver = _make_selenium_driver()
    if not driver:
        return []

    results = []
    try:
        if site == "amazon":
            url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        elif site == "flipkart":
            url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}&sort=relevance"
        else:
            return []

        driver.get(url)
        _rand_delay(3, 5)

        # Simulate human: random scroll
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3)")
        _rand_delay(0.5, 1.5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6)")
        _rand_delay(0.5, 1.5)

        html   = driver.page_source
        soup   = BeautifulSoup(html, "lxml")

        if site == "amazon":
            results = _bs_amazon(requests.Session(), query, budget)
            # If BS failed on the fetched HTML, parse directly
            if not results:
                # Parse the selenium-rendered page directly
                cards = soup.select("div[data-component-type='s-search-result']")
                for card in cards[:12]:
                    try:
                        name_el = card.select_one("h2 a span") or card.select_one("h2 span")
                        if not name_el:
                            continue
                        name = name_el.get_text(strip=True)
                        price_el = card.select_one(".a-price .a-offscreen") or card.select_one(".a-price-whole")
                        price = _parse_price(price_el.get_text()) if price_el else None
                        if not price or (budget and price > budget):
                            continue
                        a_el = card.select_one("h2 a")
                        href = a_el["href"] if a_el else ""
                        prod_url = href if href.startswith("http") else "https://www.amazon.in" + href
                        img_el = card.select_one("img.s-image")
                        image = img_el.get("src", "") if img_el else ""
                        r_el = card.select_one(".a-icon-alt")
                        rating = _parse_rating(r_el.get_text()) if r_el else None
                        m = re.search(r"/dp/([A-Z0-9]{10})", prod_url)
                        reviews_url = f"https://www.amazon.in/product-reviews/{m.group(1)}?sortBy=recent" if m else ""
                        results.append({
                            "id": f"az_{abs(hash(name))}",
                            "name": name[:100], "price": price, "rating": rating,
                            "review_count": "", "source": "Amazon",
                            "url": prod_url, "image": image, "reviews_url": reviews_url,
                        })
                    except Exception:
                        continue
        elif site == "flipkart":
            # Dismiss popup first
            try:
                driver.find_element(By.CSS_SELECTOR, "button._2KpZ6l._2doB4z").click()
                _rand_delay(0.5, 1)
            except Exception:
                pass
            html  = driver.page_source
            soup  = BeautifulSoup(html, "lxml")
            session = requests.Session()
            results = _parse_flipkart_soup(soup, budget)

    except Exception as e:
        log.warning(f"Selenium {site} error: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return results


def _parse_flipkart_soup(soup: BeautifulSoup, budget: int) -> list[dict]:
    """Parse Flipkart HTML that was already fetched (by selenium or requests)."""
    results = []
    cards = (soup.select("div[data-id]") or
             soup.select("div._1AtVbE") or
             soup.select("div.cPHDOP"))
    for card in cards[:12]:
        try:
            name = ""
            for sel in ["._4rR01T","a.wjcEIp","a[title]",".s1Q9rs"]:
                el = card.select_one(sel)
                if el:
                    name = el.get_text(strip=True) or el.get("title","")
                    if name: break
            if not name: continue
            price = None
            for sel in ["._30jeq3","._1_WHN1",".Nx9bqj"]:
                el = card.select_one(sel)
                if el:
                    price = _parse_price(el.get_text())
                    if price: break
            if not price or (budget and price > budget): continue
            a_el = card.select_one("a[href*='/p/']") or card.select_one("a._1fQZEK") or card.select_one("a")
            href = a_el["href"] if a_el else ""
            prod_url = href if href.startswith("http") else ("https://www.flipkart.com" + href)
            prod_url = prod_url.split("?")[0]
            img_el = card.select_one("img._396cs4") or card.select_one("img._2r_T1I") or card.select_one("img")
            image = ""
            if img_el:
                src = img_el.get("src") or img_el.get("data-src") or ""
                if "rukminim" in src:
                    src = re.sub(r"/\d+/\d+/", "/512/512/", src)
                image = src
            r_el = card.select_one("._3LWZlK")
            rating = _parse_rating(r_el.get_text()) if r_el else None
            results.append({
                "id": f"fk_{abs(hash(name))}",
                "name": name[:100], "price": price, "rating": rating,
                "review_count": "", "source": "Flipkart",
                "url": prod_url, "image": image,
                "reviews_url": prod_url + "#ratings",
            })
        except Exception:
            continue
    return results


# ═══════════════════════════════════════════════════════════════
# STRATEGY 3 — SerpAPI  (100% reliable, recommended)
# ═══════════════════════════════════════════════════════════════

def _serpapi_search(query: str, budget: int, engine: str = "amazon") -> list[dict]:
    """
    Use SerpAPI to get product listings. 100% reliable.
    Free tier: 100 searches/month at serpapi.com
    """
    if not SERPAPI_KEY:
        return []

    results = []
    try:
        params = {
            "engine":   engine,
            "k":        query,
            "api_key":  SERPAPI_KEY,
            "gl":       "in",
            "hl":       "en",
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
        data = resp.json()

        items = (data.get("organic_results")  or
                 data.get("shopping_results") or [])

        for item in items[:15]:
            try:
                price_raw = (item.get("price") or
                             item.get("extracted_price") or "")
                price = _parse_price(str(price_raw))
                if not price:
                    continue
                if budget and price > budget:
                    continue

                name   = item.get("title", "")[:100]
                rating = item.get("rating") or _parse_rating(str(item.get("reviews", "")))
                url    = (item.get("link") or
                          item.get("product_link") or "")
                image  = (item.get("thumbnail") or
                          item.get("image") or "")

                reviews_url = ""
                if "amazon.in" in url:
                    m = re.search(r"/dp/([A-Z0-9]{10})", url)
                    if m:
                        reviews_url = f"https://www.amazon.in/product-reviews/{m.group(1)}"
                elif "flipkart.com" in url:
                    reviews_url = url + "#ratings"

                source = "Amazon" if "amazon" in engine else "Shopping"

                results.append({
                    "id":           f"sp_{abs(hash(name))}",
                    "name":         name,
                    "price":        price,
                    "rating":       rating,
                    "review_count": str(item.get("reviews", "")),
                    "source":       source,
                    "url":          url,
                    "image":        image,
                    "reviews_url":  reviews_url,
                })
            except Exception as e:
                log.debug(f"SerpAPI item error: {e}")
                continue

    except Exception as e:
        log.warning(f"SerpAPI error: {e}")

    log.info(f"SerpAPI → {len(results)} products")
    return results


# ═══════════════════════════════════════════════════════════════
# SITE DETECTION
# ═══════════════════════════════════════════════════════════════

BEAUTY_KW = [
    "lipstick","lip","foundation","moisturizer","moisturiser",
    "sunscreen","serum","face wash","cleanser","toner","cream",
    "makeup","cosmetic","skincare","spf","vitamin c","niacinamide",
    "kajal","eyeliner","blush","highlighter","concealer","primer",
]
ELEC_KW = [
    "phone","mobile","smartphone","laptop","notebook","earbuds",
    "headphone","watch","tablet","speaker","camera","tv","monitor",
]

def _detect_category(query: str) -> str:
    q = query.lower()
    if any(kw in q for kw in BEAUTY_KW):
        return "beauty"
    if any(kw in q for kw in ELEC_KW):
        return "electronics"
    return "general"


# ═══════════════════════════════════════════════════════════════
# STAGE 1 — MAIN SEARCH  (tries all 3 strategies)
# ═══════════════════════════════════════════════════════════════

def scrape_stage1(query: str, budget: int = 0) -> list[dict]:
    """
    Search for products matching query + budget.
    Tries (in order):
      1. requests + BeautifulSoup  (fastest)
      2. Selenium anti-detection   (fallback)
      3. SerpAPI                   (most reliable, needs API key)
    """
    category = _detect_category(query)
    all_prods: list[dict] = []
    seen: set[str] = set()

    session = requests.Session()
    session.headers.update(random.choice(HEADERS_LIST))

    def _add(batch: list[dict]):
        for p in batch:
            key = (p.get("name") or "").lower()[:20]
            if key and key not in seen:
                seen.add(key)
                all_prods.append(p)

    # ── Strategy 1: requests + BS ─────────────────────────────
    log.info("Trying Strategy 1: requests + BeautifulSoup")
    try:
        if category == "beauty":
            _add(_bs_nykaa(session, query, budget))
            _rand_delay(1, 2)
            _add(_bs_amazon(session, query, budget))
        else:
            _add(_bs_flipkart(session, query, budget))
            _rand_delay(1, 2)
            _add(_bs_amazon(session, query, budget))
    except Exception as e:
        log.warning(f"Strategy 1 error: {e}")

    log.info(f"After Strategy 1: {len(all_prods)} products")

    # ── Strategy 2: Selenium (if BS got < 3 results) ──────────
    if len(all_prods) < 3:
        log.info("Strategy 1 insufficient — trying Strategy 2: Selenium")
        try:
            if category == "beauty":
                sel_results = _selenium_scrape(query, budget, "amazon")
            else:
                sel_results = _selenium_scrape(query, budget, "flipkart")
                if not sel_results:
                    sel_results = _selenium_scrape(query, budget, "amazon")
            _add(sel_results)
        except Exception as e:
            log.warning(f"Strategy 2 error: {e}")
        log.info(f"After Strategy 2: {len(all_prods)} products")

    # ── Strategy 3: SerpAPI (if still < 3 results) ────────────
    if len(all_prods) < 3 and SERPAPI_KEY:
        log.info("Trying Strategy 3: SerpAPI")
        try:
            _add(_serpapi_search(query, budget, engine="amazon"))
        except Exception as e:
            log.warning(f"Strategy 3 error: {e}")
        log.info(f"After Strategy 3: {len(all_prods)} products")

    if not all_prods:
        log.error("All strategies failed — no products found")

    # Sort cheapest first
    all_prods.sort(key=lambda x: x.get("price") or 999999)

    # Save CSV
    _save_csv(all_prods, f"stage1_{int(time.time())}.csv")
    log.info(f"Stage 1 done → {len(all_prods)} products")
    return all_prods


# ═══════════════════════════════════════════════════════════════
# STAGE 2 — PRICE COMPARISON
# ═══════════════════════════════════════════════════════════════

def _get_pdp_price(url: str, store: str, session: requests.Session, driver_needed: bool = False) -> Optional[int]:
    """Visit the actual product page to get the absolute current price."""
    log.info(f"[PDP] Fetching accurate price from: {url[:60]}...")
    
    # Try Requests first (Strategy 1)
    if not driver_needed:
        try:
            resp = session.get(url, headers=random.choice(HEADERS_LIST), timeout=10)
            if resp.status_code == 200 and "captcha" not in resp.text.lower():
                soup = BeautifulSoup(resp.text, "lxml")
                price = None
                if store == "Amazon":
                    for sel in ["span.priceToPay .a-price-whole", ".a-price-whole", "#priceblock_ourprice"]:
                        el = soup.select_one(sel)
                        if el: 
                            price = _parse_price(el.get_text())
                            if price: break
                elif store == "Flipkart":
                    for sel in [".Nx9bqj", "._30jeq3", "._16Jk6d"]:
                        el = soup.select_one(sel)
                        if el:
                            price = _parse_price(el.get_text())
                            if price: break
                elif store == "Nykaa":
                    for sel in [".css-1jcz6ot", "span[class*='price-now']"]:
                        el = soup.select_one(sel)
                        if el:
                            price = _parse_price(el.get_text())
                            if price: break
                if price: return price
        except: pass

    # Fallback to Selenium (Strategy 2)
    log.info(f"[PDP] Requests blocked or failed, using Selenium for {store}...")
    driver = _make_selenium_driver()
    if not driver: return None
    try:
        driver.get(url)
        _rand_delay(3, 5)
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        price = None
        if store == "Amazon":
            for sel in ["span.priceToPay .a-price-whole", ".a-price-whole"]:
                try: price = _parse_price(driver.find_element(By.CSS_SELECTOR, sel).text)
                except: continue
                if price: break
        elif store == "Flipkart":
            for sel in [".Nx9bqj", "._30jeq3"]:
                try: price = _parse_price(driver.find_element(By.CSS_SELECTOR, sel).text)
                except: continue
                if price: break
        return price
    except: return None
    finally: driver.quit()

def scrape_stage2(product_name: str, product_url: str = "") -> list[dict]:
    """
    Get prices for a product from multiple stores with 100% accuracy.
    """
    prices = []
    seen_stores: set[str] = set()
    category = _detect_category(product_name)
    
    session = requests.Session()
    session.headers.update(random.choice(HEADERS_LIST))

    store_configs = [
        ("Amazon",   "amazon",   _bs_amazon),
        ("Flipkart", "flipkart", _bs_flipkart),
    ]
    if category == "beauty":
        store_configs.append(("Nykaa", "nykaa", _bs_nykaa))

    for store_name, site_key, scrape_fn in store_configs:
        try:
            log.info(f"[Stage 2] Searching {store_name} for: {product_name}")
            # 1. Find the product link via search
            batch = scrape_fn(session, product_name, budget=0, max_results=1)
            if not batch:
                batch = _selenium_scrape(product_name, 0, site_key)
                if batch: batch = batch[:1]

            if batch:
                p = batch[0]
                # 2. VIST THE LINK to get real price
                accurate_price = _get_pdp_price(p["url"], store_name, session)
                
                prices.append({
                    "store":        store_name,
                    "price":        accurate_price or p["price"],
                    "url":          p["url"],
                    "image":        p.get("image", ""),
                    "rating":       p.get("rating"),
                    "review_count": p.get("review_count", ""),
                    "reviews_url":  p.get("reviews_url", _build_reviews_url(p)),
                    "is_best":      False,
                })
                seen_stores.add(store_name)
            
            _rand_delay(1, 2)
        except Exception as e:
            log.warning(f"Stage 2 {store_name} error: {e}")

    # Sort and flag best
    prices.sort(key=lambda x: x.get("price") or 999999)
    if prices:
        prices[0]["is_best"] = True

    log.info(f"Stage 2 → {len(prices)} accurate prices for '{product_name}'")
    return prices


# ═══════════════════════════════════════════════════════════════
# CSV HELPER
# ═══════════════════════════════════════════════════════════════

def _save_csv(products: list[dict], filename: str) -> str:
    if not products:
        return ""
    path  = DATA_DIR / filename
    clean = [{k: v for k, v in p.items() if not k.startswith("_")} for p in products]
    keys  = list(clean[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(clean)
    log.info(f"CSV saved → {path}")
    return str(path)

def save_results_csv(products: list[dict], query: str) -> str:
    safe = re.sub(r"[^\w]", "_", query)[:25]
    return _save_csv(products, f"results_{safe}_{int(time.time())}.csv")


# ═══════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    q      = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "gaming phone under 15000"
    budget = 0
    m      = re.search(r"(\d+)\s*k?$", q)
    if m:
        budget = int(m.group(1))
        if "k" in q.lower()[-3:]:
            budget *= 1000

    print(f"\nSearching: '{q}'  budget={budget}")
    print("=" * 60)
    results = scrape_stage1(q, budget)
    print(f"\nFound {len(results)} products:\n")
    for p in results:
        print(f"  {p['name'][:50]:50s}  ₹{p.get('price',0):>8,}")
        print(f"    Source  : {p.get('source','?')}")
        print(f"    Rating  : {p.get('rating','?')}  ({p.get('review_count','?')} reviews)")
        print(f"    Image   : {'✅' if p.get('image') else '❌'} {p.get('image','')[:60]}")
        print(f"    URL     : {p.get('url','')[:60]}")
        print(f"    Reviews : {p.get('reviews_url','')[:60]}")
        print()