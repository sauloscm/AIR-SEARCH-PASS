import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.google_flights import scrape_flights

dates_to_check = [
    ("IMP", "REC", datetime(2026, 7, 5)),
    ("IMP", "REC", datetime(2026, 7, 16)),
    ("REC", "IMP", datetime(2026, 7, 3)),
    ("REC", "IMP", datetime(2026, 7, 10)),
]

def main():
    print("Iniciando verificação de incongruências nas datas mais caras...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for orig, dest, date in dates_to_check:
            print(f"\nVerificando {orig}->{dest} em {date.strftime('%Y-%m-%d')}...")
            result = scrape_flights(page, orig, dest, date)
            print(f"Resultado final retornado: {result}")
            time.sleep(3)

        browser.close()

if __name__ == "__main__":
    main()
