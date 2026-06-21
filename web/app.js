document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("scraper-form");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const sheetBtn = document.getElementById("sheet-btn");
    const terminal = document.getElementById("terminal");
    const statusDot = document.getElementById("status-dot");
    const statusText = document.getElementById("status-text");

    let ws = null;

    // Helper: adiciona log no terminal
    function appendLog(text) {
        const line = document.createElement("div");
        line.className = "log-line";
        
        // Estilização básica baseada no conteúdo do log
        if (text.includes("[SISTEMA]") || text.includes("====================")) line.classList.add("system");
        else if (text.includes("[DEBUG]")) line.classList.add("debug");
        else if (text.includes("Jackpot!") || text.includes("Melhor Voo") || text.includes("[RESGATE]")) line.classList.add("success");
        else if (text.includes("ERRO") || text.includes("AVISO") || text.includes("Bloqueio")) line.classList.add("error");
        else if (text.includes("não foi alcançado")) line.classList.add("warning");

        line.textContent = text;
        terminal.appendChild(line);
        
        // Auto-scroll para o final
        terminal.scrollTop = terminal.scrollHeight;
    }

    // Inicializar e manter a conexão WebSocket
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log("WebSocket conectado.");
        };
        
        ws.onmessage = (event) => {
            appendLog(event.data);
        };
        
        ws.onclose = () => {
            console.log("WebSocket desconectado. Tentando reconectar em 3s...");
            setTimeout(connectWebSocket, 3000);
        };
    }

    // Atualiza a interface baseado no status do backend
    async function checkStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            
            if (data.sheet_url && data.sheet_url !== "#") {
                sheetBtn.href = data.sheet_url;
                sheetBtn.removeAttribute("disabled");
            }

            if (data.is_running) {
                setUIState(true);
            } else {
                setUIState(false);
            }
        } catch (e) {
            console.error("Erro ao checar status:", e);
        }
    }

    function setUIState(isRunning) {
        if (isRunning) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusDot.className = "status-dot active";
            statusText.textContent = "Protocolo em Execução...";
            statusText.style.color = "var(--primary-neon)";
            // Desabilita inputs
            document.querySelectorAll("input").forEach(i => i.disabled = true);
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusDot.className = "status-dot";
            statusText.textContent = "Sistema Ocioso";
            statusText.style.color = "var(--text-muted)";
            // Habilita inputs
            document.querySelectorAll("input").forEach(i => i.disabled = false);
        }
    }

    // Eventos dos botões
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const payload = {
            start_date: document.getElementById("start_date").value.replace(/\D/g, ""),
            end_date: document.getElementById("end_date").value.replace(/\D/g, ""),
            routes: document.getElementById("routes").value
        };

        try {
            const res = await fetch("/api/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (res.ok) {
                terminal.innerHTML = ""; // Limpa terminal anterior
                appendLog(`-> Inicializando Hydra com rotas: ${payload.routes}`);
                setUIState(true);
            } else {
                appendLog(`-> [ERRO] ${data.message}`);
                alert("Erro ao iniciar: " + data.message);
            }
        } catch (e) {
            alert("Erro de comunicação com o servidor.");
        }
    });

    stopBtn.addEventListener("click", async () => {
        if(!confirm("Tem certeza que deseja abortar a busca?")) return;
        
        try {
            const res = await fetch("/api/stop", { method: "POST" });
            if (res.ok) {
                setUIState(false);
                appendLog("-> Comando de aborto enviado ao servidor.");
            }
        } catch (e) {
            alert("Erro de comunicação com o servidor.");
        }
    });

    // Inicia
    connectWebSocket();
    
    // Poll de status (útil se recarregar a página)
    checkStatus();
    setInterval(checkStatus, 5000);
    
    // Define datas defaults fixas
    document.getElementById("start_date").value = "15/07/2026";
    document.getElementById("end_date").value = "30/07/2026";
    
    // --- Sprite Animation Logic ---
    const spriteContainer = document.getElementById("hydra-sprite-container");
    let spriteInterval = null;
    let currentFrame = 0;
    
    // Coordenadas X e Y para uma grade 4x2 (8 quadros)
    const frames = [
        "0% 0%",      // Frame 1 (Linha 1, Col 1)
        "100% 0%",    // Frame 2 (Linha 1, Col 2)
        "0% 33.333%", // Frame 3 (Linha 2, Col 1)
        "100% 33.333%",// Frame 4 (Linha 2, Col 2)
        "0% 66.666%", // Frame 5 (Linha 3, Col 1)
        "100% 66.666%",// Frame 6 (Linha 3, Col 2)
        "0% 100%",    // Frame 7 (Linha 4, Col 1)
        "100% 100%"   // Frame 8 (Linha 4, Col 2)
    ];

    // Modify setUIState to include animation control
    const originalSetUIState = setUIState;
    setUIState = function(isRunning) {
        originalSetUIState(isRunning);
        if (isRunning) {
            spriteContainer.style.display = "block";
            if (!spriteInterval) {
                spriteInterval = setInterval(() => {
                    spriteContainer.style.backgroundPosition = frames[currentFrame];
                    currentFrame = (currentFrame + 1) % frames.length;
                }, 400); // 400ms = 2.5 frames por segundo, estilo JRPG clássico
            }
        } else {
            spriteContainer.style.display = "none";
            if (spriteInterval) {
                clearInterval(spriteInterval);
                spriteInterval = null;
            }
        }
    };
});
