# Hydra Air Search ✈️

Um motor de buscas autônomo focado na extração e comparação de preços de passagens aéreas. O projeto agora conta com uma interface Web moderna (Controle Central Hydra) que executa a raspagem em segundo plano, localizando os menores preços e consolidando-os automaticamente em uma planilha do Google.

## 🚀 Como funciona?

Este projeto foi atualizado para a versão **Hydra v2.0 - CDP Stealth**:

1. **O Motor Principal (Google Flights):** Utiliza *Web Scraping* com a biblioteca Playwright para abrir um navegador fantasma e extrair de forma robusta e paralela os valores do Google Flights.
2. **Interface Web Interativa:** Um painel de controle construído com FastAPI e WebSockets que exibe logs em tempo real como um terminal Matrix, acompanhado de uma animação clássica em 8-bits da Hydra regenerando suas cabeças enquanto minera os preços.
3. **Google Sheets Integration:** O resultado é jogado na nuvem instantaneamente utilizando Google Service Accounts.

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+ & FastAPI** (Backend e WebSockets)
- **HTML, CSS e JavaScript** (Interface do Painel)
- **Playwright** (Raspagem de Dados / Navegação Headless stealth)
- **gspread & pandas** (Gestão, formatação e inserção no banco de dados / Google Sheets)
- **Git** (Versionamento)

## 💻 Instalação

1. Clone o repositório em sua máquina:
   ```bash
   git clone https://github.com/sauloscm/AIR-SEARCH-PASS.git
   cd AIR-SEARCH-PASS
   ```
2. Instale as dependências Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Instale o navegador embutido do Playwright (Obrigatório para o scraping):
   ```bash
   python -m playwright install chromium
   ```

## ⚙️ Configuração (Variáveis de Ambiente)

Para que a gravação das passagens na sua nuvem funcione, você precisa criar um arquivo chamado `.env` na raiz do projeto (use o `.env.example` como base).

Lá dentro, preencha:
```env
GOOGLE_SHEET_ID=seu_id_da_planilha_aqui
GOOGLE_CREDENTIALS_JSON={"type": "service_account", "project_id": "..."}
```
*Lembre-se de dar acesso de **Editor** à sua planilha para o email listado no seu `GOOGLE_CREDENTIALS_JSON`.*

## ▶️ Uso

Para rodar o robô principal (que atualiza as planilhas do Google) basta executar o atalho bat:
```bash
./run_search.bat
```
*(Ele pode ser colocado na pasta `shell:startup` do Windows para iniciar junto ao computador).*

Para rodar a versão paralela comparativa:
```bash
./run_search_airlines.bat
```

## 🔒 Segurança

**IMPORTANTE:** O seu arquivo `.env` contendo a chave (JSON) da Conta de Serviço do Google Cloud nunca deve ser "comitado". Este projeto já possui um `.gitignore` configurado adequadamente para barrar a injeção desse arquivo no controle de versão.
