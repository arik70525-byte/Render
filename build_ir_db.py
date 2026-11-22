# language: Python, file: build_ir_db.py
import urllib.request
import csv
import json
import io

print("[*] Скачиваем базу irdb с GitHub (это займет время)...")
url = "https://raw.githubusercontent.com/probonopd/irdb/master/codes/ALL.csv"
response = urllib.request.urlopen(url)
data = response.read().decode('utf-8')

print("[*] Парсим данные...")
csv_reader = csv.reader(io.StringIO(data))
db = {}

# Пропускаем заголовок
next(csv_reader, None)

count = 0
for row in csv_reader:
    if len(row) < 6: continue
    brand = row[0].strip().lower()
    device = row[1].strip().lower()
    function = row[3].strip().lower()
    protocol = row[4].strip()
    code = row[5].strip()
    
    # Нам нужны только те, где есть сырой код или протокол
    if brand not in db:
        db[brand] = {}
    if device not in db[brand]:
        db[brand][device] = {}
        
    # В irdb коды могут быть в формате protocol,device,subdevice,function
    # Для простоты сохраняем строку, сервер сам решит, как её отправить
    db[brand][device][function] = {"protocol": protocol, "code": code}
    count += 1

print(f"[+] Обработано {count} кодов. Сохраняем...")
with open("ir_full.json", "w") as f:
    json.dump(db, f)

print("[+] Готово! Файл ir_full.json создан.")
