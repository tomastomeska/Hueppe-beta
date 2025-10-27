# Rychlý Git Workflow pro Hueppe

## 📝 **Běžný workflow:**

### **Lokální změny:**
```bash
# 1. Spusťte a testujte lokálně
C:/wamp64/www/hueppe/.venv/Scripts/python.exe app.py

# 2. Po dokončení úprav uložte
git add -A
git commit -m "Popis změn"
git push origin main
```

### **Aktualizace na PythonAnywhere:**
```bash
# Na PythonAnywhere console:
bash update_pythonanywhere.sh

# Nebo manuálně:
cd /home/tomastomeska/Hueppe-bz
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

### **Restart aplikace:**
- Web tab → Reload yourusername.pythonanywhere.com

## 🚨 **Důležité tipy:**

### **Před každou změnou:**
- Testujte lokálně na http://127.0.0.1:5000
- Zkontrolujte, že vše funguje
- Commitujte pouze funkční kód

### **Po každé změně:**
- Git push na GitHub
- Git pull na PythonAnywhere  
- Restart web aplikace

### **Konfigurace:**
- `settings.json` můžete mít různý pro lokální vs PythonAnywhere
- Databáze se synchronizuje automaticky (SQLite soubor)
- Uploads složka se nesynchronizuje (přidejte do .gitignore)

## 🔧 **Užitečné příkazy:**

### **Lokální vývoj:**
```bash
# Spuštění serveru
C:/wamp64/www/hueppe/.venv/Scripts/python.exe app.py

# Test aplikace
C:/wamp64/www/hueppe/.venv/Scripts/python.exe test_pythonanywhere.py

# Zobrazení změn
git status
git diff
```

### **PythonAnywhere debug:**
```bash
# Logování chyb
tail -f /var/log/yourusername.pythonanywhere.com.error.log

# Test importů
python test_pythonanywhere.py

# Restart a log
# Web tab → Reload → Error logs
```