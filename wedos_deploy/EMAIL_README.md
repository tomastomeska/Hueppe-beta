# 📧 Email konfigurace pro Hueppe systém

## Kompletní email funkcionalita implementována!

### ✅ **Co je nové:**

#### 🎯 **1. Zobrazení celkové váhy**
- Váha se nyní zobrazuje v Lane přehledu: **Celková váha: X.X kg**
- Váha se automaticky importuje ze sloupce F v Excel souboru
- Váha se započítává do LSA summarky v emailech

#### 📧 **2. Email systém pro dopravce**
**Kdy:** Po uzavření zakázky
**Předmět:** `Kódy k nakládce (DD.MM.YYYY)`
**Obsah:**
```
Dobrý den, posílám Vám seznam kódů LSA k naložení v Bad Zwisenhahn...

LSA kódy k naložení:
LSA CZEX001: 2 palety
LSA CZU001: 3 palety
...
```

#### 📋 **3. Email systém pro nakládku** 
**Kdy:** Po uzavření zakázky (s možností dodatečného textu)
**Předmět:** `Aviso (DD.MM.YYYY)`
**Obsah:** HTML tabulka s LSA kódy, počty palet, rozměry a váhami

#### ⚙️ **4. Konfigurace**

**settings.json:**
```json
{
  "smtp": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "your-email@gmail.com", 
    "password": "your-app-password",
    "use_tls": true,
    "from": "your-email@gmail.com"
  },
  "default_loading_emails": [
    "loading1@bad-zwisenhahn.com",
    "loading2@bad-zwisenhahn.com"
  ]
}
```

### 🎮 **Jak použít:**

#### **Při uzavírání zakázky:**
1. Vyplňte **email dopravce** (nepovinné)
2. Vyplňte **email adresy nakládky** (nepovinné - použijí se defaultní)
3. Zakázku uzavřete

#### **Po uzavření zakázky:**
1. **📩 Odeslat dopravci** - pošle LSA seznam dopravci
2. **📋 Odeslat na nakládku** - pošle detailní tabulku s možností přidat dodatečný text

#### **Aktualizace adres:**
- Můžete kdykoliv aktualizovat email adresy pro uzavřenou zakázku
- Změny se projeví při dalším odesílání emailů

### 🧪 **Testování:**
- Vytvořena testovací zakázka s ID 1
- Obsahuje ukázková LSA data s váhami
- **URL:** http://127.0.0.1:5000/order/1

### 📝 **Poznámky:**
- Pro Gmail použijte **App Password** místo hlavního hesla
- Emaily obsahují automaticky LSA summary podle přiřazených lanes
- Podporuje HTML formátování pro lepší čitelnost
- Váha se zobrazuje v kilogramech (kg)

### 🔧 **Pro produkční nasazení:**
1. Aktualizujte SMTP konfiguraci v `settings.json`
2. Nastavte správné default loading emails
3. Otestujte odesílání na testovací adresy