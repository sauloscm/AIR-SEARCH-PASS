import os
import json
import gspread
import pandas as pd

def get_google_client():
    """
    Autentica e retorna o client do gspread usando a variável de ambiente GOOGLE_CREDENTIALS_JSON.
    No GitHub Actions, essa variável será um Secret contendo o JSON da service account do GCP.
    """
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        print("Aviso: GOOGLE_CREDENTIALS_JSON não encontrada no .env")
        return None
    
    try:
        creds_dict = json.loads(credentials_json)
        # O gspread possui suporte nativo para dicts com google-auth
        client = gspread.service_account_from_dict(creds_dict)
        return client
    except Exception as e:
        print(f"Erro ao autenticar no Google Sheets: {e}")
        return None

def update_spreadsheet(flights_data: list):
    """
    Atualiza a planilha do Google com os menores preços diários consolidados.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("Aviso: GOOGLE_SHEET_ID não encontrada no .env")
        return

    client = get_google_client()
    if not client:
        return

    try:
        # Abre a planilha pelo ID
        spreadsheet = client.open_by_key(sheet_id)
        
        # Tenta pegar a aba de "Preços", senão usa a primeira
        try:
            worksheet = spreadsheet.worksheet("Preços")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.sheet1

        if not flights_data:
            print("Nenhum dado de voo para inserir.")
            return

        # Converter a lista de dicionários em DataFrame para facilitar agregações
        df = pd.DataFrame(flights_data)
        
        # Consolida os dados: pega o menor preço por Origem, Destino e Data
        idx = df.groupby(['origin', 'destination', 'date'])['price'].idxmin()
        best_flights_df = df.loc[idx].sort_values(by=['origin', 'date'])
        
        # Cabeçalho
        headers = ["Origem", "Destino", "Data", "Preço (BRL)", "Hora", "Companhia", "Fonte API", "Link"]
        
        # Formata os dados para inserção
        rows_to_insert = [headers]
        for _, row in best_flights_df.iterrows():
            rows_to_insert.append([
                row['origin'],
                row['destination'],
                row['date'],
                f"R$ {row['price']:.2f}",
                row['time'],
                row['airline'],
                row['source'],
                row['link']
            ])

        # Limpa a planilha inteira e atualiza com os novos dados
        print("Limpando dados antigos da planilha...")
        worksheet.clear()
        
        print("Inserindo os dados atualizados...")
        worksheet.update('A1', rows_to_insert)
        
        print(f"Planilha atualizada com sucesso! Total de {len(rows_to_insert)-1} voos registrados.")
        
    except Exception as e:
        print(f"Erro ao atualizar a planilha: {e}")

if __name__ == "__main__":
    # Teste isolado
    from dotenv import load_dotenv
    load_dotenv()
    # update_spreadsheet([{"origin": "IMP", "destination": "REC", "date": "2026-05-01", "price": 900.0, "time": "12:00", "airline": "LA", "source": "Teste", "link": ""}])
