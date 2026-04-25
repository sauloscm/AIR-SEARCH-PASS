import os
import time
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Atualiza sys.path para garantir que consegue achar os módulos
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.google_flights import scrape_flights
from spreadsheet_manager import update_spreadsheet

def main():
    print("========================================")
    print(" MOTOR DE BUSCAS - WEB SCRAPING GOOGLE  ")
    print("========================================")
    
    load_dotenv()
    
    all_flights = []
    days_ahead = 60
    
    print(f"\nIniciando raspagem de dados para os próximos {days_ahead} dias...")
    print("Isso vai demorar entre 20 a 30 minutos (Pausas ativadas para evitar bloqueios).")
    
    # Vamos gerar as rotas e datas que queremos buscar
    searches = []
    for i in range(1, days_ahead + 1):
        target_date = datetime.now() + timedelta(days=i)
        searches.append(("IMP", "REC", target_date))
        searches.append(("REC", "IMP", target_date))
        
    total = len(searches)
    
    for idx, (orig, dest, date) in enumerate(searches):
        print(f"\nProgresso: {idx+1}/{total}")
        
        result = scrape_flights(orig, dest, date)
        if result and result["price"]:
            all_flights.append(result)
            
        # Pausa aleatória entre 5 e 15 segundos para enganar o anti-bot do Google
        delay = random.uniform(5, 15)
        print(f"Aguardando {delay:.1f} segundos antes da próxima página...")
        time.sleep(delay)

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
