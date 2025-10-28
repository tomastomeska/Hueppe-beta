#!/usr/bin/env python3
"""
Script pro správu zakázek - zobrazení a mazání
"""

import sys
sys.path.append('.')
from app import app, db, Order, PalletItem, ImportedFile

def list_orders():
    """Zobrazí všechny zakázky"""
    with app.app_context():
        orders = Order.query.all()
        print("📋 Dostupné zakázky:")
        print("-" * 50)
        for order in orders:
            items_count = len(order.items)
            print(f"ID: {order.id:2d} | Název: '{order.name}' | Palety: {items_count}")
        return orders

def delete_order(order_id):
    """Smaže zakázku včetně všech palet"""
    with app.app_context():
        order = Order.query.get(order_id)
        if not order:
            print(f"❌ Zakázka s ID {order_id} neexistuje!")
            return False
        
        order_name = order.name
        
        # Smaž všechny importované soubory
        ImportedFile.query.filter_by(order_id=order_id).delete()
        
        # Smaž všechny palety
        PalletItem.query.filter_by(order_id=order_id).delete()
        
        # Smaž zakázku
        db.session.delete(order)
        db.session.commit()
        
        print(f"✅ Zakázka '{order_name}' (ID: {order_id}) byla smazána!")
        return True

if __name__ == "__main__":
    print("🛠️  Správa zakázek")
    print("=" * 30)
    
    orders = list_orders()
    
    if len(sys.argv) > 1 and sys.argv[1] == "delete":
        if len(sys.argv) > 2:
            try:
                order_id = int(sys.argv[2])
                delete_order(order_id)
            except ValueError:
                print("❌ ID zakázky musí být číslo!")
        else:
            print("❌ Použití: python manage_orders.py delete <order_id>")
    else:
        print("\n💡 Pro smazání zakázky použij:")
        print("   python manage_orders.py delete <order_id>")