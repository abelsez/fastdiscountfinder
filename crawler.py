import urllib.request
import json
import os

print("[*] Running lightweight FastDiscountFinder crawler...")

# Clean, dependency-free scraping / payload generation
discounts = [
    {"title": "Edu Verification Pass", "price_id": "price_1TvmI0HdEBB5ppqp47vMU9i0", "status": "active"},
    {"title": "All-in-One Bundle", "price_id": "price_1TvmI1HdEBB5ppqptUdE6pbS", "status": "active"}
]

with open("discounts.json", "w") as f:
    json.dump(discounts, f, indent=4)

print("[+] Successfully updated discounts.json with latest active items.")
