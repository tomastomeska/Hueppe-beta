# Hueppe Bad Zwischenahn - Wedos Deployment Guide

## Přenos na Wedos server

### 1. Příprava souborů
Nahrajte tyto soubory na váš Wedos hosting:
- `app.py` - hlavní aplikace
- `wsgi.py` - WSGI konfigurace pro Wedos
- `requirements.txt` - Python závislosti
- `templates/` - složka se všemi šablonami
- `settings.json` - email konfigurace (vytvořte podle settings.example.json)

### 2. Konfigurace Python prostředí na Wedos
1. Přihlaste se do Wedos administrace
2. Jděte do sekce "Python aplikace"
3. Vytvořte novou Python aplikaci (Python 3.8+)
4. Nastavte:
   - **Vstupní soubor**: `wsgi.py`
   - **Adresář aplikace**: root složka vašeho webu
   - **Python verze**: 3.8 nebo novější

### 3. Instalace závislostí
V terminále Wedos spusťte:
```bash
pip install -r requirements.txt
```

### 4. Konfigurace databáze
Databáze SQLite se vytvoří automaticky při prvním spuštění.
Ujistěte se, že má aplikace práva na zápis do složky.

### 5. Email konfigurace
Vytvořte soubor `settings.json` podle vzoru `settings.example.json`:
```json
{
    "smtp_server": "smtp.wedos.net",
    "smtp_port": 587,
    "smtp_username": "vas-email@vase-domena.cz",
    "smtp_password": "vase-heslo",
    "smtp_use_tls": true,
    "default_sender": "vas-email@vase-domena.cz"
}
```

### 6. Práva souborů
Ujistěte se, že má aplikace práva na:
- Čtení všech souborů aplikace
- Zápis do složky pro SQLite databázi
- Zápis pro nahrávání Excel souborů

### 7. Testování
Po nahrání navštivte vaši doménu a otestujte:
- Vytvoření nové zakázky
- Import Excel souboru
- Přiřazení na linky
- Email funkce

### Řešení problémů
- Pokud aplikace nefunguje, zkontrolujte error logy v Wedos administraci
- Ověřte, že jsou nainstalované všechny závislosti z requirements.txt
- Zkontrolujte práva souborů a složek
- Ověřte správnost email konfigurace v settings.json

### Struktura souborů na serveru:
```
/
├── app.py
├── wsgi.py
├── requirements.txt
├── settings.json
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── order.html
│   └── ...
└── hueppe.db (vytvoří se automaticky)
```