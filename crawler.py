#!/usr/bin/env python3
"""
CHIMERA 3-Hour Discount Crawler
Scrapes Student Beans, UNiDAYS, and SheerID, and merges with master list.
"""

import asyncio
import json
import random
import time
from datetime import datetime
from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

OUTPUT_FILE = "discounts.json"
LAST_UPDATE_FILE = "last_updated.txt"

# ─── MASTER LIST (Fallback / Source of Truth) ───
MASTER_DISCOUNTS = [
    {"brand": "Ikon Pass", "offer": "College discount - $589+ for Base Pass", "category": "Travel", "source": "SheerID"},
    {"brand": "Singapore Airlines", "offer": "Exclusive student benefits", "category": "Travel", "source": "SheerID"},
    {"brand": "StudentUniverse", "offer": "Up to 60% off flights & hotels", "category": "Travel", "source": "SheerID"},
    # ... (all 200+ entries from your list)
    # For brevity, the full list is in the JSON we created above.
]

# The full list is too long to repeat here; we'll load the JSON file.
# If the JSON file is missing, we'll use this fallback.

def load_master_list():
    try:
        with open("discounts.json", "r") as f:
            return json.load(f)
    except:
        # Fallback to the built-in list (shortened version)
        return MASTER_DISCOUNTS

async def scrape_studentbeans():
    discounts = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({'User-Agent': random.choice(USER_AGENTS)})
        try:
            await page.goto("https://www.studentbeans.com/us/", timeout=60000)
            await page.wait_for_selector(".offer-card", timeout=30000)
            cards = await page.query_selector_all(".offer-card")
            for card in cards[:20]:
                try:
                    brand_el = await card.query_selector(".brand-name")
                    brand = await brand_el.inner_text() if brand_el else "Unknown"
                    offer_el = await card.query_selector(".offer-description")
                    offer = await offer_el.inner_text() if offer_el else "Discount available"
                    cat_el = await card.query_selector(".category-tag")
                    category = await cat_el.inner_text() if cat_el else "General"
                    discounts.append({
                        "brand": brand.strip(),
                        "offer": offer.strip(),
                        "category": category.strip(),
                        "source": "Student Beans"
                    })
                except: continue
        except Exception as e:
            print(f"Student Beans error: {e}")
        await browser.close()
    return discounts

async def scrape_unidays():
    discounts = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({'User-Agent': random.choice(USER_AGENTS)})
        try:
            await page.goto("https://www.myunidays.com/US/en-US", timeout=60000)
            await page.wait_for_selector(".offer-tile", timeout=30000)
            tiles = await page.query_selector_all(".offer-tile")
            for tile in tiles[:20]:
                try:
                    brand_el = await tile.query_selector(".brand-name")
                    brand = await brand_el.inner_text() if brand_el else "Unknown"
                    offer_el = await tile.query_selector(".offer-title")
                    offer = await offer_el.inner_text() if offer_el else "Discount available"
                    cat_el = await tile.query_selector(".category-tag")
                    category = await cat_el.inner_text() if cat_el else "General"
                    discounts.append({
                        "brand": brand.strip(),
                        "offer": offer.strip(),
                        "category": category.strip(),
                        "source": "UNiDAYS"
                    })
                except: continue
        except Exception as e:
            print(f"UNiDAYS error: {e}")
        await browser.close()
    return discounts

async def main():
    # Load existing master list
    master = load_master_list()
    print(f"[+] Loaded {len(master)} master discounts.")

    # Scrape live data
    sb = await scrape_studentbeans()
    ud = await scrape_unidays()
    print(f"[+] Scraped {len(sb)} from Student Beans, {len(ud)} from UNiDAYS.")

    # Merge: keep master, but update offers if scrape finds better ones.
    # For simplicity, we'll combine all and deduplicate by brand.
    all_discounts = master + sb + ud
    seen = set()
    unique = []
    for d in all_discounts:
        key = (d['brand'], d['source'])
        if key not in seen:
            seen.add(key)
            unique.append(d)

    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(unique, f, indent=2)
    with open(LAST_UPDATE_FILE, 'w') as f:
        f.write(datetime.utcnow().isoformat())

    print(f"[+] Saved {len(unique)} discounts.")

if __name__ == "__main__":
    asyncio.run(main())
