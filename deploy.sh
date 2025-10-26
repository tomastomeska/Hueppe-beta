#!/bin/bash
# Deployment script pro Wedos
# Spusťte tento skript po nahrání souborů na server

echo "🚀 Wedos deployment script pro Hueppe Bad Zwischenahn"
echo "=================================================="

# Kontrola Python verze
echo "📋 Kontrola Python verze..."
python3 --version

# Instalace závislostí
echo "📦 Instalace Python závislostí..."
pip3 install -r requirements.txt

# Kontrola, zda existuje settings.json
if [ ! -f "settings.json" ]; then
    echo "⚠️  VAROVÁNÍ: settings.json neexistuje!"
    echo "   Zkopírujte settings.example.json do settings.json"
    echo "   a vyplňte správné email údaje."
    cp settings.example.json settings.json
fi

# Nastavení práv
echo "🔐 Nastavení práv souborů..."
chmod 755 *.py
chmod 644 *.json *.md *.txt
chmod -R 644 templates/

# Kontrola WSGI
echo "🧪 Test WSGI konfigurace..."
python3 -c "import wsgi; print('✅ WSGI OK')"

# Kontrola hlavní aplikace
echo "🧪 Test hlavní aplikace..."
python3 -c "import app; print('✅ App OK')"

echo ""
echo "✅ Deployment dokončen!"
echo ""
echo "📋 Další kroky:"
echo "1. Upravte settings.json s vašimi email údaji"
echo "2. V Wedos administraci nastavte Python aplikaci:"
echo "   - Vstupní soubor: wsgi.py"
echo "   - Python verze: 3.8+"
echo "3. Otestujte aplikaci na vaší doméně"
echo ""