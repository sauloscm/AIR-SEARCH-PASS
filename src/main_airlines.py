import os
import time
import random
from datetime import datetime, timedelta

# Atualiza sys.path para garantir que consegue achar os módulos
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.google_flights import scrape_flights
from scraper.latam import scrape_latam
from scraper.azul import scrape_azul

def print_result(label, result):
    if result and result.get("price"):
        print(f"  [{label}] R$ {result['price']:.2f} | Hora: {result.get('time', 'N/A')} | Comp: {result.get('airline', 'N/A')}")
    else:
        print(f"  [{label}] Falhou ou não encontrou voos.")

def main():
    print("=====================================================")
    print(" MOTOR DE BUSCAS - COMPARADOR GOOGLE x AZUL x LATAM  ")
    print("=====================================================")
    
    days_ahead = 60
    best_flights_overall = []
    
    print(f"\nIniciando raspagem focada nas companhias para os próximos {days_ahead} dias...")
    print("ATENÇÃO: Este processo demorará muito mais devido à proteção dos sites.")
    
    searches = []
    for i in range(1, days_ahead + 1):
        target_date = datetime.now() + timedelta(days=i)
        searches.append(("IMP", "REC", target_date))
        searches.append(("REC", "IMP", target_date))
        
    total = len(searches)
    
    for idx, (orig, dest, date) in enumerate(searches):
        print(f"\n--- Progresso: {idx+1}/{total} | Data: {date.strftime('%Y-%m-%d')} | Rota: {orig}->{dest} ---")
        
        results = []
        
        # 1. Google Flights
        res_google = scrape_flights(orig, dest, date)
        print_result("GOOGLE", res_google)
        if res_google: results.append(res_google)
        
        # 2. LATAM
        res_latam = scrape_latam(orig, dest, date)
        print_result("LATAM", res_latam)
        if res_latam: results.append(res_latam)
            
        # 3. Azul
        res_azul = scrape_azul(orig, dest, date)
        print_result("AZUL ", res_azul)
        if res_azul: results.append(res_azul)
            
        if results:
            best = min(results, key=lambda x: x["price"])
            print(f">>> VENCEDOR DA DATA: {best['source']} por R$ {best['price']:.2f} <<<")
            best_flights_overall.append(best)
        else:
            print(">>> NENHUM VOO ENCONTRADO EM NENHUMA FONTE PARA ESTA DATA <<<")
            
        # Pausa aleatória longa para evitar bloqueio nos sites oficiais
        delay = random.uniform(10, 20)
        print(f"Aguardando {delay:.1f}s antes da próxima consulta...\n")
        time.sleep(delay)

    print("\n[Salvando Resultados]")
    if best_flights_overall:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resultados_search_azul_latam_air")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"resultado_comparativo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("Data\tOrigem\tDestino\tPreço (R$)\tHora\tCompanhia\tFonte/Agência\tLink\n")
            for bf in best_flights_overall:
                f.write(f"{bf['date']}\t{bf['origin']}\t{bf['destination']}\t{bf['price']}\t{bf.get('time', 'N/A')}\t{bf.get('airline', 'N/A')}\t{bf['source']}\t{bf['link']}\n")
        
        print(f"-> Arquivo TXT gerado com sucesso em: {filepath}")
        print("-> Basta copiar os dados de dentro desse arquivo e colar diretamente no Excel/Google Sheets.")
    else:
        print("-> Nenhum voo foi encontrado, então nenhum arquivo TXT foi gerado.")

    print("\n=====================================================")
    print("          PROCESSO COMPARATIVO CONCLUÍDO             ")
    print("=====================================================")
    time.sleep(10)

if __name__ == "__main__":
    main()
