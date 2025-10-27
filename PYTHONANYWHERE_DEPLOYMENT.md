# PythonAnywhere Deployment Guide - Hueppe BZ

## 📋 Požadavky
- PythonAnywhere účet (Free/Paid)
- **Python 3.10** (doporučená verze)
- Možnost nahrát soubory

## 🚀 Kroky pro nasazení:

### 1. Nahrání souborů
```bash
# Na PythonAnywhere console:
git clone https://github.com/tomastomeska/Hueppe-bz.git
cd Hueppe-bz
```

### 2. Instalace závislostí
```bash
# Vytvoření virtual environment s Python 3.10
python3.10 -m venv venv
source venv/bin/activate

# Instalace balíčků
pip install -r requirements.txt
```

### 3. Konfigurace WSGI
- Zkopírujte `wsgi_pythonanywhere.py` do `/var/www/`
- Upravte path v WSGI souboru:
```python
project_home = '/home/VASE_UZIVATELSKE_JMENO/Hueppe-bz'
```

### 4. Nastavení Web App
1. Jděte do **Web** tab
2. Klikněte **Add a new web app**
3. Vyberte **Manual configuration**
4. **Vyberte Python 3.10** ⭐
5. V **Code** sekci:
   - Source code: `/home/yourusername/Hueppe-bz`
   - WSGI file: `/var/www/yourusername_pythonanywhere_com_wsgi.py`

### 5. Konfigurace Virtual Environment
- V **Virtualenv** sekci zadejte:
  `/home/yourusername/Hueppe-bz/venv`

### 6. Statické soubory (pokud potřeba)
- URL: `/static/`
- Directory: `/home/yourusername/Hueppe-bz/static/`

### 7. Finální nastavení
- Vytvořte složku `uploads` pokud neexistuje
- Nastavte správná oprávnění pro SQLite databázi
- Upravte `settings.json` pro produkční prostředí

## 🔧 Požadované balíčky (requirements.txt):
```
Flask==2.2.5
Flask-SQLAlchemy==3.0.3
pandas==2.2.3
openpyxl==3.1.2
python-dotenv==1.0.0
Flask-Mail==0.9.1
```

## ⚙️ Důležité poznámky:
- Databáze se vytvoří automaticky při prvním spuštění
- Pro email funkce nastavte SMTP v `settings.json`
- Upload složka musí mít write oprávnění
- Pro Free účty pozor na CPU limity

## 🌐 Přístup:
Po nasazení bude aplikace dostupná na:
`https://yourusername.pythonanywhere.com`

## 🔍 Debugging:
- Loggy najdete v **Tasks** > **Error logs**
- Pro debugging můžete dočasně zapnout `debug=True`