#!/usr/bin/env python3
"""
Script pro správu LSA tabulek - zobrazení a mazání
"""

import sys
sys.path.append('.')
from app import app, db, LSATable, LSAItem

def list_lsa_tables():
    """Zobrazí všechny LSA tabulky"""
    with app.app_context():
        tables = LSATable.query.all()
        print("📊 Dostupné LSA tabulky:")
        print("-" * 60)
        for table in tables:
            items_count = len(table.items)
            print(f"ID: {table.id:2d} | Název: '{table.name}' | Řádků: {items_count} | Soubor: {table.filename}")
        return tables

def delete_lsa_table(table_id):
    """Smaže LSA tabulku včetně všech položek"""
    with app.app_context():
        table = LSATable.query.get(table_id)
        if not table:
            print(f"❌ LSA tabulka s ID {table_id} neexistuje!")
            return False
        
        table_name = table.name
        
        # Smaž všechny LSA items
        LSAItem.query.filter_by(table_id=table_id).delete()
        
        # Smaž tabulku
        db.session.delete(table)
        db.session.commit()
        
        print(f"✅ LSA tabulka '{table_name}' (ID: {table_id}) byla smazána!")
        return True

if __name__ == "__main__":
    print("📊 Správa LSA tabulek")
    print("=" * 35)
    
    tables = list_lsa_tables()
    
    if len(sys.argv) > 1 and sys.argv[1] == "delete":
        if len(sys.argv) > 2:
            try:
                table_id = int(sys.argv[2])
                delete_lsa_table(table_id)
            except ValueError:
                print("❌ ID tabulky musí být číslo!")
        else:
            print("❌ Použití: python manage_lsa_tables.py delete <table_id>")
    else:
        print("\n💡 Pro smazání LSA tabulky použij:")
        print("   python manage_lsa_tables.py delete <table_id>")