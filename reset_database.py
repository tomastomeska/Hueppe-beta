#!/usr/bin/env python3
"""
Script pro vymazání a znovu inicializaci databáze
POZOR: Toto smaže všechna data!
"""

import os
import sys

def reset_database():
    """Smaže databázi a vytvoří novou"""
    db_path = 'hueppe.db'
    
    print("⚠️  POZOR: Toto smaže všechna data v databázi!")
    
    # Kontrola existence databáze
    if os.path.exists(db_path):
        print(f"📄 Nalezena databáze: {db_path}")
        
        # Potvrzení
        if len(sys.argv) > 1 and sys.argv[1] == '--force':
            confirm = 'ano'
        else:
            confirm = input("Opravdu chcete smazat databázi? (napište 'ano'): ").lower()
        
        if confirm == 'ano':
            try:
                # Smazání databáze
                os.remove(db_path)
                print(f"✅ Databáze {db_path} byla smazána")
                
                # Reinicializace
                import init_db
                print("🔄 Reinicializace databáze...")
                
                print("✨ Databáze byla úspěšně resetována!")
                print("\n📋 Doporučené kroky:")
                print("1. Restart webové aplikace")
                print("2. Kontrola funkcionalita")
                print("3. Import záložních dat (pokud potřeba)")
                
            except Exception as e:
                print(f"❌ Chyba při mazání databáze: {e}")
        else:
            print("❌ Reset zrušen")
    else:
        print(f"⚠️  Databáze {db_path} neexistuje")
        print("🔄 Vytvoření nové databáze...")
        
        try:
            import init_db
            print("✅ Nová databáze byla vytvořena")
        except Exception as e:
            print(f"❌ Chyba při vytváření databáze: {e}")

if __name__ == "__main__":
    print("🗑️  Reset databáze Hueppe")
    print("=" * 30)
    reset_database()