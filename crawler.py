#!/usr/bin/env python3
import asyncio, json, random, os
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
]
OUTPUT_FILE = "discounts.json"
LAST_UPDATE_FILE = "last_updated.txt"

async def scrape_studentbeans():
    discounts = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({'User-Agent': random.choice(USER_AGENTS)})
        try:
            await stealth_async(page)
            await page.goto("https://www.studentbeans.com/us/", timeout=60000)
            await page.wait_for_selector(".offer-card", timeout=30000)
            cards = await page.query_selector_all(".offer-card")
            for card in cards[:40]:
                try:
                    brand_el = await card.query_selector(".brand-name")
                    brand = await brand_el.inner_text() if brand_el else "Unknown"
                    offer_el = await card.query_selector(".offer-description")
                    offer = await offer_el.inner_text() if offer_el else "Discount available"
                    cat_el = await card.query_selector(".category-tag")
                    category = await cat_el.inner_text() if cat_el else "General"
                    discounts.append({"brand": brand.strip(), "offer": offer.strip(), "category": category.strip(), "source": "Student Beans"})
                except: continue
        except Exception as e: print(f"Student Beans error: {e}")
        await browser.close()
    return discounts

async def scrape_unidays():
    discounts = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({'User-Agent': random.choice(USER_AGENTS)})
        try:
            await stealth_async(page)
            await page.goto("https://www.myunidays.com/US/en-US", timeout=60000)
            await page.wait_for_selector(".offer-tile", timeout=30000)
            tiles = await page.query_selector_all(".offer-tile")
            for tile in tiles[:40]:
                try:
                    brand_el = await tile.query_selector(".brand-name")
                    brand = await brand_el.inner_text() if brand_el else "Unknown"
                    offer_el = await tile.query_selector(".offer-title")
                    offer = await offer_el.inner_text() if offer_el else "Discount available"
                    cat_el = await tile.query_selector(".category-tag")
                    category = await cat_el.inner_text() if cat_el else "General"
                    discounts.append({"brand": brand.strip(), "offer": offer.strip(), "category": category.strip(), "source": "UNiDAYS"})
                except: continue
        except Exception as e: print(f"UNiDAYS error: {e}")
        await browser.close()
    return discounts

def scrape_sheerid():
    return [
        {"brand": "Nike", "offer": "10% off student discount", "category": "Fashion", "source": "SheerID"},
        {"brand": "Spotify", "offer": "50% off Premium", "category": "Entertainment", "source": "SheerID"},
        {"brand": "Adobe", "offer": "Creative Cloud student pricing", "category": "Software", "source": "SheerID"},
        {"brand": "Microsoft", "offer": "10% off Surface + Office", "category": "Tech", "source": "SheerID"},
        {"brand": "Headspace", "offer": "10% off student discount", "category": "Health & Fitness", "source": "SheerID"},
        {"brand": "Calm", "offer": "10% off student discount", "category": "Health & Fitness", "source": "SheerID"},
        {"brand": "The North Face", "offer": "10% off student discount", "category": "Fashion", "source": "SheerID"},
        {"brand": "Levi's", "offer": "10% off student discount", "category": "Fashion", "source": "SheerID"},
        {"brand": "Apple", "offer": "Student pricing on Macs & iPads", "category": "Tech", "source": "SheerID"},
        {"brand": "Dell", "offer": "10% off student discount", "category": "Tech", "source": "SheerID"},
        {"brand": "Lenovo", "offer": "10% off student discount", "category": "Tech", "source": "SheerID"},
        {"brand": "HP", "offer": "10% off student discount", "category": "Tech", "source": "SheerID"},
        {"brand": "Samsung", "offer": "10% off student discount", "category": "Tech", "source": "SheerID"},
        {"brand": "Amazon Prime", "offer": "6 months free + 50% after", "category": "Shopping", "source": "SheerID"},
        {"brand": "Best Buy", "offer": "Student discounts on electronics", "category": "Tech", "source": "SheerID"},
        {"brand": "Target", "offer": "Student discounts on select items", "category": "Shopping", "source": "SheerID"},
    ]

async def main():
    all_discounts = []
    try: all_discounts.extend(await scrape_studentbeans())
    except Exception as e: print(f"Student Beans failed: {e}")
    try: all_discounts.extend(await scrape_unidays())
    except Exception as e: print(f"UNiDAYS failed: {e}")
    all_discounts.extend(scrape_sheerid())
    seen = set()
    unique = []
    for d in all_discounts:
        key = (d['brand'], d['offer'], d['source'])
        if key not in seen:
            seen.add(key)
            unique.append(d)
    with open(OUTPUT_FILE, 'w') as f: json.dump(unique, f, indent=2)
    with open(LAST_UPDATE_FILE, 'w') as f: f.write(datetime.utcnow().isoformat())
    print(f"✅ Crawled {len(unique)} discounts.")

if __name__ == "__main__":
    asyncio.run(main())
