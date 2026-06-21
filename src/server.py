import os
import sys
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Hydra Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caminho para o diretório de arquivos estáticos da interface web
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")

# Estado global do processo do scraper
scraper_process = None
log_history = []
active_websockets = []

class ScraperConfig(BaseModel):
    start_date: str
    end_date: str
    routes: str

async def broadcast_log(message: str):
    log_history.append(message)
    # Mantém apenas os últimos 500 logs para não consumir muita memória
    if len(log_history) > 500:
        log_history.pop(0)
        
    for ws in active_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            pass

@app.post("/api/start")
async def start_scraper(config: ScraperConfig):
    global scraper_process, log_history
    if scraper_process and scraper_process.returncode is None:
        return JSONResponse({"status": "error", "message": "Scraper já está rodando!"}, status_code=400)

    log_history.clear()
    await broadcast_log(f"-> Iniciando scraper: Rotas {config.routes}, Período {config.start_date} a {config.end_date}")

    python_executable = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "main.py")

    cmd = [
        python_executable, 
        "-u",
        script_path, 
        "--start", config.start_date, 
        "--end", config.end_date,
        "--routes", config.routes
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        scraper_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            env=env
        )
        
        # Tarefa em background para ler os logs
        asyncio.create_task(read_process_output(scraper_process))
        return {"status": "success", "message": "Scraper iniciado com sucesso."}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/stop")
async def stop_scraper():
    global scraper_process
    if scraper_process and scraper_process.returncode is None:
        scraper_process.terminate()
        await broadcast_log("-> [SISTEMA] Processo do scraper foi interrompido pelo usuário.")
        return {"status": "success", "message": "Scraper parado."}
    return JSONResponse({"status": "error", "message": "Scraper não está rodando."}, status_code=400)

@app.get("/api/status")
async def get_status():
    global scraper_process
    is_running = scraper_process is not None and scraper_process.returncode is None
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else "#"
    
    return {
        "is_running": is_running,
        "sheet_url": sheet_url
    }

async def read_process_output(process):
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").strip()
        
        # Filtra os avisos chatos do Node.js/Playwright
        if "DeprecationWarning:" in text or "node --trace-deprecation" in text or "CVEs are not issued" in text:
            continue
            
        if text:
            await broadcast_log(text)
    
    await process.wait()
    await broadcast_log(f"-> [SISTEMA] Processo finalizado com código {process.returncode}")

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    
    # Envia o histórico atual ao conectar
    for log in log_history:
        await websocket.send_text(log)
        
    try:
        while True:
            # Mantém a conexão aberta e reage se o cliente desconectar
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)

# Serve a aplicação estática
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "Interface web não encontrada."})

if __name__ == "__main__":
    import uvicorn
    # Encontra a porta
    port = 8000
    print(f"=========================================")
    print(f" INICIANDO SERVIDOR WEB HYDRA")
    print(f" Acesse: http://localhost:{port}")
    print(f"=========================================")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
