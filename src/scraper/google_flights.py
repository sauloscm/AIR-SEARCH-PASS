import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

def extract_price(text: str):
    """
    Tenta extrair o valor numérico de um texto contendo R$.
    Ex: "R$ 1.250" -> 1250.0
    """
    matches = re.findall(r'R\$\s*([\d\.]+)', text)
    if matches:
        # Pega a primeira ocorrência, remove os pontos de milhar e converte
        val = matches[0].replace('.', '')
        try:
            return float(val)
        except ValueError:
            return None
    return None

def scrape_flights(origin: str, destination: str, target_date: datetime) -> dict:
    """
    Usa o Playwright para raspar a página do Google Flights para uma data específica.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{date_str}%20oneway"
    
    print(f"[{origin}->{destination}] Acessando Google Flights para o dia {date_str}...")
    
    result = {
        "source": "Google Flights (Scraper)",
        "origin": origin,
        "destination": destination,
        "date": date_str,
        "time": "N/A",  # Difícil raspar a hora com 100% precisão sem quebrar o HTML, vamos focar no menor preço do dia
        "price": None,
        "currency": "BRL",
        "airline": "Múltiplas/Google",
        "link": url
    }

    try:
        with sync_playwright() as p:
            # Lança o navegador Chromium (invisível por padrão, headless=True)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Timeout longo pois o Google Flights pode demorar para carregar e renderizar o JS
            page.goto(url, timeout=60000, wait_until="networkidle")
            
            # Espera uns segundos a mais pro React/JS do Google processar os voos na tela
            page.wait_for_timeout(5000) 

            # Uma forma robusta de achar os cards de voos é procurar elementos <li> ou <div>
            # que contenham um preço "R$" e um horário "HH:MM", mas não o texto da página inteira.
            elements = page.query_selector_all('li')
            if not elements:
                elements = page.query_selector_all('div[role="listitem"]')
            if not elements:
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
                # Pega a tupla com o menor preço
                lowest_price, best_text = min(valid_flights, key=lambda x: x[0])
                
                # Tenta extrair o horário
                time_match = re.search(r'\d{1,2}:\d{2}\s*(–|-|a)\s*\d{1,2}:\d{2}', best_text)
                extracted_time = time_match.group(0) if time_match else "N/A"
                if extracted_time == "N/A":
                    # Tenta só pegar o primeiro horário de partida
                    t_match = re.search(r'\d{1,2}:\d{2}', best_text)
                    if t_match: extracted_time = t_match.group(0)
                
                # Tenta achar a companhia aérea
                airline = "Múltiplas/Google"
                if "Azul" in best_text: airline = "Azul"
                elif "GOL" in best_text or "Gol" in best_text: airline = "GOL"
                elif "LATAM" in best_text or "Latam" in best_text: airline = "LATAM"
                elif "Voepass" in best_text or "Passaredo" in best_text: airline = "Voepass"
                
                result["price"] = lowest_price
                result["time"] = extracted_time
                result["airline"] = airline
                
                print(f"-> Melhor Voo: R$ {lowest_price} | {airline} | {extracted_time}")
                return result
            else:
                print("-> Nenhum preço detectado na tela (pode não haver voos ou a tela não carregou).")
                return None
                
    except Exception as e:
        print(f"-> Erro ao raspar: {e}")
        return None

if __name__ == "__main__":
    # Teste isolado
    from datetime import timedelta
    test_date = datetime.now() + timedelta(days=10)
    data = scrape_flights("IMP", "REC", test_date)
    print(data)
