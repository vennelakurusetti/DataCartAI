
import sys
import os
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path("backend").absolute()))

from app.scraper.selenium_scraper import make_driver, _amazon_search, _flipkart_search, _nykaa_search
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_scraper(query="laptop"):
    print(f"Testing scraper with query: {query}")
    
    # Try with visible browser to see what's happening
    opts = Options()
    opts.add_argument("--headless=new") 
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    })
    
    try:
        print("\n--- Testing Amazon ---")
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        driver.get(url)
        time.sleep(5)
        
        cards = driver.find_elements("css selector", "div[data-component-type='s-search-result']")
        print(f"Amazon cards found: {len(cards)}")
        if len(cards) == 0:
            driver.save_screenshot("amazon_fail.png")
            with open("amazon_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Amazon failed, screenshot and source saved.")
        else:
            print(f"Sample card text: {cards[0].text[:100]}...")

        print("\n--- Testing Nykaa ---")
        url = f"https://www.nykaa.com/search/result/?q={query.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        cards = driver.find_elements("css selector", "div[class*='productWrapper'], div[class*='product-card']")
        print(f"Nykaa cards found: {len(cards)}")
        if len(cards) == 0:
            driver.save_screenshot("nykaa_fail.png")
            print("Nykaa failed, screenshot saved.")
        else:
            print(f"Sample card text: {cards[0].text[:100]}...")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_scraper("sunscreen")
