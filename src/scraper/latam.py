import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import urllib.parse

def extract_price(text: str):
    matches = re.findall(r'R\$\s*([\d\.,]+)', text)
    if matches:
        # Pega a primeira ocorrência, remove pontos e troca virgula por ponto
        val = matches[0].replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None
    return None

def scrape_latam(origin: str, destination: str, target_date: datetime) -> dict:
    """
    Usa o Playwright para raspar a página oficial da LATAM para uma data específica.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    outbound_date = urllib.parse.quote(f"{date_str}T12:00:00.000Z")
    
    url = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origin}&inbound=null&outbound={outbound_date}&destination={destination}&adt=1&chd=0&inf=0&trip=OW&cabin=Economy&redemption=false"
    
    print(f"[LATAM] [{origin}->{destination}] Acessando LATAM para o dia {date_str}...")
    
    result = {
        "source": "LATAM Oficial",
        "origin": origin,
        "destination": destination,
        "date": date_str,
        "time": "N/A",
        "price": None,
        "currency": "BRL",
        "airline": "LATAM",
        "link": url
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            page.goto(url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(8000) # O site da LATAM demora a montar os voos
            
            # O LATAM geralmente coloca as opções de voo em <li>
            elements = page.query_selector_all('li')
            
            valid_flights = []
            for el in elements:
                try:
                    text = el.inner_text()
                    if text and 'R$' in text and len(text) < 400 and re.search(r'\d{1,2}:\d{2}', text):
                        p_val = extract_price(text)
                        if p_val and p_val > 50:
                            valid_flights.append((p_val, text))
                except:
                    continue
            
            browser.close()

            if valid_flights:
                lowest_price, best_text = min(valid_flights, key=lambda x: x[0])
                
                # Extrai o horário
                time_match = re.search(r'\d{1,2}:\d{2}', best_text)
                extracted_time = time_match.group(0) if time_match else "N/A"
                
                result["price"] = lowest_price
                result["time"] = extracted_time
                
                return result
            else:
                return None
                
    except Exception as e:
        print(f"-> [LATAM] Erro: {str(e).encode('ascii', 'ignore').decode('ascii')}")
        return None
