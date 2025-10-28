#!/usr/bin/env python3
"""
Skript pro kompletní reinicializaci databáze (smaže vše a vytvoří znovu)
"""

import os
import sys
import sqlite3

# Přidáme aktuální adresář do Python cesty
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def clean_init_database():
    """Kompletně smaže a znovu vytvoří databázi"""
    try:
        # Najdeme všechny .db soubory a smažeme je
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        for db_file in db_files:
            try:
                os.remove(db_file)
                print(f"✅ Smazán starý databázový soubor: {db_file}")
            except Exception as e:
                print(f"❌ Nepodařilo se smazat {db_file}: {e}")
        
        # Vytvoříme novou databázi
        with app.app_context():
            # Dropneme všechny tabulky
            db.drop_all()
            print("✅ Všechny staré tabulky byly smazány")
            
            # Vytvoříme nové tabulky
            db.create_all()
            print("✅ Nové databázové tabulky byly vytvořeny")
            
            # Zkontrolujeme, zda tabulky existují
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
                all_tables = [row[0] for row in result.fetchall()]
                print(f"✅ Vytvořené tabulky: {all_tables}")
                
                # Ověříme základní tabulky
                required_tables = ['order', 'pallet_item', 'imported_file']
                missing_tables = [t for t in required_tables if t not in all_tables]
                if missing_tables:
                    print(f"❌ Chybí požadované tabulky: {missing_tables}")
                    return False
                else:
                    print("✅ Všechny požadované tabulky jsou přítomny")
                    
        return True
                    
    except Exception as e:
        print(f"❌ Chyba při reinicializaci databáze: {e}")
        return False

if __name__ == "__main__":
    print("=== KOMPLETNÍ REINICIALIZACE DATABÁZE ===")
    print("VAROVÁNÍ: Toto smaže všechna data!")
    
    success = clean_init_database()
    if success:
        print("🎉 Databáze byla úspěšně reinicializována!")
        print("📝 Můžete nyní bezpečně restartovat aplikaci")
    else:
        print("💥 Chyba při reinicializaci databáze")
        sys.exit(1)