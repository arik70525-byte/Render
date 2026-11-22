# language: Python, file: main.py, platform: Render
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests, json, re, os
from queue import Queue
from urllib.parse import urlparse

app = FastAPI()

# Разрешаем запросы с любых устройств (Android)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ================= ЗАГРУЗКА ИК-БАЗЫ =================
IR_DB = {}
if os.path.exists("ir_full.json"):
    print("[*] Загрузка ИК-базы в память...")
    with open("ir_full.json", "r") as f:
        IR_DB = json.load(f)
    print(f"[+] ИК-база загружена. Брендов: {len(IR_DB)}")
else:
    print("[!] ВНИМАНИЕ: ir_full.json не найден. ИК-пульт работать не будет.")

# ================= 1. БАЗА КАМЕР =================
def scan_cameras():
    results = []
    try:
        r = requests.get("https://www.insecam.org/en/bycountry/RU/", headers=HEADERS, timeout=10)
        ips = re.findall(r'<a href="http://([0-9.]+):?(\d*)', r.text)
        for ip, port in ips[:10]:
            results.append({"ip": ip, "port": port if port else "80", "status": "Открыта"})
    except Exception as e:
        results.append({"error": str(e)})
    return results

# ================= 2. СКАНЕР САЙТОВ =================
def scan_site(target):
    if not target.startswith("http"): target = "https://" + target
    res = {"target": target, "vulns": []}
    paths = ["/.env", "/.git/config", "/backup.sql", "/admin/"]
    for path in paths:
        try:
            r = requests.get(target.rstrip('/') + path, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                res["vulns"].append({"type": "CRITICAL", "path": path, "info": r.text[:100]})
        except: pass
    return res

# ================= 3. ЛЕВИАФАН (Граф) =================
def leviathan(start_type, start_value):
    visited = set()
    queue = Queue()
    queue.put((start_type, start_value))
    graph = {"target": start_value, "findings": []}
    
    while not queue.empty():
        curr_type, curr_val = queue.get()
        if (curr_type, curr_val) in visited: continue
        visited.add((curr_type, curr_val))
        
        if curr_type == "phone":
            try:
                r = requests.get(f"https://t.me/{curr_val}", headers=HEADERS, timeout=5)
                if "tgme_page_title" in r.text:
                    graph["findings"].append({"source": "Telegram", "data": f"Аккаунт: t.me/{curr_val}"})
                    queue.put(("nick", curr_val))
            except: pass
        if curr_type == "nick":
            try:
                r = requests.get(f"https://github.com/{curr_val}", headers=HEADERS, timeout=5)
                if r.status_code == 200 and "Page not found" not in r.text:
                    graph["findings"].append({"source": "GitHub", "data": f"Профиль: github.com/{curr_val}"})
            except: pass
    return graph

# ================= 4. ОБРАБОТКА ЧАТА =================
@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    text = data.get('text', '').lower()
    
    if not text:
        return {"reply": "Пустой запрос."}

    # --- ИК-ПУЛЬТ ---
    if text.startswith("ик ") or text.startswith("ir "):
        parts = text.split(" ")
        if len(parts) >= 3:
            brand = parts[1]
            action = parts[2]
            if brand in IR_DB and action in IR_DB[brand]:
                return {"reply": f"ИК-код найден: {brand} {action}", "ir_data": IR_DB[brand][action]}
            else:
                return {"reply": f"Код для {brand} ({action}) не найден."}
        return {"reply": "Формат: ИК samsung power"}

    # --- КАМЕРЫ ---
    if "камер" in text:
        return {"reply": "Сканирую открытые камеры...", "data": scan_cameras()}
    
    # --- САЙТ ---
    if "сайт" in text or "url" in text:
        url_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-z]{2,})', text)
        if url_match:
            return {"reply": f"Сканирую {url_match.group(0)}...", "data": scan_site(url_match.group(0))}
        return {"reply": "Укажи сайт."}
    
    # --- ЛЕВИАФАН ---
    if "номер" in text or "телефон" in text:
        phone_match = re.search(r'(\+?\d{10,15})', text)
        if phone_match:
            return {"reply": f"Запускаю Левиафан для {phone_match.group(0)}...", "data": leviathan("phone", phone_match.group(0))}
        return {"reply": "Укажи номер."}

    return {"reply": "Не понял. Используй: 'камеры', 'сайт example.com', 'номер 7999...', 'ИК samsung power'."}

# Пинг для Render
@app.get("/")
def root(): return {"status": "Brain is alive"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
