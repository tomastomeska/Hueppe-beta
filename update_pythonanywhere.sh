#!/bin/bash
# PythonAnywhere update script
# Spusťte tento script na PythonAnywhere po každém git push

echo "🔄 Aktualizace Hueppe aplikace..."

# Přejít do projektové složky
cd /home/tomastomeska/Hueppe-bz

# Stáhnout nejnovější změny
echo "📥 Stahování změn z GitHub..."
git pull origin main

# Aktivovat virtual environment
echo "🐍 Aktivace virtual environment..."
source venv/bin/activate

# Aktualizovat dependencies pokud se změnily
echo "📦 Kontrola dependencies..."
pip install -r requirements.txt --quiet

# Spustit test
echo "🧪 Spuštění testů..."
python test_pythonanywhere.py

echo "✅ Aktualizace dokončena!"
echo "🌐 Nezapomeňte restartovat web app v Web tabu!"
echo "   https://www.pythonanywhere.com/user/tomastomeska/webapps/"