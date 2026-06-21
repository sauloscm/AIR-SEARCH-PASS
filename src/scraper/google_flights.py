import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import functools

print = functools.partial(print, flush=True)

def extract_price(text: str):
    """
    Tenta extrair o valor numérico de um texto contendo R$.
    Ex: "R$ 1.250" ou "R$1,505" -> 1250.0 ou 1505.0
    """
    matches = re.findall(r'R\$\s*([\d\.,]+)', text)
    if matches:
        # Pega sempre o ÚLTIMO valor de preço do card, para evitar coisas como "Economize R$ 200" ou "Bagagem R$ 100" que aparecem antes
        val_str = matches[-1]
        # Descarta centavos se houver (,00 ou .00)
        if len(val_str) >= 3 and val_str[-3] in [',', '.']:
            val_str = val_str[:-3]
        
        # Remove os demais pontos e vírgulas
        val = val_str.replace('.', '').replace(',', '')
        try:
            return float(val)
        except ValueError:
            return None
    return None

def scrape_flights(page, origin: str, destination: str, target_date: datetime) -> dict:
    """
    Usa o Playwright para raspar a página do Google Flights para uma data específica.
    Força Point-of-Sale brasileiro via parâmetros hl/gl/curr na URL.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    
    # =====================================================================
    # URL COM IDENTIDADE BRASILEIRA FORÇADA (Point-of-Sale / POS)
    # - hl=pt-BR  -> Força a interface em Português do Brasil
    # - gl=BR     -> Força a geolocalização do servidor para Brasil
    # - curr=BRL  -> Força a moeda para Real Brasileiro
    # =====================================================================
    url = (
        f"https://www.google.com/travel/flights"
        f"?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{date_str}%20oneway"
        f"&hl=pt-BR&gl=BR&curr=BRL"
    )
    
    print(f"[{origin}->{destination}] Acessando Google Flights para o dia {date_str}...")
    
    result = {
        "source": "Google Flights (Scraper)",
        "origin": origin,
        "destination": destination,
        "date": date_str,
        "time": "N/A",
        "price": None,
        "min_price_found": None,
        "currency": "BRL",
        "airline": "Múltiplas/Google",
        "link": url
    }

    try:
        # Troca networkidle por domcontentloaded para não travar em trackers de terceiros
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # Tenta fechar o aviso de cookies (se aparecer na Europa ou em janela anônima)
        try:
            page.locator('button:has-text("Aceitar tudo"), button:has-text("Accept all")').click(timeout=3000)
        except:
            pass

        # Aguarda a aparição do símbolo monetário como forte indicativo que os preços carregaram
        try:
            page.wait_for_selector('text="R$"', timeout=10000)
        except:
            # Se não achou R$, pode ser que a tela de erro apareceu
            try:
                # Verifica se é a tela de "O itinerário selecionado não está mais disponível" (voo não existe mais)
                if page.get_by_text("não está mais disponível", exact=False).is_visible(timeout=1000) or page.get_by_text("não estão mais disponíveis", exact=False).is_visible():
                    print("-> Google Flights informou: 'O itinerário selecionado não está mais disponível'. Pulando dia...")
                    return None
                    
                # Tenta localizar o botão de forma genérica
                btn_atualizar = page.locator('text=/Atualizar|Refresh|Reload|Tentar novamente/i').locator('visible=true').first
                if not btn_atualizar.is_visible(timeout=1000):
                    btn_atualizar = page.get_by_role("button", name=re.compile(r"Atualizar|Refresh|Reload", re.IGNORECASE)).first
                    
                if btn_atualizar.is_visible(timeout=2000):
                    print("-> Google Flights exibiu 'Algo deu errado'. Forçando um Reload completo da página...")
                    page.reload(timeout=30000, wait_until='domcontentloaded')
                    page.wait_for_timeout(4000)
                    
                    # Verifica se a tela de erro continuou
                    if page.locator('text=/Atualizar|Refresh|Reload|Tentar novamente/i').locator('visible=true').count() > 0:
                        print("-> O erro persistiu após o reload! Limpando cache da sessão e navegando forçadamente...")
                        try:
                            page.context.clear_cookies()
                            page.evaluate("window.localStorage.clear(); window.sessionStorage.clear();")
                            page.evaluate("navigator.serviceWorker.getRegistrations().then(function(rs) { for(let r of rs) { r.unregister() } })")
                        except:
                            pass
                            
                        page.goto(url, timeout=30000, wait_until='domcontentloaded')
                        page.wait_for_timeout(5000)
                        
                        if page.locator('text=/Atualizar|Refresh|Reload|Tentar novamente/i').locator('visible=true').count() > 0:
                            print("-> [CRÍTICO] Bloqueio severo detectado. A sessão foi envenenada.")
                            raise RuntimeError("SESSION_BLOCKED")
            except RuntimeError:
                raise
            except Exception as e:
                pass
        
        # =====================================================================
        # CABEÇA 1 DA HIDRA: Ler a aba "Menores preços" / "Cheapest"
        # Lê o preço mínimo SEM CLICAR (evita recarregar a página)
        # Suporta interface em PT-BR e EN como fallback
        # =====================================================================
        target_price = 0
        try:
            aba_menores = page.locator('text=/Menores preços|Cheapest/i').locator('visible=true').first
            if aba_menores.is_visible(timeout=3000):
                txt_aba = aba_menores.inner_text()
                target_price = extract_price(txt_aba) or 0
                print(f"-> [DEBUG] Aba 'Menores preços' diz que o mínimo é R$ {target_price} (Não clicaremos nela!)")
        except:
            pass

        # Garante que os cartões de voo terminaram de carregar no React
        try:
            page.wait_for_function(r'''() => {
                let els = Array.from(document.querySelectorAll('li, div[role="listitem"]'));
                return els.some(el => /\d{1,2}:\d{2}/.test(el.innerText) && (
                    el.innerText.includes('parada') || el.innerText.includes('direto') ||
                    el.innerText.includes('stop') || el.innerText.includes('nonstop')
                ));
            }''', timeout=15000)
        except:
            print("-> [DEBUG] Timeout esperando os cartões de voo renderizarem no DOM.")

        # =====================================================================
        # CABEÇA 2A DA HIDRA: CAPTURA IMEDIATA dos cards ANTES de interagir
        # O Google Flights atualiza os resultados dinamicamente quando o
        # usuário interage (scroll, clique). Voos baratos como Azul R$886
        # podem DESAPARECER após "Mostrar mais voos" ou scroll. Por isso,
        # capturamos os cards AGORA, antes de qualquer interação.
        #
        # ANTI-RACE-CONDITION: A aba "Menores preços" às vezes já mostra o
        # preço final (ex: R$886), mas os cards ainda exibem preços
        # provisórios (ex: R$958). Se detectarmos essa inconsistência,
        # aguardamos e re-capturamos até os preços estabilizarem.
        # =====================================================================
        early_cards = []
        max_early_attempts = 3
        for attempt in range(max_early_attempts):
            early_cards = []
            try:
                early_elements = page.locator('li, div[role="listitem"]').all()
                if attempt == 0:
                    print(f"-> [DEBUG] Captura antecipada: {len(early_elements)} elementos ANTES de interagir...")
                for i, el in enumerate(early_elements):
                    try:
                        if el.is_visible():
                            txt = el.inner_text()
                            has_time = re.search(r'\d{1,2}:\d{2}', txt)
                            has_flight_word = any(w in txt.lower() for w in ['parada', 'direto', 'stop', 'nonstop', 'escala'])
                            if has_time and len(txt) > 20 and (has_flight_word or 'h' in txt):
                                p_val = extract_price(txt)
                                if p_val and p_val > 50:
                                    early_cards.append({
                                        'index': i,
                                        'price': p_val,
                                        'text': txt,
                                        'locator': el,
                                        'source': 'early'
                                    })
                    except:
                        pass
            except Exception as e:
                print(f"-> [DEBUG] Erro na captura antecipada: {e}")

            if early_cards:
                early_min = min(c['price'] for c in early_cards)
                # Se a aba "Menores preços" indica um preço menor do que encontramos,
                # os cards ainda estão com preços provisórios. Esperamos e tentamos de novo.
                if target_price > 0 and early_min > target_price and attempt < max_early_attempts - 1:
                    print(f"-> [DEBUG] Captura antecipada (tentativa {attempt+1}): mín R$ {early_min} > aba R$ {target_price}. Preços ainda provisórios, aguardando 2s...")
                    page.wait_for_timeout(2000)
                    continue
                else:
                    early_prices = [c['price'] for c in early_cards]
                    print(f"-> [DEBUG] Captura antecipada encontrou {len(early_cards)} voos: mín R$ {min(early_prices)}, máx R$ {max(early_prices)}")
                    break
            else:
                if attempt < max_early_attempts - 1:
                    page.wait_for_timeout(2000)
                    continue
                break

        # =====================================================================
        # CABEÇA 2B DA HIDRA: Clicar em "Mostrar mais voos" para revelar voos escondidos
        # =====================================================================
        try:
            btn_mais = page.locator('text=/Mostrar mais voos|More flights|Outros voos/i').locator('visible=true').first
            if btn_mais.is_visible(timeout=2000):
                btn_mais.click(timeout=3000)
                print("-> [DEBUG] Clicou em 'Mostrar mais voos' para revelar voos ocultos!")
                page.wait_for_timeout(2000)
        except:
            pass

        # Rola a página para baixo e para cima para forçar o React a renderizar os cards ocultos (virtualized list)
        for _ in range(5):
            page.keyboard.press('PageDown')
            page.wait_for_timeout(300)
        for _ in range(5):
            page.keyboard.press('PageUp')
            page.wait_for_timeout(300)

        # =====================================================================
        # CABEÇA 3 DA HIDRA: Varrer TODOS os cards visíveis na página (pós-interação)
        # =====================================================================
        valid_cards = []
        elements = page.locator('li, div[role="listitem"]').all()
        print(f"-> [DEBUG] Analisando {len(elements)} elementos da lista principal (pós-interação)...")
        for i, el in enumerate(elements):
            if el.is_visible():
                txt = el.inner_text()
                has_time = re.search(r'\d{1,2}:\d{2}', txt)
                has_flight_word = any(w in txt.lower() for w in ['parada', 'direto', 'stop', 'nonstop', 'escala'])
                if has_time and len(txt) > 20 and (has_flight_word or 'h' in txt):
                    p_val = extract_price(txt)
                    if p_val and p_val > 50:
                        valid_cards.append({
                            'index': i,
                            'price': p_val,
                            'text': txt,
                            'locator': el,
                            'source': 'post'
                        })

        # =====================================================================
        # MERGE: Combina cards da captura antecipada com os pós-interação.
        # Se um voo barato sumiu após a interação (ex: Azul R$886), ele ainda
        # estará nos early_cards e será considerado no resultado final.
        # =====================================================================
        post_prices = {c['price'] for c in valid_cards}
        early_only = []
        for ec in early_cards:
            # Adiciona cards antecipados que NÃO existem mais nos pós-interação
            # (compara por horário para evitar duplicatas)
            ec_time = re.search(r'\d{1,2}:\d{2}', ec['text'])
            ec_time_str = ec_time.group(0) if ec_time else ""
            already_exists = False
            for vc in valid_cards:
                vc_time = re.search(r'\d{1,2}:\d{2}', vc['text'])
                vc_time_str = vc_time.group(0) if vc_time else ""
                if ec_time_str == vc_time_str and abs(ec['price'] - vc['price']) < 10:
                    already_exists = True
                    break
            if not already_exists:
                early_only.append(ec)
                print(f"-> [RESGATE] Voo de R$ {ec['price']} ({ec_time_str}) capturado antes de sumir da página!")

        # Adiciona os voos resgatados à lista
        valid_cards.extend(early_only)

        if not valid_cards:
            print("-> Nenhum preço de voo detectado na tela principal (Mesmo após recarregar).")
            return None

        # Ordenar os cards pelo preço de fachada (para priorizar os mais baratos aparentes)
        valid_cards = sorted(valid_cards, key=lambda x: x['price'])
        
        overall_best_price = float('inf')
        overall_best_text = ""
        overall_airline = ""
        overall_time = ""

        # =====================================================================
        # CABEÇA 4 DA HIDRA: Deep Scan nos 3 voos mais baratos
        # =====================================================================
        cards_to_check = valid_cards[:3]
        print(f"-> [DEBUG] Iniciando Deep Scan em {len(cards_to_check)} voos para achar preços de agências...")
        
        for idx, card in enumerate(cards_to_check):
            print(f"\n-> [SCAN {idx+1}/{len(cards_to_check)}] Verificando voo de fachada R$ {card['price']}...")
            
            time_match = re.search(r'\d{1,2}:\d{2}', card['text'])
            extracted_time = time_match.group(0) if time_match else "N/A"
            
            airline = "Múltiplas/Google"
            if "Azul" in card['text']: airline = "Azul"
            elif "GOL" in card['text'] or "Gol" in card['text']: airline = "GOL"
            elif "LATAM" in card['text'] or "Latam" in card['text']: airline = "LATAM"
            elif "Voepass" in card['text'] or "Passaredo" in card['text']: airline = "Voepass"

            local_best_price = card['price']

            # Se o voo foi resgatado da captura antecipada (sumiu da página),
            # não podemos clicar nele. Usamos o preço de fachada diretamente.
            if card.get('source') == 'early':
                print(f"-> [RESGATE] Voo resgatado da captura antecipada. Usando preço de fachada R$ {card['price']} diretamente.")
                if local_best_price < overall_best_price:
                    overall_best_price = local_best_price
                    overall_best_text = card['text']
                    overall_airline = airline
                    overall_time = extracted_time
                if target_price > 0 and overall_best_price <= target_price:
                    print(f"-> [DEBUG] Jackpot! Preço alvo de R$ {target_price} atingido/superado!")
                    break
                continue

            try:
                if idx > 0:
                    for _ in range(5):
                        page.keyboard.press('PageDown')
                        page.wait_for_timeout(300)
                    for _ in range(5):
                        page.keyboard.press('PageUp')
                        page.wait_for_timeout(300)
                        
                    reloaded_elements = page.locator('li, div[role="listitem"]').all()
                    found = False
                    for rel in reloaded_elements:
                        if rel.is_visible() and extracted_time in rel.inner_text():
                            rel.click(timeout=5000)
                            found = True
                            break
                    if not found:
                        print(f"-> [DEBUG] Não conseguiu reencontrar o card (procurando por {extracted_time}) após voltar. Pulando.")
                        continue
                else:
                    card['locator'].click(timeout=5000)
                
                print(f"-> Clicou no voo ({airline}). Aguardando expansão...")
                
                # Clica em Selecionar voo (PT e EN)
                try:
                    page.wait_for_timeout(1000)
                    btn_selecionar = page.locator('button:has-text("Selecionar"), button:has-text("Select flight"), button:has-text("Select")').locator('visible=true').first
                    if btn_selecionar.is_visible(timeout=3000):
                        btn_selecionar.click(timeout=5000)
                except:
                    pass
                
                # =====================================================================
                # CABEÇA 5 DA HIDRA: Extração inteligente de preços de agências
                # =====================================================================
                try:
                    try:
                        page.wait_for_selector('text=/Opções de reserva|Booking options/i', state='visible', timeout=8000)
                    except:
                        btn_atualizar = page.locator('text=/Atualizar|Refresh|Reload|Tentar novamente/i').locator('visible=true').first
                        if not btn_atualizar.is_visible(timeout=1000):
                            btn_atualizar = page.get_by_role("button", name=re.compile(r"Atualizar|Refresh|Reload", re.IGNORECASE)).first
                            
                        if btn_atualizar.is_visible(timeout=2000):
                            btn_atualizar.click(timeout=3000)
                            page.wait_for_selector('text=/Opções de reserva|Booking options/i', state='visible', timeout=15000)
                    
                    page.wait_for_timeout(2000)
                    
                    for _ in range(4):
                        page.keyboard.press('PageDown')
                        page.wait_for_timeout(500)
                        
                    # Extrai preços de agências (botões PT e EN)
                    details_text = page.evaluate('''() => {
                        let textBlocks = [];
                        let elements = document.querySelectorAll('button, a, div[role="button"], span[role="button"]');
                        for (let el of elements) {
                            if (el.innerText && /Continuar|Selecionar|Reservar|Acessar|Ir para|Continue|Book|Select|View deal/i.test(el.innerText)) {
                                let parent = el.parentElement;
                                for(let i=0; i<4; i++) {
                                    if(parent && parent.parentElement) parent = parent.parentElement;
                                }
                                if (parent) textBlocks.push(parent.innerText);
                            }
                        }
                        return textBlocks.join(' --- ');
                    }''')
                    
                    if not details_text.strip():
                        print("-> [DEBUG] AVISO: Nenhum botão de agência encontrado na página de detalhes!")
                        details_text = page.evaluate('document.body.innerText')
                    
                    details_text = re.sub(r'(?i)economize.*?R\$.*', '', details_text)
                    details_text = re.sub(r'(?i)save.*?R\$.*', '', details_text)
                    
                    details_prices = []
                    for match in re.finditer(r'(.{0,30})R\$\s*([\d\.,]+)(.{0,30})', details_text.replace('\n', ' ')):
                        prefix = match.group(1).strip()
                        val_str = match.group(2)
                        suffix = match.group(3).strip()
                        if len(val_str) >= 3 and val_str[-3] in [',', '.']:
                            val_str = val_str[:-3]
                        try:
                            val = float(val_str.replace('.', '').replace(',', ''))
                            if val > 50:
                                blacklist = ['hotel', 'carro', 'aluguel', 'ganhe', 'car', 'rent', 'earn']
                                ctx_lower = (prefix + suffix).lower()
                                if not any(bl in ctx_lower for bl in blacklist):
                                    details_prices.append(val)
                        except:
                            pass
                    
                    if details_prices:
                        min_detail_price = min(details_prices)
                        print(f"-> [DEBUG] Mínimo na agência para este voo: R$ {min_detail_price}")
                        if min_detail_price < local_best_price:
                            local_best_price = min_detail_price
                            
                except Exception as details_ex:
                    print(f"-> [DEBUG] Detalhes não carregaram ou voo direto: {details_ex}")
                    
            except Exception as e:
                print(f"-> [DEBUG] Erro ao interagir com card: {e}")
            
            # Atualiza o recorde global
            if local_best_price < overall_best_price:
                overall_best_price = local_best_price
                overall_best_text = card['text']
                overall_airline = airline
                overall_time = extracted_time
                
            # Se já achamos o preço alvo (ou menor), não precisa olhar os outros cards!
            if target_price > 0 and overall_best_price <= target_price:
                print(f"-> [DEBUG] Jackpot! Preço alvo de R$ {target_price} atingido/superado!")
                break
                
            # Prepara para o próximo loop: volta para a tela principal
            if idx < len(cards_to_check) - 1:
                print("-> Retornando para a página de resultados da data atual...")
                try:
                    page.goto(url, timeout=30000, wait_until='domcontentloaded')
                except:
                    pass
                page.wait_for_timeout(3000)

        # =====================================================================
        # CABEÇA 6 DA HIDRA: Último recurso - clica na aba "Menores preços"
        # Se o Deep Scan não alcançou o preço-alvo, tenta reordenar a lista
        # =====================================================================
        if target_price > 0 and overall_best_price > target_price:
            print(f"\n-> [HIDRA] O preço-alvo R$ {target_price} não foi alcançado (melhor: R$ {overall_best_price}).")
            print(f"-> [HIDRA] Ativando Cabeça 6: Clicando na aba 'Menores preços'...")
            try:
                page.goto(url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
                
                aba_menores_click = page.locator('text=/Menores preços|Cheapest/i').locator('visible=true').first
                if aba_menores_click.is_visible(timeout=3000):
                    aba_menores_click.click(timeout=5000)
                    page.wait_for_timeout(4000)
                    
                    # Expande a lista
                    try:
                        btn_mais2 = page.locator('text=/Mostrar mais voos|More flights|Outros voos/i').locator('visible=true').first
                        if btn_mais2.is_visible(timeout=2000):
                            btn_mais2.click(timeout=3000)
                            page.wait_for_timeout(2000)
                    except:
                        pass
                    
                    # Re-varre os cards na aba "Menores preços"
                    cheapest_elements = page.locator('li, div[role="listitem"]').all()
                    for el in cheapest_elements:
                        if el.is_visible():
                            txt = el.inner_text()
                            has_time = re.search(r'\d{1,2}:\d{2}', txt)
                            if has_time and len(txt) > 20:
                                p_val = extract_price(txt)
                                if p_val and p_val > 50 and p_val < overall_best_price:
                                    overall_best_price = p_val
                                    overall_best_text = txt
                                    overall_time = has_time.group(0)
                                    if "Azul" in txt: overall_airline = "Azul"
                                    elif "GOL" in txt or "Gol" in txt: overall_airline = "GOL"
                                    elif "LATAM" in txt or "Latam" in txt: overall_airline = "LATAM"
                                    elif "Voepass" in txt: overall_airline = "Voepass"
                                    print(f"-> [HIDRA] Cabeça 6 encontrou preço menor: R$ {p_val} | {overall_airline} | {overall_time}")
            except Exception as e:
                print(f"-> [HIDRA] Cabeça 6 falhou: {e}")

        # Após o scan, salva o melhor encontrado
        result["price"] = overall_best_price
        result["min_price_found"] = target_price if target_price > 0 else overall_best_price
        result["time"] = overall_time
        result["airline"] = overall_airline
        
        print(f"-> Melhor Voo Encontrado: R$ {overall_best_price} | {overall_airline} | {overall_time}")
        return result

    except RuntimeError:
        # Repassa o erro de bloqueio severo para o main.py lidar (recriar navegador)
        raise
    except Exception as e:
        print(f"-> Erro ao raspar: {e}")
        return None

if __name__ == "__main__":
    # Teste isolado
    from datetime import datetime
    from playwright.sync_api import sync_playwright
    test_date = datetime(2026, 7, 30)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="pt-BR", timezone_id="America/Sao_Paulo", viewport={'width': 1280, 'height': 720})
        page = context.new_page()
        data = scrape_flights(page, "REC", "IMP", test_date)
        print(data)
        browser.close()
