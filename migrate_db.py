#!/usr/bin/env python3
"""
Migrace databáze pro přidání nového sloupce lsa_item_id do pallet_item tabulky
"""

import os
import sys
import sqlite3

# Přidáme aktuální adresář do Python cesty
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_database():
    """Přidá nový sloupec lsa_item_id do pallet_item tabulky"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hueppe.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Zkontroluj, zda sloupec již existuje
        cursor.execute("PRAGMA table_info(pallet_item)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'lsa_item_id' not in columns:
            print("Přidávám sloupec lsa_item_id do pallet_item tabulky...")
            cursor.execute("ALTER TABLE pallet_item ADD COLUMN lsa_item_id INTEGER")
            print("✅ Sloupec lsa_item_id byl úspěšně přidán")
        else:
            print("✅ Sloupec lsa_item_id již existuje")
        
        # Zkontroluj také změnu názvu sloupce name -> pallet_text
        if 'name' in columns and 'pallet_text' not in columns:
            print("Přejmenování sloupce 'name' na 'pallet_text'...")
            
            # SQLite nepodporuje přejmenování sloupců přímo
            # Musíme vytvořit novou tabulku a přenést data
            cursor.execute("""
                CREATE TABLE pallet_item_new (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    lsa_item_id INTEGER,
                    date_received VARCHAR(64),
                    lsa_designation VARCHAR(64),
                    lsa VARCHAR(64),
                    pallet_text VARCHAR(255),
                    qty INTEGER DEFAULT 1,
                    weight FLOAT DEFAULT 0.0,
                    length_m FLOAT DEFAULT 0.0,
                    assigned_lane INTEGER DEFAULT 0,
                    import_order INTEGER DEFAULT 0,
                    loaded BOOLEAN DEFAULT 0,
                    FOREIGN KEY (order_id) REFERENCES order(id),
                    FOREIGN KEY (lsa_item_id) REFERENCES lsa_item(id)
                )
            """)
            
            # Přenést existující data
            cursor.execute("""
                INSERT INTO pallet_item_new (
                    id, order_id, date_received, lsa_designation, lsa, pallet_text,
                    qty, weight, length_m, assigned_lane, import_order, loaded
                )
                SELECT 
                    id, order_id, date_received, lsa_designation, lsa, name,
                    qty, weight, length_m, assigned_lane, import_order, loaded
                FROM pallet_item
            """)
            
            # Smazat starou tabulku a přejmenovat novou
            cursor.execute("DROP TABLE pallet_item")
            cursor.execute("ALTER TABLE pallet_item_new RENAME TO pallet_item")
            
            print("✅ Sloupec 'name' byl přejmenován na 'pallet_text'")
        
        elif 'pallet_text' not in columns:
            print("Přidávám sloupec pallet_text...")
            cursor.execute("ALTER TABLE pallet_item ADD COLUMN pallet_text VARCHAR(255)")
            print("✅ Sloupec pallet_text byl přidán")
        
        conn.commit()
        conn.close()
        
        print("🎉 Migrace databáze byla úspěšně dokončena!")
        return True
        
    except Exception as e:
        print(f"❌ Chyba při migraci databáze: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("Spouštím migraci databáze...")
    success = migrate_database()
    if success:
        print("✨ Databáze je připravena pro nový LSA systém!")
    else:
        print("💥 Migrace se nezdařila")
        sys.exit(1)