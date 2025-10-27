#!/usr/bin/env python3
"""
Kompletní SMTP test s autentizací a odesláním emailu
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

# Nastavení
SMTP_HOST = "smtp.european.cz"
SMTP_PORT = 587
USERNAME = "tomeska@european.cz"
PASSWORD = "eutomeska18"
FROM_EMAIL = "tomeska@european.cz"

def full_smtp_test():
    """Kompletní test včetně odeslání emailu"""
    print("🔍 Kompletní SMTP test...")
    print(f"Server: {SMTP_HOST}:{SMTP_PORT}")
    print(f"Username: {USERNAME}")
    print("-" * 50)
    
    try:
        # 1. Připojení
        print("1️⃣ Připojování k serveru...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        print("✅ Připojení úspěšné")
        
        # 2. EHLO
        print("2️⃣ EHLO...")
        server.ehlo()
        print("✅ EHLO úspěšné")
        
        # 3. TLS
        print("3️⃣ Aktivace TLS...")
        server.starttls()
        print("✅ TLS aktivováno")
        
        # 4. Autentizace
        print("4️⃣ Autentizace...")
        server.login(USERNAME, PASSWORD)
        print("✅ Autentizace úspěšná")
        
        # 5. Vytvoření emailu
        print("5️⃣ Vytváření testovacího emailu...")
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = FROM_EMAIL  # Pošleme sami sobě
        msg['Subject'] = "✅ SMTP Test - Hueppe systém - FUNKČNÍ!"
        
        body = f"""
Výborně! SMTP nastavení funguje správně! 🎉

Detaily připojení:
- Server: {SMTP_HOST}
- Port: {SMTP_PORT}
- TLS: Aktivní
- Username: {USERNAME}
- Čas testu: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Tento email potvrzuje, že Hueppe systém může úspěšně odesílat emaily.

Můžete nyní bezpečně používat:
- Emaily dopravcům s LSA seznamy
- Emaily na nakládku s detailními tabulkami
- Notifikace o nových zakázkách

S pozdravem,
Hueppe systém
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        print("✅ Email vytvořen")
        
        # 6. Odeslání
        print("6️⃣ Odesílání emailu...")
        server.send_message(msg)
        print("✅ Email úspěšně odeslán!")
        
        # 7. Ukončení
        server.quit()
        print("✅ Připojení ukončeno")
        
        print("\n🎉 SMTP NASTAVENÍ FUNGUJE PERFEKTNĚ!")
        print("📧 Zkontrolujte svou emailovou schránku na tomeska@european.cz")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Chyba: {e}")
        print(f"Typ chyby: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Kompletní SMTP Test pro Hueppe")
    print("=" * 60)
    
    success = full_smtp_test()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ SMTP KONFIGURACE JE SPRÁVNÁ!")
        print("📧 Emaily budou nyní fungovat ve vašem systému")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Je potřeba zkontrolovat nastavení")
        print("=" * 60)