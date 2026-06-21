import os
import time
import random
import subprocess
import socket
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Atualiza sys.path para garantir que consegue achar os módulos
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.google_flights import scrape_flights
from spreadsheet_manager import update_spreadsheet


def find_chrome():
    """Localiza o executável do Google Chrome instalado no Windows."""
    paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def is_port_in_use(port):
    """Verifica se uma porta TCP está em uso."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


import socket
import argparse
import functools

print = functools.partial(print, flush=True)

def main():
    print("========================================")
    print(" MOTOR DE BUSCAS - WEB SCRAPING GOOGLE  ")
    print("   >> MODO HIDRA v2.0 - CDP STEALTH <<  ")
    print("========================================")
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Motor de buscas Google Flights")
    parser.add_argument("--start", type=str, help="Data de início (DD/MM/AAAA ou DDMMAAAA)")
    parser.add_argument("--end", type=str, help="Data de fim (DD/MM/AAAA ou DDMMAAAA)")
    parser.add_argument("--routes", type=str, help="Rotas separadas por vírgula (ex: IMP-REC,REC-IMP)")
    args = parser.parse_args()
    
    all_flights = []
    
    def parse_date_input(date_str):
        date_str = date_str.strip()
        if len(date_str) == 8 and date_str.isdigit():
            date_str = f"{date_str[:2]}/{date_str[2:4]}/{date_str[4:]}"
        return datetime.strptime(date_str, "%d/%m/%Y")
        
    start_date = None
    end_date = None

    if args.start and args.end:
        start_date = parse_date_input(args.start)
        end_date = parse_date_input(args.end)
    else:
        while True:
            try:
                user_input = input("\nDigite a data de INÍCIO (ou as duas datas juntas ex: 15072026 30072026): ").strip()
                
                # Checa se o usuário colou 16 números juntos (ex: 1507202630072026)
                if len(user_input) == 16 and user_input.isdigit():
                    start_date = parse_date_input(user_input[:8])
                    end_date = parse_date_input(user_input[8:])
                    break
                    
                # Checa se o usuário colou separadas por espaço
                parts = user_input.split()
                if len(parts) == 2:
                    start_date = parse_date_input(parts[0])
                    end_date = parse_date_input(parts[1])
                    break
                    
                # Se for apenas uma data
                start_date = parse_date_input(user_input)
                break
            except ValueError:
                print("Formato inválido! Tente DD/MM/AAAA ou DDMMAAAA.")
                
        while end_date is None:
            try:
                end_date_str = input("Digite a data de FIM: ").strip()
                end_date = parse_date_input(end_date_str)
                if end_date < start_date:
                    print("A data de fim não pode ser anterior à data de início!")
                    end_date = None
                    continue
                break
            except ValueError:
                print("Formato inválido! Tente DD/MM/AAAA ou DDMMAAAA.")
                
    start_date_str = start_date.strftime("%d/%m/%Y")
    end_date_str = end_date.strftime("%d/%m/%Y")
    
    print(f"\nIniciando raspagem de dados para o período de {start_date_str} a {end_date_str}...")
    print("Isso vai demorar algum tempo dependendo do intervalo (Pausas ativadas para evitar bloqueios).")
    
    # Vamos gerar as rotas e datas que queremos buscar
    searches = []
    
    routes_list = []
    if args.routes:
        for r in args.routes.split(","):
            parts = r.split("-")
            if len(parts) == 2:
                routes_list.append((parts[0].strip(), parts[1].strip()))
    else:
        routes_list = [("IMP", "REC"), ("REC", "IMP")]

    current_date = start_date
    while current_date <= end_date:
        for orig, dest in routes_list:
            searches.append((orig, dest, current_date))
        current_date += timedelta(days=1)
        
    total = len(searches)
    
    # =====================================================================
    # HIDRA v2.0 - LANÇAMENTO STEALTH VIA CDP
    # Em vez de deixar o Playwright lançar o Chrome (o que injeta flags de
    # automação detectáveis), nós lançamos o Chrome REAL via subprocess
    # como se o usuário tivesse clicado no ícone. Depois conectamos o
    # Playwright por fora via Chrome DevTools Protocol (CDP).
    # O Google NÃO consegue distinguir isso de um usuário real.
    # =====================================================================
    
    chrome_path = find_chrome()
    if not chrome_path:
        print("\n[ERRO FATAL] Google Chrome não encontrado no sistema!")
        print("Instale o Google Chrome e tente novamente.")
        time.sleep(5)
        return
    
    user_data_dir = os.path.abspath(os.path.join(os.getcwd(), 'chrome_profile'))
    debug_port = 9222
    
    # Encontra uma porta livre (evita conflito se o usuário tem Chrome aberto)
    for port_attempt in range(9222, 9232):
        if not is_port_in_use(port_attempt):
            debug_port = port_attempt
            break
    else:
        print("[ERRO] Nenhuma porta de debug disponível (9222-9231). Feche outras instâncias do Chrome.")
        time.sleep(5)
        return
    
    print(f"\n[STEALTH CDP] Lançando Chrome REAL via subprocess...")
    print(f"[STEALTH CDP] Executável: {chrome_path}")
    print(f"[STEALTH CDP] Perfil: {user_data_dir}")
    print(f"[STEALTH CDP] Porta de debug: {debug_port}")
    print(f"[STEALTH CDP] navigator.webdriver = undefined (genuíno, NÃO falsificado)")
    
    chrome_process = subprocess.Popen([
        chrome_path,
        f"--user-data-dir={user_data_dir}",
        f"--remote-debugging-port={debug_port}",
        "--lang=pt-BR",
        "--accept-lang=pt-BR,pt;q=0.9",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate",
        "--window-size=1280,800",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Aguarda o Chrome iniciar e abrir a porta de debug
    print("[STEALTH CDP] Aguardando Chrome inicializar...")
    for attempt in range(20):
        if is_port_in_use(debug_port):
            print(f"[STEALTH CDP] Chrome ativo na porta {debug_port}!")
            break
        time.sleep(1)
    else:
        print("[ERRO] Chrome não iniciou em tempo hábil!")
        chrome_process.terminate()
        time.sleep(5)
        return
    
    time.sleep(2)  # Espera extra para o Chrome estabilizar
    
    try:
        with sync_playwright() as p:
            print("[STEALTH CDP] Conectando Playwright ao Chrome via DevTools Protocol...")
            browser = p.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            print("\n========================================")
            print(" [HIDRA v2.0] Chrome REAL conectado!")
            print(" - Sem flags de automação")
            print(" - Sem banner 'controlado por software'")
            print(" - navigator.webdriver = undefined")
            print(" - Idioma: pt-BR | Moeda: BRL")
            print("========================================")
            print("\nIniciando a varredura...\n")
            
            idx = 0
            while idx < total:
                orig, dest, date = searches[idx]
                print(f"\nProgresso: {idx+1}/{total}")
                
                try:
                    result = scrape_flights(page, orig, dest, date)
                    if result and result["price"]:
                        all_flights.append(result)
                except RuntimeError as e:
                    if "SESSION_BLOCKED" in str(e):
                        print("-> [ANTI-BOT] Limpando sessão e aguardando cooldown...")
                        try:
                            # Limpa cookies e storage sem recriar o navegador
                            context.clear_cookies()
                            page.evaluate("try { window.localStorage.clear(); window.sessionStorage.clear(); } catch(e) {}")
                        except:
                            pass
                        time.sleep(10)
                        # Não incrementa o idx para tentar esse mesmo voo de novo!
                        continue
                    else:
                        print(f"-> [ERRO DESCONHECIDO] {e}")
                        
                # Pausa aleatória rápida (Chrome real = confiança máxima)
                delay = random.uniform(2.0, 5.0)
                print(f"Aguardando {delay:.1f} segundos antes da próxima página...")
                time.sleep(delay)
                
                idx += 1
    finally:
        # Garante que o Chrome seja fechado mesmo se houver erro
        print("\n[Limpeza] Encerrando Chrome...")
        chrome_process.terminate()
        try:
            chrome_process.wait(timeout=5)
        except:
            chrome_process.kill()

    print("\n[Finalizando] Atualizando a planilha do Google...")
    if all_flights:
        update_spreadsheet(all_flights)
    else:
        print("Nenhum preço foi encontrado. A planilha não será atualizada.")
        
    print("\n========================================")
    print("          PROCESSO CONCLUÍDO            ")
    print("========================================")
    
    # Aguarda 5 segundos para o usuário ver a mensagem antes do terminal fechar
    time.sleep(5)

if __name__ == "__main__":
    main()
