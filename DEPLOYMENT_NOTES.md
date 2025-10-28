# 🚀 Deployment na PythonAnywhere - Centralizovaný LSA systém

## 📋 Klíčové změny v této verzi:

### ✅ **Nové funkcionality:**
1. **Centralizované LSA tabulky** - Nová stránka `/lsa_tables` pro správu LSA
2. **Upload Excel/CSV** - Automatické přeskočení hlavičky (skiprows=2)
3. **Import z LSA tabulek** - Možnost importovat LSA do zakázek z centrálních tabulek
4. **Sledování využití** - Přehled kde je každé LSA použito
5. **Testovací zakázky** - Možnost vytvořit prázdné zakázky pro testing

### ✅ **Opravy:**
1. **Delete funkcionalita** - Opravena JavaScript delete funkcionalita zakázek
2. **VS Code lint** - Odstraněny všechny lint chyby v onclick handlers
3. **Hlavičky souborů** - Automatické filtrování hlavičkových řádků v LSA tabulkách

### ✅ **Databázové změny:**
- Nové tabulky: `lsa_table`, `lsa_item`
- Nový sloupec: `pallet_item.lsa_item_id`

## 🔧 **Deployment kroky:**

### 1. **Aktualizace kódu na PythonAnywhere:**
```bash
cd /home/yourusername/Hueppe-bz
git pull origin main
```

### 2. **Migrace databáze:**
```bash
python3.11 migrate_db.py
```

### 3. **Instalace nových dependencies:**
```bash
pip3.11 install --user -r requirements.txt
```

### 4. **Nastavení EMAIL API (volitelné pro PythonAnywhere):**

> ⚠️ **BEZPEČNOST:** API klíče NIKDY neukládej do git repozitáře! Používej environment variables.

#### **SendGrid (Doporučeno - 100 emails/den zdarma):**
1. ✅ Registrace dokončena na [sendgrid.com](https://sendgrid.com)
2. ✅ API klíč vytvořen v Settings → API Keys
3. ✅ Template ID dostupný v Dynamic Templates
4. Nastav environment variable:
```bash
export SENDGRID_API_KEY='your_sendgrid_api_key_here'
```
5. **DŮLEŽITÉ:** Ověř sender email v SendGrid:
   - Jdi na Settings → Sender Authentication → Single Sender Verification
   - Přidej svou email adresu (např. tomas.tomeska@gmail.com)
   - Ověř email adresu přes potvrzovací email

#### **Mailgun (Alternativa - 5000 emails/měsíc zdarma):**
1. Registruj se na [mailgun.com](https://mailgun.com)
2. Ověř doménu a získej API klíč
3. Nastav environment variables:
```bash
export MAILGUN_API_KEY='your_mailgun_api_key_here'
export MAILGUN_DOMAIN='your-domain.mailgun.org'
```

#### **Nastavení env variables na PythonAnywhere:**
- Jdi na **Files** → **home/yourusername**
- Edituj `.bashrc` soubor
- Přidej na konec:
```bash
export SENDGRID_API_KEY='your_actual_sendgrid_api_key_here'
# nebo pro Mailgun:
# export MAILGUN_API_KEY='your_api_key_here'
# export MAILGUN_DOMAIN='your-domain.mailgun.org'
```
- Restartuj console: `source ~/.bashrc`

### 5. **Restart webové aplikace:**
- Jdi na Web tab v PythonAnywhere dashboard
- Klikni "Reload" pro restartování aplikace

### 6. **Testování:**
- Zkontroluj stránku `/lsa_tables`
- Otestuj upload LSA souboru
- Otestuj import LSA do zakázky
- Otestuj delete funkcionalita

## ⚠️ **Důležité poznámky:**

### **Databáze:**
- Automatická migrace přidá nové sloupce bez ztráty dat
- Existující data zůstanou zachována

### **LSA Upload:**
- Soubory musí mít alespoň 5 sloupců (A, B, C, D, E)
- Automaticky se přeskakují první 2 řádky (hlavička)
- Filtrují se nevalidní LSA kódy

### **Email systém:**
- **Lokálně:** Používá SMTP (localhost:25 nebo externí SMTP)
- **PythonAnywhere:** Automatický fallback na API služby
- **Fallback pořadí:** SMTP → SendGrid API → Mailgun API
- **Konfigurace:** Přes environment variables (volitelné)

## 🎯 **Nové URL endpointy:**
- `/lsa_tables` - Správa LSA tabulek
- `/upload_lsa_table` - Upload nové LSA tabulky
- `/get_lsa_table/<id>` - API pro obsah LSA tabulky
- `/import_lsa_from_table` - Import LSA z tabulky do zakázky
- `/create_test_order` - Vytvoření testovací zakázky

---
**Commit:** fd03a40
**Datum:** 28. 10. 2025
**Status:** ✅ Připraveno k deployment