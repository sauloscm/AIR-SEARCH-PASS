import time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

with sync_playwright() as p:
    print("Iniciando browser...")
    context = p.chromium.launch_persistent_context(
        user_data_dir="./test_profile",
        headless=True,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    print("Aplicando stealth...")
    page = context.pages[0] if context.pages else context.new_page()
    Stealth().apply_stealth_sync(page)
    
    print("Navegando para google.com...")
    page.goto("https://www.google.com/travel/flights", timeout=15000)
    print("Página carregada!")
    
    context.close()
