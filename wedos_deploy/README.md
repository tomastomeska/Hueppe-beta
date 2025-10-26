Hueppe - Nakladka palet (prototype)

Prototype web app to upload .xlsx pallet lists and build orders.

Requirements:
- Python 3.10+ (download from https://www.python.org/downloads/)
- pip

Install Python first:
1. Download Python from https://www.python.org/downloads/windows/
2. During installation, check "Add Python to PATH"
3. Restart PowerShell

Install (PowerShell):

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Run:

python app.py

Open http://127.0.0.1:5000

Features:
- Upload xlsx: app reads rows from row 3 and columns A-F and expands pallets by quantity.
- Assign pallets to lane 1/2/3, compute lane totals and price.
- Close orders with carrier info (name, pickup time, truck plate).
- Print order view and email notifications.
- Settings page for prices, capacity, SMTP config.

Note: Configure SMTP settings in Settings page for email notifications to work.
