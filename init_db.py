#!/usr/bin/env python3
"""
Skript pro inicializaci nových databázových tabulek
"""

import os
import sys

# Přidáme aktuální adresář do Python cesty
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, LSATable, LSAItem

def init_new_tables():
    """Vytvoří nové tabulky v databázi"""
    with app.app_context():
        try:
            # Vytvoříme jen nové tabulky
            db.create_all()
            print("✅ Nové tabulky pro LSA systém byly úspěšně vytvořeny")
            
            # Zkontrolujeme, zda tabulky existují
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
                all_tables = [row[0] for row in result.fetchall()]
                print(f"Všechny tabulky v databázi: {all_tables}")
                
                lsa_tables = [t for t in all_tables if 'lsa' in t.lower()]
                if lsa_tables:
                    print(f"✅ LSA tabulky nalezeny: {lsa_tables}")
                else:
                    print("❌ Žádné LSA tabulky nenalezeny")
                    
        except Exception as e:
            print(f"❌ Chyba při vytváření tabulek: {e}")
            return False
            
    return True

if __name__ == "__main__":
    print("Inicializace nových databázových tabulek...")
    success = init_new_tables()
    if success:
        print("🎉 Databáze je připravena pro nový LSA systém!")
    else:
        print("💥 Chyba při inicializaci databáze")
        sys.exit(1)