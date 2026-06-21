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

        # Converter a lista de dicionários novos em DataFrame
        df_new = pd.DataFrame(flights_data)
        
        # Consolida os dados novos: pega o menor preço por Origem, Destino e Data
        idx = df_new.groupby(['origin', 'destination', 'date'])['price'].idxmin()
        best_flights_df = df_new.loc[idx]
        
        # Converte os novos dados para o formato/colunas da planilha
        new_records = []
        for _, row in best_flights_df.iterrows():
            min_found = row.get('min_price_found')
            if pd.isna(min_found) or min_found is None:
                min_found = row['price']
                
            new_records.append({
                "Origem": row['origin'],
                "Destino": row['destination'],
                "Data": row['date'],
                "Mínimo Encontrado (Aba)": f"R$ {min_found:.2f}",
                "Preço Validado (BRL)": f"R$ {row['price']:.2f}",
                "Hora": row['time'],
                "Companhia": row['airline'],
                "Fonte API": row['source'],
                "Link": row['link']
            })
            
        df_combined = pd.DataFrame(new_records)
            
        # Ordena a planilha final por Origem e Data
        df_combined = df_combined.sort_values(by=['Origem', 'Data'])
        
        headers = ["Origem", "Destino", "Data", "Mínimo Encontrado (Aba)", "Preço Validado (BRL)", "Hora", "Companhia", "Fonte API", "Link"]
        
        # Se alguma coluna não existir, adiciona
        for col in headers:
            if col not in df_combined.columns:
                df_combined[col] = ""
                
        # Converte para lista de listas
        rows_to_insert = [headers] + df_combined[headers].fillna("").values.tolist()

        # Limpa a planilha inteira e atualiza com os dados mesclados
        print("Substituindo dados antigos da planilha com os dados mesclados e atualizados...")
        worksheet.clear()
        
        print("Enviando dados para o Google Sheets...")
        worksheet.update('A1', rows_to_insert)
        
        print(f"Planilha atualizada com sucesso! Total de {len(rows_to_insert)-1} voos registrados atualmente na planilha.")
        
    except Exception as e:
        print(f"Erro ao atualizar a planilha: {e}")

if __name__ == "__main__":
    # Teste isolado
    from dotenv import load_dotenv
    load_dotenv()
    # update_spreadsheet([{"origin": "IMP", "destination": "REC", "date": "2026-05-01", "price": 900.0, "time": "12:00", "airline": "LA", "source": "Teste", "link": ""}])
