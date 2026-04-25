# Air Search Pass ✈️

Um motor de buscas autônomo focado na extração e comparação de preços de passagens aéreas. O projeto foi arquitetado para atuar silenciosamente, raspando dados de passagens aéreas de voos específicos (como Imperatriz -> Recife) para uma janela de 60 dias, localizando os menores preços e consolidando-os automaticamente em uma planilha do Google.

## 🚀 Como funciona?

Este projeto contém duas abordagens de robôs:

1. **O Motor Principal (Google Flights):** Utiliza *Web Scraping* com a biblioteca Playwright para abrir um navegador fantasma e extrair de forma robusta e paralela os valores diretamente do agregador do Google Flights. O resultado é jogado em tempo real numa planilha da nuvem utilizando Google Service Accounts.
2. **O Motor Comparativo (Azul x LATAM x Google):** Um orquestrador paralelo feito para visitar as companhias separadamente, enfrentar os escudos de segurança delas e imprimir no terminal um embate de quem fornece a passagem mais barata.

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Playwright** (Raspagem de Dados / Navegação Headless)
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
