#!/usr/bin/env python3
"""
Kontrolní script pro ověření deployment na PythonAnywhere
"""

import os
import subprocess

def check_git_status():
    """Zkontroluje Git status"""
    print("🔍 Git status:")
    try:
        result = subprocess.run(['git', 'log', '--oneline', '-5'], 
                              capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"❌ Chyba Git: {e}")

def check_files():
    """Zkontroluje klíčové soubory"""
    files_to_check = [
        'templates/homepage.html',
        'templates/loading_orders.html'
    ]
    
    for file_path in files_to_check:
        print(f"\n📄 Kontrola {file_path}:")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Kontrola klíčových řetězců
                if file_path == 'templates/homepage.html':
                    if 'BETA' in content:
                        print("✅ BETA badge nalezen")
                    else:
                        print("❌ BETA badge CHYBÍ!")
                        
                    if 'position-absolute' in content:
                        print("✅ Beta styling nalezen")
                    else:
                        print("❌ Beta styling CHYBÍ!")
                        
                elif file_path == 'templates/loading_orders.html':
                    if 'betaWarningModal' in content:
                        print("✅ Beta modal nalezen")
                    else:
                        print("❌ Beta modal CHYBÍ!")
                        
                    if 'sessionStorage' in content:
                        print("✅ Session storage JS nalezen")
                    else:
                        print("❌ Session storage JS CHYBÍ!")
        else:
            print(f"❌ Soubor {file_path} neexistuje!")

def check_current_commit():
    """Zkontroluje aktuální commit"""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True)
        current = result.stdout.strip()[:8]
        
        result = subprocess.run(['git', 'rev-parse', 'origin/main'], 
                              capture_output=True, text=True)
        remote = result.stdout.strip()[:8]
        
        print(f"🔍 Aktuální commit: {current}")
        print(f"🔍 Remote commit:   {remote}")
        
        if current == remote:
            print("✅ Repozitář je aktuální")
        else:
            print("❌ Repozitář NENÍ aktuální! Spusť: git pull origin main")
            
    except Exception as e:
        print(f"❌ Chyba při kontrole commitů: {e}")

if __name__ == "__main__":
    print("🔧 Kontrola deployment na PythonAnywhere")
    print("=" * 45)
    
    check_current_commit()
    check_git_status()
    check_files()
    
    print("\n💡 Pokud chybí změny:")
    print("1. git pull origin main")
    print("2. Restart v Web tabu")
    print("3. Vyčisti cache (Ctrl+F5)")