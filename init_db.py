#!/usr/bin/env python3
"""
Skript pro inicializaci databáze
"""

import os
import sys

# Přidáme aktuální adresář do Python cesty
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def init_database():
    """Vytvoří databázové tabulky"""
    with app.app_context():
        try:
            # Vytvoříme všechny tabulky
            db.create_all()
            print("✅ Databázové tabulky byly úspěšně vytvořeny")
            
            # Zkontrolujeme, zda tabulky existují
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
                all_tables = [row[0] for row in result.fetchall()]
                print(f"Všechny tabulky v databázi: {all_tables}")
                    
        except Exception as e:
            print(f"❌ Chyba při vytváření tabulek: {e}")
            return False
            
    return True

if __name__ == "__main__":
    print("Inicializace databáze...")
    success = init_database()
    if success:
        print("🎉 Databáze je připravena!")
    else:
        print("💥 Chyba při inicializaci databáze")
        sys.exit(1)