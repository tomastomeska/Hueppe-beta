# 🚀 Návod pro nasazení na Wedos server

## 📋 Požadavky
- Wedos hosting s podporou Pythonu 3.9+
- FTP/SFTP přístup (FileZilla)
- Přístup k administraci hostingu

## 📁 Struktura souborů pro upload

### 🔧 Produkční soubory (nahrát všechny):
```
├── app.py                    # Hlavní Flask aplikace
├── wsgi.py                   # WSGI entry point
├── .htaccess                 # Apache konfigurace
├── requirements.txt          # Python závislosti
├── settings.example.json     # Vzorová email konfigurace
└── templates/                # HTML šablony
    ├── base.html
    ├── index.html
    ├── order.html
    ├── upload.html
    ├── settings.html
    ├── imported_files.html
    └── print_order.html
```

### 🚫 NENAHRÁVAT:
- `.venv/` (virtual environment)
- `__pycache__/` (Python cache)
- `*.db` (databáze - vytvoří se automaticky)
- `.git/` (git repozitář)
- `.vscode/` (VS Code nastavení)

## 🔧 Postup nasazení

### 1. Příprava na Wedos
1. Přihlaste se do administrace Wedos
2. Aktivujte Python support pro vaši doménu
3. Nastavte Python verzi na 3.9 nebo vyšší

### 2. Upload souborů přes FileZilla
1. Připojte se k FTP/SFTP serveru
2. Přejděte do složky `public_html` (nebo root složky webu)
3. Nahrajte všechny produkční soubory zachovávající strukturu

### 3. Instalace závislostí
Na Wedos se připojte přes SSH nebo použijte webovou konzoli:
```bash
cd /path/to/your/website
pip3 install --user -r requirements.txt
```

### 4. Konfigurace emailů
1. Zkopírujte `settings.example.json` na `settings.json`
2. Pro Wedos hosting (doporučeno - žádné heslo potřeba):
```json
{
    "smtp": {
        "host": "localhost",
        "port": 25,
        "username": "",
        "password": "",
        "use_tls": false,
        "from": "tomeska@european.cz"
    }
}
```

3. Alternativně pro externí SMTP (pokud lokální nefunguje):
```json
{
    "smtp": {
        "host": "smtp.wedos.net",
        "port": 587,
        "username": "tomeska@european.cz",
        "password": "vase-heslo",
        "use_tls": true,
        "from": "tomeska@european.cz"
    }
}
```

### 5. Nastavení oprávnění
```bash
chmod 644 *.py
chmod 644 *.json
chmod 755 templates/
chmod 644 templates/*
```

### 6. Test aplikace
- Otevřete doménu v prohlížeči
- Měla by se zobrazit úvodní stránka aplikace
- Vyzkoušejte vytvoření zakázky a import Excel souboru

## 🔍 Řešení problémů

### Aplikace se nezobrazuje
1. Zkontrolujte `.htaccess` pravidla
2. Ověřte Python support v Wedos administraci
3. Zkontrolujte error logy na serveru

### Python moduly nejsou dostupné
```bash
pip3 install --user flask sqlalchemy pandas openpyxl
```

### Databáze se nevytváří
- Ověřte write oprávnění ve složce
- Zkontrolujte SQLite support na serveru

### Email nefunguje
1. Zkontrolujte `settings.json` konfiguraci
2. Ověřte SMTP nastavení u Wedos
3. Zkontrolujte firewall pravidla

## 📧 Konfigurace emailů

### Doporučené nastavení pro Wedos (bez hesla):
- **Host**: `localhost` (používá lokální SMTP server)
- **Port**: `25`
- **Username**: prázdné
- **Password**: prázdné
- **TLS**: `false`
- **From**: `tomeska@european.cz`

### Alternativní SMTP nastavení pro Wedos:
- **Server**: `smtp.wedos.net`
- **Port**: `587` (STARTTLS) nebo `465` (SSL)
- **Username**: `tomeska@european.cz`
- **Password**: heslo k emailu
- **TLS**: `true`

### Automatické fallback:
Aplikace se automaticky pokusí:
1. **Nejdříve** použít lokální SMTP server (localhost:25)
2. **Pokud selže**, použije externí SMTP server ze settings.json

### Testování emailů:
Po nasazení vyzkoušejte:
1. Vytvořte testovací zakázku
2. Uzavřete ji s email adresami
3. Odešlete test email

## 🔒 Bezpečnost

### Důležité:
- `settings.json` obsahuje citlivé údaje
- `.htaccess` blokuje přístup k `.py`, `.db` a config souborům
- Databáze se vytváří automaticky s restrictivními právy

### Doporučení:
- Použijte silná hesla pro email účty
- Pravidelně aktualizujte závislosti
- Monitorujte error logy

## 🎯 Výsledek

Po úspěšném nasazení budete mít:
- ✅ Funkční Flask aplikaci na vaší doméně
- ✅ Excel import s automatickým přiřazením linek
- ✅ Vizualizaci nákladu vozidla
- ✅ Drag & drop přesouvání palet
- ✅ Email systém pro dopravce a nakládku
- ✅ Kompletní správu paletového systému

## 📞 Podpora

V případě problémů:
1. Zkontrolujte error logy na Wedos serveru
2. Ověřte konfiguraci v administraci Wedos
3. Kontaktujte Wedos support pro specifické Python problémy