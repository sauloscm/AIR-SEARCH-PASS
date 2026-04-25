import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

def extract_price(text: str):
    matches = re.findall(r'R\$\s*([\d\.,]+)', text)
    if matches:
        val = matches[0].replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None
    return None

def scrape_azul(origin: str, destination: str, target_date: datetime) -> dict:
    """
    Tenta raspar o site da Azul. Como a Azul não tem URL direta pública e possui o Akamai, 
    é um scraper muito sensível a bloqueios. 
    Tentaremos acessar uma URL estruturada que ocasionalmente funciona como Deep Link.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    
    # Rotação de URL profunda comum em sistemas da Azul
    url = f"https://www.voeazul.com.br/br/pt/home/selecao-voo?c=BRL&d={destination}&dt={date_str}&o={origin}&p=1&ps=1"
    
    print(f"[AZUL] [{origin}->{destination}] Acessando AZUL para o dia {date_str}...")
    
    result = {
        "source": "AZUL Oficial",
        "origin": origin,
        "destination": destination,
        "date": date_str,
        "time": "N/A",
        "price": None,
        "currency": "BRL",
        "airline": "Azul",
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
            
            # Navega e aguarda bastante, Azul carrega o painel de voos via JS
            page.goto(url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(10000)
            
            elements = page.query_selector_all('div')
            
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
                
                time_match = re.search(r'\d{1,2}:\d{2}', best_text)
                extracted_time = time_match.group(0) if time_match else "N/A"
                
                result["price"] = lowest_price
                result["time"] = extracted_time
                
                return result
            else:
                return None
                
    except Exception as e:
        print(f"-> [AZUL] Erro: {str(e).encode('ascii', 'ignore').decode('ascii')}")
        return None
