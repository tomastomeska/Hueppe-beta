@echo off
echo 🚀 Vytváření Wedos deployment balíčku...
echo =====================================

REM Vytvoření deployment složky
if exist "wedos_deploy" rmdir /s /q wedos_deploy
mkdir wedos_deploy

REM Kopírování produkčních souborů
echo 📦 Kopírování souborů...
copy app.py wedos_deploy\
copy wsgi.py wedos_deploy\
copy requirements.txt wedos_deploy\
copy settings.example.json wedos_deploy\
copy .htaccess wedos_deploy\
copy README.md wedos_deploy\
copy EMAIL_README.md wedos_deploy\
copy WEDOS_DEPLOYMENT.md wedos_deploy\
copy deploy.sh wedos_deploy\

REM Kopírování templates složky
echo 📁 Kopírování templates...
xcopy /E /I templates wedos_deploy\templates

echo.
echo ✅ Deployment balíček vytvořen ve složce: wedos_deploy
echo.
echo 📋 Další kroky:
echo 1. Zazipujte složku 'wedos_deploy'
echo 2. Nahrajte ZIP na váš Wedos hosting
echo 3. Rozbalte na serveru
echo 4. Vytvořte settings.json podle settings.example.json
echo 5. Spusťte deploy.sh (nebo postupujte podle WEDOS_DEPLOYMENT.md)
echo.
pause