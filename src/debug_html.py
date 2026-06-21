import time
from playwright.sync_api import sync_playwright

url = "https://www.google.com/travel/flights?q=Flights%20to%20IMP%20from%20REC%20on%202026-07-30%20oneway"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded")
    
    # Accept cookies
    try:
        page.locator('button:has-text("Aceitar tudo"), button:has-text("Accept all")').click(timeout=3000)
    except:
        pass

    page.wait_for_selector('text="R$"', timeout=15000)
    
    # Scroll down to load all
    for _ in range(5):
        page.keyboard.press('PageDown')
        time.sleep(0.3)
        
    print("--- DUMPING LOCATORS ---")
    
    # Dump li and listitems
    elements = page.locator('li, div[role="listitem"]').all()
    print(f"Encontrou {len(elements)} elementos li/listitem.")
    for i, el in enumerate(elements[:10]):
        text = el.inner_text().replace('\n', ' | ')
        print(f"[{i}] {text[:200]}")
        
    print("\n--- BUSCANDO PELO AZUL 22:35 ---")
    azul = page.locator('text=/22:35/').all()
    print(f"Encontrou {len(azul)} elementos com 22:35.")
    for el in azul:
        print(el.evaluate("el => el.tagName + ' ' + el.className + ' ' + el.getAttribute('role')"))
        
    browser.close()
