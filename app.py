import os
import json
import re
import smtplib
import hashlib
from datetime import datetime
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from flask import Flask, render_template, request, redirect, url_for, flash, make_response, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import pandas as pd

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.json')

# Load settings with error handling
try:
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        SETTINGS = json.load(f)
except FileNotFoundError:
    print(f"Warning: {SETTINGS_PATH} not found, using default settings")
    SETTINGS = {
        "smtp": {
            "host": "localhost",
            "port": 25,
            "username": "",
            "password": "",
            "use_tls": False,
            "from": "tomeska@european.cz"
        }
    }

app = Flask(__name__)
# Use environment variable for secret key in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-me-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'hueppe.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed = db.Column(db.Boolean, default=False)
    saved_for_later = db.Column(db.Boolean, default=False)
    capacity_m = db.Column(db.Float, default=SETTINGS.get('default_capacity_m', 13.6))
    price_per_place = db.Column(db.Float, default=SETTINGS.get('price_per_place', 1160.0))
    full_truck_price = db.Column(db.Float, default=SETTINGS.get('full_truck_price', 25600.0))
    # Carrier info
    carrier_name = db.Column(db.String(120))
    pickup_datetime = db.Column(db.DateTime)
    truck_license_plate = db.Column(db.String(20))
    # Email addresses
    carrier_email = db.Column(db.String(120))
    loading_emails = db.Column(db.Text)  # JSON string pro více emailů
    user_email = db.Column(db.String(120))  # Email uživatele pro Reply-To
    # Loading status and tracking numbers
    is_loaded = db.Column(db.Boolean, default=False)
    delivered = db.Column(db.Boolean, default=False)
    za_number = db.Column(db.String(50))  # ZA číslo (např. ZA-10250)
    oo_number = db.Column(db.String(50))  # OO číslo (např. OO-11056)

    def __repr__(self):
        return f'<Order {self.id} {self.name}>'

class ImportedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False, unique=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    rows_imported = db.Column(db.Integer, default=0)
    
    order = db.relationship('Order', backref=db.backref('imported_files', lazy=True))

# Nové modely pro centralizované LSA tabulky
class LSATable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # Název tabulky LSA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    filename = db.Column(db.String(255))  # Původní název souboru
    file_hash = db.Column(db.String(64))  # Hash souboru pro duplicity
    rows_count = db.Column(db.Integer, default=0)  # Počet řádků v tabulce
    
    def __repr__(self):
        return f'<LSATable {self.id} {self.name}>'

class LSAItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('lsa_table.id'), nullable=False)
    date_received = db.Column(db.String(64))  # Column A - Date when pallet overview was received
    lsa_designation = db.Column(db.String(64))  # Column B - LSA designation (CZEX, CZU atd.)
    lsa = db.Column(db.String(64))  # Column C - LSA code
    pallet_text = db.Column(db.String(255))  # Column D - Item text
    qty = db.Column(db.Integer, default=1)
    weight = db.Column(db.Float, default=0.0)
    length_m = db.Column(db.Float, default=0.0)  # Column E - Length in meters
    import_order = db.Column(db.Integer, default=0)  # Původní pořadí importu
    used_in_orders = db.Column(db.Text)  # JSON seznam order_id kde byla použita
    
    table = db.relationship('LSATable', backref=db.backref('items', lazy=True))
    
    def __repr__(self):
        return f'<LSAItem {self.id} LSA:{self.lsa} len:{self.length_m} m>'

class PalletItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    # Reference na LSA item (pokud je z tabulky)
    lsa_item_id = db.Column(db.Integer, db.ForeignKey('lsa_item.id'), nullable=True)
    date_received = db.Column(db.String(64))  # Column A - Date when pallet overview was received
    lsa_designation = db.Column(db.String(64))  # Column B - LSA designation (CZEX, CZU atd.)
    lsa = db.Column(db.String(64))  # Column C - LSA code
    pallet_text = db.Column(db.String(255))  # Column D - Item text
    qty = db.Column(db.Integer, default=1)
    weight = db.Column(db.Float, default=0.0)
    length_m = db.Column(db.Float, default=0.0)  # Column E - Length in meters
    assigned_lane = db.Column(db.Integer, default=0)  # 0=unassigned,1,2,3 lanes
    import_order = db.Column(db.Integer, default=0)  # Původní pořadí importu
    loaded = db.Column(db.Boolean, default=False)  # Označení skutečně naložených palet

    order = db.relationship('Order', backref=db.backref('items', lazy=True))
    lsa_item = db.relationship('LSAItem', backref=db.backref('pallet_items', lazy=True))

    def __repr__(self):
        return f'<Pallet {self.id} LSA:{self.lsa} len:{self.length_m} m lane:{self.assigned_lane}>'

def init_db():
    db.create_all()
    
    # Migrace pro přidání sloupce 'delivered' 
    try:
        # Zkusíme přidat sloupec delivered, pokud neexistuje
        with db.engine.begin() as conn:
            result = conn.execute(db.text("PRAGMA table_info([order])"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'delivered' not in columns:
                conn.execute(db.text("ALTER TABLE [order] ADD COLUMN delivered BOOLEAN DEFAULT 0"))
                print("Added 'delivered' column to Order table")
    except Exception as e:
        print(f"Migration note: {e}")
    
    # Migrace pro přidání sloupce 'loaded' do PalletItem
    try:
        with db.engine.begin() as conn:
            result = conn.execute(db.text("PRAGMA table_info(pallet_item)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'loaded' not in columns:
                conn.execute(db.text("ALTER TABLE pallet_item ADD COLUMN loaded BOOLEAN DEFAULT 0"))
                print("Added 'loaded' column to PalletItem table")
    except Exception as e:
        print(f"Migration note for PalletItem: {e}")

def get_lsa_color(lsa_code):
    """Vrátí konzistentní barvu pro LSA kód"""
    if not lsa_code:
        return '#6c757d'  # šedá pro prázdné
    
    # Hash LSA kódu pro konzistentní barvy
    import hashlib
    hash_object = hashlib.md5(lsa_code.encode())
    hash_hex = hash_object.hexdigest()
    
    # Převod na HSL pro lepší čitelnost
    hue = int(hash_hex[:2], 16) * 360 // 256
    saturation = 70  # 70% saturace
    lightness = 45   # 45% světlost
    
    return f'hsl({hue}, {saturation}%, {lightness}%)'

# Registrace funkce pro template
app.jinja_env.globals.update(get_lsa_color=get_lsa_color)

@app.template_filter('from_json')
def from_json_filter(value):
    """Jinja filter pro parsování JSON stringu"""
    try:
        return json.loads(value) if value else []
    except:
        return []

def parse_length_from_text(text):
    # Expect formats like '80x230' or 'Standard EWP 80x130' -> extract second number
    # 80x230 means 230cm length = 2.30m
    if not isinstance(text, str):
        return 0.0
    m = re.search(r"(\d{2,3})\s*[xX]\s*(\d{2,3})", text)
    if m:
        # first group width (80), second group length (e.g., 230)
        width = int(m.group(1))
        length = int(m.group(2))
        # convert length cm to meters
        return round(length / 100.0, 3)
    # fallback: try to find a three-digit number
    m2 = re.search(r"(\d{3})", text)
    if m2:
        length = int(m2.group(1))
        return round(length / 100.0, 3)
    return 0.0

def auto_assign_lanes(order_id):
    """Automatically assign pallets to lanes using round-robin with auto-optimization"""
    order = Order.query.get_or_404(order_id)
    all_items = PalletItem.query.filter_by(order_id=order.id).order_by(PalletItem.import_order).all()
    
    if not all_items:
        return
    
    # Reset all assignments first
    for item in all_items:
        item.assigned_lane = 0
    
    # Simple round-robin assignment: 1, 2, 3, 1, 2, 3, ... (podle původního pořadí importu)
    for i, item in enumerate(all_items):
        lane = (i % 3) + 1  # gives 1, 2, 3, 1, 2, 3, ...
        item.assigned_lane = lane
    
    db.session.commit()
    
    # Automatická optimalizace: přesuň palety z přetížených lanes
    lane_totals = [0.0, 0.0, 0.0]
    
    # Spočítej aktuální zatížení lanes
    for item in all_items:
        if item.assigned_lane:
            lane_totals[item.assigned_lane - 1] += item.length_m
    
    # Finalizace: přesuň palety z přetížených lanes
    max_lane_capacity = 13.6
    
    for lane_idx in range(3):
        if lane_totals[lane_idx] > max_lane_capacity:
            # Najdi palety v této lane (seřazené od nejmenších)
            lane_items = [item for item in all_items if item.assigned_lane == lane_idx + 1]
            lane_items.sort(key=lambda x: x.length_m)
            
            # Zkus přesunout nejmenší palety
            for item in lane_items:
                if lane_totals[lane_idx] <= max_lane_capacity:
                    break
                    
                # Najdi jinou lane s dostatečným místem
                for target_lane in range(3):
                    if target_lane != lane_idx and lane_totals[target_lane] + item.length_m <= max_lane_capacity:
                        # Přesuň paletu
                        lane_totals[lane_idx] -= item.length_m
                        lane_totals[target_lane] += item.length_m
                        item.assigned_lane = target_lane + 1
                        break
    
    db.session.commit()

def calculate_file_hash(file_content):
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()

def send_email(to_emails, subject, body, html_body=None, sender_email=None, reply_to=None):
    """Odešle email pomocí SMTP konfigurace nebo lokálního sendmail"""
    try:
        smtp_config = SETTINGS.get('smtp', {})
        
        # Nastavení odesílací adresy (custom nebo výchozí)
        from_email = sender_email or smtp_config.get('from', 'tomeska@european.cz')
        
        # Vytvoření emailu
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['Subject'] = subject
        
        # Nastavení Reply-To pokud je specifikované
        if reply_to:
            msg['Reply-To'] = reply_to
        elif sender_email and sender_email != from_email:
            # Pokud je custom sender, nastavit jako Reply-To
            msg['Reply-To'] = sender_email
        
        # Přidání textové části
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Přidání HTML části pokud je k dispozici
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        # Příprava seznamu emailů
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        
        valid_emails = [email.strip() for email in to_emails if email.strip()]
        if not valid_emails:
            return False, "Žádné platné email adresy"
        
        # Zkusíme nejdříve lokální odesílání (pro Wedos hosting)
        try:
            # Použití lokálního SMTP serveru (typické pro shared hosting)
            server = smtplib.SMTP('localhost', 25)
            
            for email in valid_emails:
                msg['To'] = email
                server.send_message(msg)
                del msg['To']  # Odstranit pro další iteraci
            
            server.quit()
            return True, "Email byl úspěšně odeslán přes lokální server"
            
        except Exception as local_error:
            print(f"Lokální SMTP selhal: {local_error}")
            
            # Fallback na externí SMTP server
            if smtp_config.get('host') and smtp_config.get('host') != 'localhost':
                server = smtplib.SMTP(smtp_config.get('host'), smtp_config.get('port', 587))
                
                if smtp_config.get('use_tls', True):
                    server.starttls()
                
                if smtp_config.get('username') and smtp_config.get('password'):
                    server.login(smtp_config.get('username'), smtp_config.get('password'))
                
                for email in valid_emails:
                    msg['To'] = email
                    server.send_message(msg)
                    del msg['To']
                
                server.quit()
                return True, "Email byl úspěšně odeslán přes externí SMTP"
            else:
                raise local_error
        
    except Exception as e:
        return False, f"Chyba při odesílání emailu: {str(e)}"

def generate_lsa_summary(order):
    """Vygeneruje shrnutí LSA kódů s počty palet"""
    lsa_summary = {}
    
    for item in order.items:
        if item.assigned_lane in (1, 2, 3):  # Pouze přiřazené palety
            if item.lsa not in lsa_summary:
                lsa_summary[item.lsa] = {
                    'count': 0,
                    'total_weight': 0.0,
                    'lengths': {}
                }
            
            lsa_summary[item.lsa]['count'] += 1
            lsa_summary[item.lsa]['total_weight'] += item.weight
            
            # Grupování podle délky
            length_key = f"{item.length_m:.1f}m"
            if length_key not in lsa_summary[item.lsa]['lengths']:
                lsa_summary[item.lsa]['lengths'][length_key] = 0
            lsa_summary[item.lsa]['lengths'][length_key] += 1
    
    return lsa_summary

def generate_carrier_email_body(order):
    """Vygeneruje text emailu pro dopravce"""
    pickup_date = order.pickup_datetime.strftime('%d.%m.%Y') if order.pickup_datetime else 'TBD'
    
    lsa_summary = generate_lsa_summary(order)
    lsa_text = "\n".join([f"LSA {lsa}: {data['count']} palet" for lsa, data in lsa_summary.items()])
    
    return f"""Dobrý den, posílám Vám seznam kódů LSA k naložení v Bad Zwischenahn. Prosím předejte řidiči. Po naložení prosím o zaslání všech dodacích listů na Whatsapp +420778759958, nebo na email. Jakmile zkontroluji správnost naložení, může řidič odjet.

Pokud není ujednáno jinak, vozidlo musí být na místě vykládky druhý den v čase 7-8 hodin. Navazující doprava!!!!! V případě zdržení mě prosím neprodleně informujte.

Datum nakládky: {pickup_date}
Kamion: {order.truck_license_plate or 'TBD'}

LSA kódy k naložení:
{lsa_text}

S pozdravem"""

def generate_loading_email_body(order, additional_text=""):
    """Vygeneruje text emailu pro nakládku s tabulkou"""
    pickup_date = order.pickup_datetime.strftime('%d.%m.%Y') if order.pickup_datetime else 'TBD'
    pickup_time = order.pickup_datetime.strftime('%H:%M') if order.pickup_datetime else 'TBD'
    
    lsa_summary = generate_lsa_summary(order)
    
    # Vytvoření HTML tabulky
    table_rows = []
    for lsa, data in lsa_summary.items():
        lengths_text = ", ".join([f"{length}: {count}ks" for length, count in data['lengths'].items()])
        table_rows.append(f"""
        <tr>
            <td>{lsa}</td>
            <td>{data['count']}</td>
            <td>{lengths_text}</td>
            <td>{data['total_weight']:.1f} kg</td>
        </tr>""")
    
    html_table = f"""
    <table border="1" style="border-collapse: collapse; margin: 20px 0;">
        <thead>
            <tr style="background-color: #f0f0f0;">
                <th style="padding: 8px;">LSA</th>
                <th style="padding: 8px;">Počet palet</th>
                <th style="padding: 8px;">Rozměry</th>
                <th style="padding: 8px;">Váha</th>
            </tr>
        </thead>
        <tbody>
            {''.join(table_rows)}
        </tbody>
    </table>"""
    
    # Textová verze tabulky
    text_table = "LSA\t\tPočet\tRozměry\t\tVáha\n" + "-" * 50 + "\n"
    for lsa, data in lsa_summary.items():
        lengths_text = ", ".join([f"{length}: {count}ks" for length, count in data['lengths'].items()])
        text_table += f"{lsa}\t\t{data['count']}\t{lengths_text}\t\t{data['total_weight']:.1f} kg\n"
    
    text_body = f"""Hello,

{pickup_date} we will load the following LSA
Truck number: {order.truck_license_plate or 'TBD'}
Loading time: {pickup_time} +2 hours

{text_table}"""
    
    html_body = f"""<div style="font-family: Arial, sans-serif;">
    <p>Hello,</p>
    <p><strong>{pickup_date}</strong> we will load the following LSA</p>
    <p><strong>Truck number:</strong> {order.truck_license_plate or 'TBD'}</p>
    <p><strong>Loading time:</strong> {pickup_time} +2 hours</p>
    
    {html_table}"""
    
    if additional_text.strip():
        text_body += f"\n\n{additional_text}"
        html_body += f"\n\n<p><strong>{additional_text}</strong></p>"
    
    html_body += "</div>"
    
    return text_body, html_body

def send_order_email(order):
    """Send order confirmation email"""
    try:
        smtp_config = SETTINGS.get('smtp', {})
        if not smtp_config.get('host') or not smtp_config.get('username'):
            flash('SMTP není nakonfigurováno v settings.json', 'warning')
            return False
            
        recipients = SETTINGS.get('email_recipients', [])
        if not recipients:
            flash('Žádní příjemci nejsou nastaveni v settings.json', 'warning')
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_config.get('from', 'no-reply@example.com')
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f'Hueppe - Objednávka nakládky: {order.name}'
        
        # Create email body
        body = f"""
Dobrý den,

zasíláme objednávku nakládky:

Zakázka: {order.name}
Vytvořeno: {order.created_at.strftime('%d.%m.%Y %H:%M')}
Dopravce: {order.carrier_name or 'neuvedeno'}
Nakládka: {order.pickup_datetime.strftime('%d.%m.%Y %H:%M') if order.pickup_datetime else 'neuvedeno'}
Kamion: {order.truck_license_plate or 'neuvedeno'}

Detaily naleznete v příloze.

S pozdravem,
Hueppe systém
"""
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Create CSV attachment
        csv_data = "lsa,pallet_text,length_m,assigned_lane,weight\n"
        for it in order.items:
            csv_data += f'{it.lsa},{it.pallet_text},{it.length_m},{it.assigned_lane},{it.weight}\n'
        
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(csv_data.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="order_{order.id}.csv"')
        msg.attach(attachment)
        
        # Send email
        server = smtplib.SMTP(smtp_config['host'], smtp_config.get('port', 587))
        if smtp_config.get('use_tls', True):
            server.starttls()
        server.login(smtp_config['username'], smtp_config['password'])
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        flash(f'Chyba při odesílání e-mailu: {str(e)}', 'danger')
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/loading_orders')
def loading_orders():
    # Zobrazí pouze aktivní zakázky (nedelivered)
    orders = Order.query.filter_by(delivered=False).order_by(Order.created_at.desc()).all()
    return render_template('loading_orders.html', orders=orders)

@app.route('/archive')
def archive():
    """Archiv doručených zakázek"""
    delivered_orders = Order.query.filter_by(delivered=True).order_by(Order.created_at.desc()).all()
    return render_template('archive.html', orders=delivered_orders)

@app.route('/create_order', methods=['POST'])
def create_order():
    name = request.form.get('name') or f'Order {datetime.utcnow().isoformat()}'
    order = Order(name=name)
    db.session.add(order)
    db.session.commit()
    return redirect(url_for('order_view', order_id=order.id))

@app.route('/order/<int:order_id>')
def order_view(order_id):
    order = Order.query.get_or_404(order_id)
    # lane totals
    lane_totals = {1:0.0,2:0.0,3:0.0}
    total_weight = 0.0
    for it in order.items:
        if it.assigned_lane in (1,2,3):
            lane_totals[it.assigned_lane] += it.length_m
        total_weight += it.weight
    # compute pallet places
    sum_cols = lane_totals[1] + lane_totals[2] + lane_totals[3]
    pallet_places = 0.0
    if sum_cols > 0:
        pallet_places = round((sum_cols / 3.0) / 0.4, 2)
    price = round(pallet_places * order.price_per_place, 2)
    is_full = price >= order.full_truck_price
    if is_full:
        price = order.full_truck_price
    
    # Generate LSA summary for closed orders
    lsa_summary = generate_lsa_summary(order) if order.closed else {}
    
    return render_template('order.html', order=order, lane_totals=lane_totals, pallet_places=pallet_places, price=price, is_full=is_full, total_weight=total_weight, lsa_summary=lsa_summary)

@app.route('/upload/<int:order_id>', methods=['GET','POST'])
def upload(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Please upload a file', 'warning')
            return redirect(url_for('order_view', order_id=order_id))
        
        # Read file content and calculate hash
        file_content = file.read()
        file_hash = calculate_file_hash(file_content)
        
        # Check if file was already imported
        existing_file = ImportedFile.query.filter_by(file_hash=file_hash).first()
        if existing_file:
            flash(f'Tento soubor už byl importován do zakázky "{existing_file.order.name}" dne {existing_file.uploaded_at.strftime("%d.%m.%Y %H:%M")}', 'warning')
            return redirect(url_for('order_view', order_id=order_id))
        
        # Reset file pointer for pandas
        file.seek(0)
        
        # Read excel with pandas
        try:
            df = pd.read_excel(file, header=None, engine='openpyxl')
        except Exception as e:
            flash(f'Failed to read Excel file: {e}', 'danger')
            return redirect(url_for('order_view', order_id=order_id))
        # We want rows from row index 2 (3rd row) and columns 0..5 (A..F)
        if df.shape[0] < 3:
            flash('Excel does not contain enough rows', 'warning')
            return redirect(url_for('order_view', order_id=order_id))
        df_sub = df.iloc[2:, 0:9].copy()  # Rozšířeno na 9 sloupců (A-I)
        rows_imported = 0
        
        # columns: date, lsa_designation, lsa, pallet_text, qty, weight, length1, length2, length3
        import_order_counter = 0
        for _, row in df_sub.iterrows():
            try:
                date_received = str(row[0]).strip() if not pd.isna(row[0]) else ''    # Sloupec A - datum
                lsa_designation = str(row[1]).strip() if not pd.isna(row[1]) else ''  # Sloupec B
                lsa = str(row[2]).strip() if not pd.isna(row[2]) else ''             # Sloupec C
                pallet_text = str(row[3]).strip() if not pd.isna(row[3]) else ''     # Sloupec D
                qty = int(row[4]) if not pd.isna(row[4]) else 1                      # Sloupec E
                weight = float(row[5]) if not pd.isna(row[5]) else 0.0               # Sloupec F
                
                # Skutečné délky ze sloupců G, H, I (místo parsování z textu)
                length_g = float(row[6]) if not pd.isna(row[6]) and str(row[6]).replace('.','').replace(',','').isdigit() else 0.0  # Sloupec G
                length_h = float(row[7]) if not pd.isna(row[7]) and str(row[7]).replace('.','').replace(',','').isdigit() else 0.0  # Sloupec H  
                length_i = float(row[8]) if not pd.isna(row[8]) and str(row[8]).replace('.','').replace(',','').isdigit() else 0.0  # Sloupec I
                
                # Vybereme první nenulovou délku (G -> H -> I -> fallback na parsing)
                if length_g > 0:
                    length_m = length_g
                elif length_h > 0:
                    length_m = length_h
                elif length_i > 0:
                    length_m = length_i
                else:
                    length_m = parse_length_from_text(pallet_text)  # Fallback na starý způsob
                    
            except Exception:
                continue
            # Expand by qty -> create separate PalletItem rows per pallet
            for i in range(max(1, qty)):
                import_order_counter += 1
                it = PalletItem(
                    order_id=order.id, 
                    date_received=date_received,
                    lsa=lsa, 
                    lsa_designation=lsa_designation,
                    pallet_text=pallet_text, 
                    qty=1, 
                    weight=weight / max(1, qty), 
                    length_m=length_m,
                    import_order=import_order_counter
                )
                db.session.add(it)
                rows_imported += 1
        
        # Save imported file record
        imported_file = ImportedFile(
            filename=file.filename,
            file_hash=file_hash,
            order_id=order.id,
            rows_imported=rows_imported
        )
        db.session.add(imported_file)
        
        db.session.commit()
        
        # Auto-assign pallets to lanes after import
        auto_assign_lanes(order_id)
        
        flash(f'Imported {rows_imported} pallets from "{file.filename}" and auto-assigned to lanes.', 'success')
        return redirect(url_for('order_view', order_id=order_id))
        
        flash('Imported pallets into order (expanded by quantity) and auto-assigned to lanes.', 'success')
        return redirect(url_for('order_view', order_id=order_id))
    return render_template('upload.html', order=order)

@app.route('/assign', methods=['POST'])
def assign():
    item_id = int(request.form.get('item_id'))
    lane = int(request.form.get('lane'))
    item = PalletItem.query.get_or_404(item_id)
    if lane not in (0,1,2,3):
        flash('Invalid lane', 'danger')
    else:
        item.assigned_lane = lane
        db.session.commit()
    return redirect(url_for('order_view', order_id=item.order_id))

@app.route('/auto_assign/<int:order_id>', methods=['POST'])
def auto_assign_route(order_id):
    auto_assign_lanes(order_id)
    flash('Palety byly automaticky přiřazeny do lanes.', 'success')
    return redirect(url_for('order_view', order_id=order_id))

def optimize_lane_assignment(order_id):
    """Optimalizuje přiřazení LSA do lanes podle reálného postupu nakládky"""
    order = Order.query.get_or_404(order_id)
    items = PalletItem.query.filter_by(order_id=order.id).all()
    
    if not items:
        return [0.0, 0.0, 0.0]
    
    # Seskupíme palety podle LSA (postupné nakládání po LSA)
    lsa_groups = {}
    for item in items:
        if item.lsa not in lsa_groups:
            lsa_groups[item.lsa] = []
        lsa_groups[item.lsa].append(item)
    
    # Inicializujeme lanes
    lane_totals = [0.0, 0.0, 0.0]
    max_lane_capacity = 13.6
    
    # Procházíme LSA postupně (jak přijdou na nakládku)
    for lsa, lsa_items in lsa_groups.items():
        # Spočítáme celkovou délku tohoto LSA
        lsa_total_length = sum(item.length_m for item in lsa_items)
        
        # Pokud se celé LSA vejde do jedné lane, najdeme nejlepší místo
        best_single_lane = None
        for i in range(3):
            if lane_totals[i] + lsa_total_length <= max_lane_capacity:
                if best_single_lane is None or lane_totals[i] < lane_totals[best_single_lane]:
                    best_single_lane = i
        
        if best_single_lane is not None:
            # Celé LSA umístíme do jedné lane
            for item in lsa_items:
                item.assigned_lane = best_single_lane + 1
            lane_totals[best_single_lane] += lsa_total_length
        else:
            # LSA se nevejde do žádné lane celé, musíme ho rozdělit
            # Postupně přiřazujeme palety z LSA do lanes (1,2,3,1,2,3...)
            current_lane = 0
            
            for item in lsa_items:
                # Najdeme první lane, kam se paleta vejde
                assigned = False
                for attempt in range(3):  # Zkusíme všechny 3 lanes
                    lane_idx = (current_lane + attempt) % 3
                    if lane_totals[lane_idx] + item.length_m <= max_lane_capacity:
                        item.assigned_lane = lane_idx + 1
                        lane_totals[lane_idx] += item.length_m
                        current_lane = (lane_idx + 1) % 3  # Další paleta začne od následující lane
                        assigned = True
                        break
                
                # Pokud se paleta nevejde nikam, přiřadíme ji do nejméně zatížené lane
                if not assigned:
                    best_lane = lane_totals.index(min(lane_totals))
                    item.assigned_lane = best_lane + 1
                    lane_totals[best_lane] += item.length_m
                    current_lane = (best_lane + 1) % 3
    
    # Finalizační fáze: přesuň palety z přetížených lanes do těch s volným místem
    max_lane_capacity = 13.6
    items_to_move = []
    
    # Najdi přetížené lanes a palety k přesunu
    for lane_idx in range(3):
        if lane_totals[lane_idx] > max_lane_capacity:
            # Najdi palety v této lane (seřazené od nejmenších)
            lane_items = [item for item in items if item.assigned_lane == lane_idx + 1]
            lane_items.sort(key=lambda x: x.length_m)
            
            # Zkus přesunout nejmenší palety
            for item in lane_items:
                if lane_totals[lane_idx] <= max_lane_capacity:
                    break
                    
                # Najdi jinou lane s dostatečným místem
                for target_lane in range(3):
                    if target_lane != lane_idx and lane_totals[target_lane] + item.length_m <= max_lane_capacity:
                        # Přesuň paletu
                        lane_totals[lane_idx] -= item.length_m
                        lane_totals[target_lane] += item.length_m
                        item.assigned_lane = target_lane + 1
                        break
    
    db.session.commit()
    return lane_totals

@app.route('/optimize_lanes/<int:order_id>', methods=['POST'])
def optimize_lanes_route(order_id):
    lane_totals = optimize_lane_assignment(order_id)
    flash(f'Lanes přeorganizovány podle reálného postupu nakládky: Lane 1: {lane_totals[0]:.2f}m, Lane 2: {lane_totals[1]:.2f}m, Lane 3: {lane_totals[2]:.2f}m', 'success')
    return redirect(url_for('order_view', order_id=order_id))

@app.route('/edit_order_name/<int:order_id>', methods=['POST'])
def edit_order_name(order_id):
    order = Order.query.get_or_404(order_id)
    new_name = request.form.get('order_name', '').strip()
    if new_name:
        order.name = new_name
        db.session.commit()
        flash(f'Jméno zakázky změněno na "{new_name}"', 'success')
    return redirect(url_for('order_view', order_id=order_id))

@app.route('/save_for_later/<int:order_id>', methods=['POST'])
def save_for_later(order_id):
    order = Order.query.get_or_404(order_id)
    order.saved_for_later = True
    db.session.commit()
    flash(f'Zakázka "{order.name}" byla uložena na později', 'success')
    return redirect(url_for('index'))

@app.route('/imported_files')
def imported_files():
    files = ImportedFile.query.order_by(ImportedFile.uploaded_at.desc()).all()
    return render_template('imported_files.html', files=files)

def get_or_create_unloaded_order():
    """Získá nebo vytvoří zakázku pro vyřazené z nakládky"""
    unloaded_order = Order.query.filter_by(name='Vyřazené z nakládky', closed=False).first()
    
    if not unloaded_order:
        unloaded_order = Order(
            name='Vyřazené z nakládky',
            capacity_m=SETTINGS.get('default_capacity_m', 13.6),
            price_per_place=SETTINGS.get('price_per_place', 1160.0),
            full_truck_price=SETTINGS.get('full_truck_price', 25600.0),
            saved_for_later=True  # Automaticky uložit na později
        )
        db.session.add(unloaded_order)
        db.session.commit()
    
    return unloaded_order

@app.route('/remove_lsa', methods=['POST'])
def remove_lsa():
    order_id = int(request.form.get('order_id'))
    lsa = request.form.get('lsa')
    order = Order.query.get_or_404(order_id)
    
    # Získej nebo vytvoř zakázku pro nenaložené LSA
    unloaded_order = get_or_create_unloaded_order()
    
    # Přesuň všechny položky s tímto LSA do zakázky nenaložených LSA
    items = PalletItem.query.filter_by(order_id=order.id, lsa=lsa).all()
    count = 0
    for it in items:
        it.order_id = unloaded_order.id
        it.assigned_lane = None  # Reset lane assignment
        count += 1
    
    db.session.commit()
    flash(f'Přesunuto {count} palet s LSA {lsa} do zakázky "Vyřazené z nakládky" (uloženo na později)', 'info')
    return redirect(url_for('order_view', order_id=order_id))

@app.route('/create_test_order', methods=['POST'])
def create_test_order():
    """Vytvoří testovací prázdnou zakázku pro testování delete funkcionality"""
    try:
        # Najdi poslední zakázku pro generování čísla
        last_order = Order.query.order_by(Order.id.desc()).first()
        if last_order and last_order.name.isdigit():
            next_number = int(last_order.name) + 1
        else:
            next_number = 999  # Test číslo
        
        test_order = Order(
            name=f'{next_number:03d}',
            closed=False,
            saved_for_later=False
        )
        
        db.session.add(test_order)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Testovací zakázka "{test_order.name}" byla vytvořena',
            'order_id': test_order.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Chyba při vytváření testovací zakázky: {str(e)}'
        })

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    """Smazání prázdné zakázky (pouze pokud neobsahuje žádné palety)"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Kontrola, zda zakázka neobsahuje palety
        pallet_count = PalletItem.query.filter_by(order_id=order.id).count()
        
        if pallet_count > 0:
            return jsonify({
                'success': False, 
                'error': f'Zakázku nelze smazat - obsahuje {pallet_count} palet. Nejprve přesuňte nebo odstraňte všechny palety.'
            })
        
        # Kontrola, zda se nejedná o speciální zakázky
        if order.name == 'Vyřazené z nakládky':
            return jsonify({
                'success': False, 
                'error': 'Systémovou zakázku "Vyřazené z nakládky" nelze smazat.'
            })
        
        # Kontrola uzavřených zakázek
        if order.closed:
            return jsonify({
                'success': False, 
                'error': 'Uzavřené zakázky nelze mazat. Nejprve zakázku znovu otevřete.'
            })
        
        order_name = order.name
        
        # Smazání importovaných souborů souvisejících se zakázkou
        ImportedFile.query.filter_by(order_id=order.id).delete()
        
        # Smazání zakázky
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Prázdná zakázka "{order_name}" byla úspěšně smazána.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Chyba při mazání zakázky: {str(e)}'
        })

@app.route('/close_order', methods=['POST'])
def close_order():
    order_id = int(request.form.get('order_id'))
    order = Order.query.get_or_404(order_id)
    
    # Get carrier info from form
    carrier_name = request.form.get('carrier_name', '').strip()
    pickup_datetime_str = request.form.get('pickup_datetime', '').strip()
    truck_license_plate = request.form.get('truck_license_plate', '').strip()
    carrier_email = request.form.get('carrier_email', '').strip()
    loading_emails_str = request.form.get('loading_emails', '').strip()
    
    # Parse pickup datetime
    pickup_datetime = None
    if pickup_datetime_str:
        try:
            pickup_datetime = datetime.strptime(pickup_datetime_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Neplatný formát data/času nakládky', 'danger')
            return redirect(url_for('order_view', order_id=order.id))
    
    # compute lane totals
    lane_totals = {1:0.0,2:0.0,3:0.0}
    for it in order.items:
        if it.assigned_lane in (1,2,3):
            lane_totals[it.assigned_lane] += it.length_m
    sum_cols = lane_totals[1] + lane_totals[2] + lane_totals[3]
    
    # Check capacity constraint
    max_lane = max(lane_totals.values())
    if max_lane > order.capacity_m:
        flash(f'Cannot close order: lane length {max_lane:.2f}m exceeds vehicle capacity {order.capacity_m}m. Remove LSA groups until below capacity.', 'danger')
        return redirect(url_for('order_view', order_id=order.id))
    
    # compute pallet places and price and mark closed
    pallet_places = round((sum_cols / 3.0) / 0.4, 2) if sum_cols > 0 else 0.0
    price = round(pallet_places * order.price_per_place, 2)
    if price >= order.full_truck_price:
        price = order.full_truck_price
    
    # Update order with carrier info
    order.closed = True
    order.saved_for_later = False  # Remove from "saved for later" when closing
    order.carrier_name = carrier_name
    order.pickup_datetime = pickup_datetime
    order.truck_license_plate = truck_license_plate
    order.carrier_email = carrier_email if carrier_email else None
    
    # Parse loading emails
    if loading_emails_str:
        loading_emails = [email.strip() for email in loading_emails_str.split(',') if email.strip()]
        order.loading_emails = json.dumps(loading_emails)
    else:
        order.loading_emails = None
    
    db.session.commit()
    
    # Send email notification
    if send_order_email(order):
        flash(f'Order closed and email sent. Dopravce: {carrier_name}, Paletových míst: {pallet_places}, Price: {price} Kč', 'success')
    else:
        flash(f'Order closed (email failed). Dopravce: {carrier_name}, Paletových míst: {pallet_places}, Price: {price} Kč', 'warning')
    
    return redirect(url_for('order_view', order_id=order.id))

@app.route('/export_order/<int:order_id>')
def export_order(order_id):
    order = Order.query.get_or_404(order_id)
    # produce CSV summary
    output = BytesIO()
    rows = ["lsa,pallet_text,length_m,assigned_lane,weight"]
    for it in order.items:
        rows.append(f'{it.lsa},{it.pallet_text},{it.length_m},{it.assigned_lane},{it.weight}')
    output.write('\n'.join(rows).encode('utf-8'))
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f'order_{order.id}.csv', mimetype='text/csv')

@app.route('/print_order/<int:order_id>')
def print_order(order_id):
    order = Order.query.get_or_404(order_id)
    # lane totals
    lane_totals = {1:0.0,2:0.0,3:0.0}
    for it in order.items:
        if it.assigned_lane in (1,2,3):
            lane_totals[it.assigned_lane] += it.length_m
    # compute pallet places
    sum_cols = lane_totals[1] + lane_totals[2] + lane_totals[3]
    pallet_places = 0.0
    if sum_cols > 0:
        pallet_places = round((sum_cols / 3.0) / 0.4, 2)
    price = round(pallet_places * order.price_per_place, 2)
    is_full = price >= order.full_truck_price
    if is_full:
        price = order.full_truck_price
    return render_template('print_order.html', order=order, lane_totals=lane_totals, pallet_places=pallet_places, price=price, is_full=is_full)

@app.route('/settings')
def settings():
    return render_template('settings.html', settings=SETTINGS)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    global SETTINGS
    try:
        SETTINGS['price_per_place'] = float(request.form.get('price_per_place', 1160.0))
        SETTINGS['full_truck_price'] = float(request.form.get('full_truck_price', 25600.0))
        SETTINGS['default_capacity_m'] = float(request.form.get('default_capacity_m', 13.6))
        SETTINGS['alternative_capacity_m'] = float(request.form.get('alternative_capacity_m', 15.4))
        
        # Update email recipients
        recipients_text = request.form.get('email_recipients', '')
        SETTINGS['email_recipients'] = [email.strip() for email in recipients_text.split(',') if email.strip()]
        
        # Update SMTP settings
        SETTINGS['smtp']['host'] = request.form.get('smtp_host', '')
        SETTINGS['smtp']['port'] = int(request.form.get('smtp_port', 587))
        SETTINGS['smtp']['username'] = request.form.get('smtp_username', '')
        SETTINGS['smtp']['password'] = request.form.get('smtp_password', '')
        SETTINGS['smtp']['from'] = request.form.get('smtp_from', '')
        SETTINGS['smtp']['use_tls'] = 'smtp_use_tls' in request.form
        
        # Save to file
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, indent=2, ensure_ascii=False)
            
        flash('Nastavení bylo uloženo', 'success')
    except Exception as e:
        flash(f'Chyba při ukládání nastavení: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/move_pallet_position', methods=['POST'])
def move_pallet_position():
    """API endpoint pro přesun palety s přesnou pozicí"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        new_lane = data.get('new_lane')
        position = data.get('position', -1)  # -1 = na konec
        
        if not item_id or new_lane is None:
            return jsonify({'success': False, 'error': 'Chybí parametry'})
        
        # Najdeme paletu
        item = db.session.get(PalletItem, item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Paleta nenalezena'})
        
        old_lane = item.assigned_lane
        order_id = item.order_id
        
        # Získáme všechny palety v cílovém lane seřazené podle import_order
        target_items = PalletItem.query.filter(
            PalletItem.order_id == order_id,
            PalletItem.assigned_lane == new_lane,
            PalletItem.id != item_id  # Vyloučíme přesouvanou paletu
        ).order_by(PalletItem.import_order).all()
        
        # Aktualizujeme lane
        item.assigned_lane = new_lane
        
        # Přepočítáme import_order pro správné pořadí
        if position == 0 or position == -1:
            # Na začátek nebo na konec
            if position == 0 and target_items:
                # Na začátek - nastavíme nižší import_order než má první paleta
                item.import_order = target_items[0].import_order - 1
            elif target_items:
                # Na konec - nastavíme vyšší import_order než má poslední paleta
                item.import_order = target_items[-1].import_order + 1
            else:
                # Jediná paleta v lane
                item.import_order = 1
        else:
            # Na konkrétní pozici
            if position <= len(target_items):
                if position == 1:
                    # Na začátek
                    item.import_order = target_items[0].import_order - 1 if target_items else 1
                else:
                    # Mezi existující palety
                    prev_item = target_items[position - 2] if position > 1 else None
                    next_item = target_items[position - 1] if position <= len(target_items) else None
                    
                    if prev_item and next_item:
                        # Mezi dvěma paletami
                        item.import_order = (prev_item.import_order + next_item.import_order) // 2
                        if item.import_order == prev_item.import_order:
                            item.import_order = prev_item.import_order + 1
                    elif prev_item:
                        # Za poslední paletu
                        item.import_order = prev_item.import_order + 1
                    else:
                        # Na začátek
                        item.import_order = next_item.import_order - 1 if next_item else 1
            else:
                # Pozice mimo rozsah - přidáme na konec
                item.import_order = target_items[-1].import_order + 1 if target_items else 1
        
        try:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Paleta přesunuta z Lane {old_lane} do Lane {new_lane} na pozici {position}',
                'old_lane': old_lane,
                'new_lane': new_lane,
                'position': position
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Chyba při uložení: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Neočekávaná chyba: {str(e)}'})

@app.route('/move_pallet', methods=['POST'])
def move_pallet():
    """API endpoint pro přesun palety mezi lanes pomocí drag & drop"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        new_lane = data.get('new_lane')
        
        if not item_id or new_lane is None:
            return jsonify({'success': False, 'error': 'Chybí parametry'})
        
        # Najdeme paletu
        item = PalletItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Paleta nenalezena'})
        
        # Aktualizujeme lane
        old_lane = item.assigned_lane
        item.assigned_lane = new_lane
        
        try:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Paleta přesunuta z Lane {old_lane} do Lane {new_lane}',
                'old_lane': old_lane,
                'new_lane': new_lane
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Chyba při uložení: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Neočekávaná chyba: {str(e)}'})

@app.route('/send_carrier_email/<int:order_id>', methods=['POST'])
def send_carrier_email(order_id):
    """Odeslání emailu dopravci s LSA seznamem"""
    order = Order.query.get_or_404(order_id)
    
    if not order.carrier_email:
        return jsonify({'success': False, 'error': 'Email dopravce není vyplněn'})
    
    if not order.pickup_datetime:
        return jsonify({'success': False, 'error': 'Datum nakládky není vyplněn'})
    
    try:
        pickup_date = order.pickup_datetime.strftime('%d.%m.%Y')
        subject = f"Kódy k nakládce ({pickup_date})"
        body = generate_carrier_email_body(order)
        
        # Použití uživatelského emailu jako Reply-To
        success, message = send_email(
            to_emails=order.carrier_email, 
            subject=subject, 
            body=body,
            reply_to=order.user_email
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Email byl odeslán dopravci'})
        else:
            return jsonify({'success': False, 'error': message})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Chyba při odesílání emailu: {str(e)}'})

@app.route('/send_loading_email/<int:order_id>', methods=['POST'])
def send_loading_email(order_id):
    """Odeslání emailu na nakládku s tabulkou LSA"""
    order = Order.query.get_or_404(order_id)
    
    if not order.pickup_datetime:
        return jsonify({'success': False, 'error': 'Datum nakládky není vyplněn'})
    
    try:
        # Získání email adres
        loading_emails = []
        if order.loading_emails:
            try:
                loading_emails = json.loads(order.loading_emails)
            except:
                loading_emails = [order.loading_emails]  # Fallback pro prostý text
        
        # Použití defaultních adres pokud nejsou vyplněny
        if not loading_emails:
            loading_emails = SETTINGS.get('default_loading_emails', [])
        
        if not loading_emails:
            return jsonify({'success': False, 'error': 'Email adresy pro nakládku nejsou vyplněny'})
        
        # Získání dodatečného textu z requestu
        additional_text = request.json.get('additional_text', '') if request.is_json else request.form.get('additional_text', '')
        
        pickup_date = order.pickup_datetime.strftime('%d.%m.%Y')
        subject = f"Aviso ({pickup_date})"
        
        text_body, html_body = generate_loading_email_body(order, additional_text)
        
        # Použití uživatelského emailu jako Reply-To
        success, message = send_email(
            to_emails=loading_emails, 
            subject=subject, 
            body=text_body, 
            html_body=html_body,
            reply_to=order.user_email
        )
        
        if success:
            return jsonify({'success': True, 'message': f'Email byl odeslán na {len(loading_emails)} adres'})
        else:
            return jsonify({'success': False, 'error': message})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Chyba při odesílání emailu: {str(e)}'})

@app.route('/update_order_emails/<int:order_id>', methods=['POST'])
def update_order_emails(order_id):
    """Aktualizace email adres v zakázce"""
    order = Order.query.get_or_404(order_id)
    
    try:
        carrier_email = request.form.get('carrier_email', '').strip()
        loading_emails_text = request.form.get('loading_emails', '').strip()
        user_email = request.form.get('user_email', '').strip()
        
        # Parsování loading emails
        if loading_emails_text:
            loading_emails = [email.strip() for email in loading_emails_text.split(',') if email.strip()]
            order.loading_emails = json.dumps(loading_emails)
        else:
            order.loading_emails = None
        
        order.carrier_email = carrier_email if carrier_email else None
        order.user_email = user_email if user_email else None
        
        db.session.commit()
        flash('Email adresy byly aktualizovány', 'success')
        
    except Exception as e:
        flash(f'Chyba při aktualizaci email adres: {str(e)}', 'danger')
    
    return redirect(url_for('order_view', order_id=order_id))

@app.route('/get_available_lsa/<int:order_id>')
def get_available_lsa(order_id):
    """API endpoint pro získání všech dostupných LSA z jiných zakázek"""
    try:
        current_order = Order.query.get_or_404(order_id)
        
        # Získáme všechny LSA z current zakázky (abychom je vyfiltrovali)
        current_lsa_codes = set(item.lsa for item in current_order.items)
        
        # Najdeme všechny dostupné LSA z různých zdrojů
        available_lsa = []
        
        # 1. LSA z zakázek uložených na později (kromě current)
        saved_orders = Order.query.filter(
            Order.saved_for_later == True,
            Order.id != order_id
        ).all()
        
        for order in saved_orders:
            for item in order.items:
                if item.lsa not in current_lsa_codes:
                    available_lsa.append({
                        'item_id': item.id,
                        'lsa': item.lsa,
                        'lsa_designation': item.lsa_designation,
                        'date_received': item.date_received,
                        'pallet_text': item.pallet_text,
                        'length_m': item.length_m,
                        'weight': item.weight,
                        'source_order_id': order.id,
                        'source_order_name': order.name,
                        'source_type': 'saved_for_later'
                    })
        
        # 2. LSA z neuzavřených zakázek (kromě current a saved_for_later)
        open_orders = Order.query.filter(
            Order.closed == False,
            Order.saved_for_later == False,
            Order.id != order_id
        ).all()
        
        for order in open_orders:
            for item in order.items:
                if item.lsa not in current_lsa_codes and item.assigned_lane == 0:  # Pouze nepřiřazené
                    available_lsa.append({
                        'item_id': item.id,
                        'lsa': item.lsa,
                        'lsa_designation': item.lsa_designation,
                        'date_received': item.date_received,
                        'pallet_text': item.pallet_text,
                        'length_m': item.length_m,
                        'weight': item.weight,
                        'source_order_id': order.id,
                        'source_order_name': order.name,
                        'source_type': 'open_order'
                    })
        
        # Seskupíme podle LSA kódu
        lsa_groups = {}
        for item in available_lsa:
            lsa_code = item['lsa']
            if lsa_code not in lsa_groups:
                lsa_groups[lsa_code] = {
                    'lsa': lsa_code,
                    'lsa_designation': item['lsa_designation'],
                    'count': 0,
                    'total_weight': 0.0,
                    'lengths': {},
                    'sources': set(),
                    'items': []
                }
            
            lsa_groups[lsa_code]['count'] += 1
            lsa_groups[lsa_code]['total_weight'] += item['weight']
            lsa_groups[lsa_code]['sources'].add(f"{item['source_order_name']} ({item['source_type']})")
            lsa_groups[lsa_code]['items'].append(item)
            
            # Grupování podle délky
            length_key = f"{item['length_m']:.1f}m"
            if length_key not in lsa_groups[lsa_code]['lengths']:
                lsa_groups[lsa_code]['lengths'][length_key] = 0
            lsa_groups[lsa_code]['lengths'][length_key] += 1
        
        # Převedeme sources set na list pro JSON serialization
        for lsa_code in lsa_groups:
            lsa_groups[lsa_code]['sources'] = list(lsa_groups[lsa_code]['sources'])
        
        return jsonify({
            'success': True,
            'available_lsa': lsa_groups,
            'total_count': len(available_lsa)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Chyba při načítání dostupných LSA: {str(e)}'})

@app.route('/import_lsa_to_order', methods=['POST'])
def import_lsa_to_order():
    """API endpoint pro import vybraných LSA do zakázky"""
    try:
        data = request.get_json()
        target_order_id = data.get('target_order_id')
        selected_items = data.get('selected_items', [])  # List of item IDs
        
        if not target_order_id or not selected_items:
            return jsonify({'success': False, 'error': 'Chybí parametry'})
        
        target_order = Order.query.get_or_404(target_order_id)
        
        # Najdeme nejvyšší import_order v cílové zakázce
        max_import_order = db.session.query(db.func.max(PalletItem.import_order)).filter_by(order_id=target_order_id).scalar() or 0
        
        imported_count = 0
        imported_lsa = set()
        
        for item_id in selected_items:
            item = PalletItem.query.get(item_id)
            if item and item.order_id != target_order_id:
                # Přesuneme item do cílové zakázky
                old_order_id = item.order_id
                item.order_id = target_order_id
                item.assigned_lane = 0  # Reset lane assignment
                max_import_order += 1
                item.import_order = max_import_order
                
                imported_count += 1
                imported_lsa.add(item.lsa)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Importováno {imported_count} palet z {len(imported_lsa)} LSA',
            'imported_count': imported_count,
            'imported_lsa': list(imported_lsa)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Chyba při importu LSA: {str(e)}'})

@app.route('/test_email')
def test_email():
    """Testovací endpoint pro ověření SMTP nastavení"""
    try:
        # Test základního SMTP připojení
        smtp_config = SETTINGS.get('smtp', {})
        
        test_message = f"""
        Testovací email z Hueppe systému
        
        Tento email byl odeslán pro ověření SMTP nastavení:
        - Server: {smtp_config.get('host')}
        - Port: {smtp_config.get('port')}
        - Username: {smtp_config.get('username')}
        - TLS: {smtp_config.get('use_tls')}
        
        Čas odeslání: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
        """
        
        # Odeslání na adresu odesílatele jako test
        success, message = send_email(
            to_emails=smtp_config.get('from', 'tomeska@european.cz'),
            subject="Test SMTP nastavení - Hueppe systém",
            body=test_message
        )
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Test email byl úspěšně odeslán! {message}'
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'Chyba při odesílání testu: {message}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Obecná chyba: {str(e)}'
        })

@app.route('/update_loading_status/<int:order_id>', methods=['POST'])
def update_loading_status(order_id):
    """Aktualizace stavu náložení, doručení a ZA/OO čísel"""
    order = Order.query.get_or_404(order_id)
    
    try:
        # Aktualizace stavu náložení
        order.is_loaded = 'is_loaded' in request.form
        
        # Aktualizace stavu doručení (pouze pokud je naloženo)
        if order.is_loaded:
            order.delivered = 'delivered' in request.form
        else:
            order.delivered = False  # Pokud není naloženo, nemůže být doručeno
        
        # Aktualizace ZA a OO čísel
        za_number = request.form.get('za_number', '').strip()
        oo_number = request.form.get('oo_number', '').strip()
        
        order.za_number = za_number if za_number else None
        order.oo_number = oo_number if oo_number else None
        
        db.session.commit()
        
        # Určení stavové zprávy
        if order.delivered:
            status_msg = "doručena (přesunuto do archivu)"
        elif order.is_loaded:
            status_msg = "naložena"
        else:
            status_msg = "čeká na naložení"
            
        flash(f'Stav zakázky aktualizován: {status_msg}', 'success')
        
    except Exception as e:
        flash(f'Chyba při aktualizaci stavu: {str(e)}', 'danger')
    
    return redirect(url_for('order_view', order_id=order_id))

@app.route('/print_loading_sheet/<int:order_id>')
def print_loading_sheet(order_id):
    """Tiskový výstup pro náložení na A4"""
    order = Order.query.get_or_404(order_id)
    
    if not order.closed:
        flash('Tiskový výstup je dostupný pouze pro uzavřené zakázky', 'warning')
        return redirect(url_for('order_view', order_id=order_id))
    
    # Vygenerujeme LSA summary pro tisk
    lsa_summary = generate_lsa_summary(order)
    
    # Aktuální čas pro footer
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    
    return render_template('print_loading_sheet.html', 
                         order=order, 
                         lsa_summary=lsa_summary,
                         current_time=current_time)

@app.route('/reopen_order/<int:order_id>', methods=['POST'])
def reopen_order(order_id):
    """Znovu otevře uzavřenou zakázku (např. kvůli zrušení dopravce)"""
    order = Order.query.get_or_404(order_id)
    
    if not order.closed:
        flash('Zakázka již není uzavřená', 'warning')
        return redirect(url_for('order_view', order_id=order.id))
    
    # Reset stavu zakázky
    order.closed = False
    order.is_loaded = False
    order.delivered = False
    
    # Zachováme informace o dopravci pro případnou potřebu
    # ale můžeme je vyčistit podle preference
    clear_carrier_info = request.form.get('clear_carrier_info') == 'on'
    
    if clear_carrier_info:
        order.carrier_name = None
        order.carrier_email = None
        order.truck_license_plate = None
        order.pickup_datetime = None
        # Zachováme loading_emails a user_email pro další použití
    
    # Reset loading statusu všech palet
    for item in order.items:
        item.loaded = False
    
    db.session.commit()
    
    action_text = "a vymazány údaje dopravce" if clear_carrier_info else "se zachováním údajů dopravce"
    flash(f'Zakázka "{order.name}" byla znovu otevřena {action_text}', 'success')
    
    return redirect(url_for('order_view', order_id=order.id))

@app.route('/mark_lsa_loaded', methods=['POST'])
def mark_lsa_loaded():
    """Označení všech palet s konkrétním LSA jako naložené"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        lsa = data.get('lsa')
        loaded = data.get('loaded', True)
        
        if not order_id or not lsa:
            return jsonify({'success': False, 'error': 'Chybí parametry order_id nebo lsa'})
        
        # Najdeme všechny palety s tímto LSA v zakázce
        items = PalletItem.query.filter_by(order_id=order_id, lsa=lsa).all()
        
        if not items:
            return jsonify({'success': False, 'error': f'Nenalezeny žádné palety s LSA {lsa}'})
        
        # Označíme všechny palety
        count = 0
        for item in items:
            item.loaded = loaded
            count += 1
        
        db.session.commit()
        
        status_text = "naložené" if loaded else "nenačítané"
        return jsonify({
            'success': True, 
            'message': f'LSA {lsa} označeno jako {status_text} ({count} palet)',
            'count': count,
            'lsa': lsa,
            'loaded': loaded
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Chyba při aktualizaci: {str(e)}'})

@app.route('/return_unloaded_lsa', methods=['POST'])
def return_unloaded_lsa():
    """Vrácení nenačítaných palet zpět do fronty (vytvoří novou zakázku nebo přidá do existující)"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'success': False, 'error': 'Chybí parametr order_id'})
        
        order = Order.query.get_or_404(order_id)
        
        # Najdeme všechny palety, které nejsou označené jako naložené
        unloaded_items = PalletItem.query.filter_by(order_id=order.id, loaded=False).all()
        
        if not unloaded_items:
            return jsonify({'success': False, 'error': 'Všechny palety jsou označené jako naložené'})
        
        # Získej nebo vytvoř zakázku pro nenaložené LSA
        unloaded_order = get_or_create_unloaded_order()
        
        # Přesuň nenaložené palety do zakázky nenaložených LSA
        count = 0
        lsa_list = []
        for item in unloaded_items:
            item.order_id = unloaded_order.id
            item.assigned_lane = 0  # Reset lane assignment
            item.loaded = False     # Resetovat loading status
            if item.lsa not in lsa_list:
                lsa_list.append(item.lsa)
            count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Přesunuto {count} nenaložených palet do zakázky "Vyřazené z nakládky"',
            'count': count,
            'lsa_codes': lsa_list,
            'unloaded_order_id': unloaded_order.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Chyba při přesunu: {str(e)}'})

@app.route('/get_loading_status/<int:order_id>')
def get_loading_status(order_id):
    """Získání statistik načítání pro konkrétní zakázku"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Seskupení podle LSA
        lsa_status = {}
        for item in order.items:
            if item.assigned_lane in (1, 2, 3):  # Pouze přiřazené palety
                if item.lsa not in lsa_status:
                    lsa_status[item.lsa] = {
                        'total': 0,
                        'loaded': 0,
                        'percentage': 0
                    }
                
                lsa_status[item.lsa]['total'] += 1
                if item.loaded:
                    lsa_status[item.lsa]['loaded'] += 1
        
        # Výpočet procent
        for lsa, status in lsa_status.items():
            if status['total'] > 0:
                status['percentage'] = round((status['loaded'] / status['total']) * 100, 1)
        
        # Celkové statistiky
        total_pallets = sum(status['total'] for status in lsa_status.values())
        loaded_pallets = sum(status['loaded'] for status in lsa_status.values())
        overall_percentage = round((loaded_pallets / total_pallets) * 100, 1) if total_pallets > 0 else 0
        
        return jsonify({
            'success': True,
            'lsa_status': lsa_status,
            'overall': {
                'total': total_pallets,
                'loaded': loaded_pallets,
                'percentage': overall_percentage
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Chyba při načítání statistik: {str(e)}'})

@app.route('/backup_database')
def backup_database():
    """Export celé databáze do JSON souboru"""
    try:
        backup_data = {
            'export_date': datetime.now().isoformat(),
            'version': '1.0',
            'orders': [],
            'pallet_items': [],
            'imported_files': []
        }
        
        # Export zakázek
        orders = Order.query.all()
        for order in orders:
            order_data = {
                'id': order.id,
                'name': order.name,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'closed': order.closed,
                'saved_for_later': order.saved_for_later,
                'capacity_m': order.capacity_m,
                'price_per_place': order.price_per_place,
                'full_truck_price': order.full_truck_price,
                'carrier_name': order.carrier_name,
                'pickup_datetime': order.pickup_datetime.isoformat() if order.pickup_datetime else None,
                'truck_license_plate': order.truck_license_plate,
                'carrier_email': order.carrier_email,
                'loading_emails': order.loading_emails,
                'user_email': order.user_email,
                'is_loaded': order.is_loaded,
                'delivered': order.delivered,
                'za_number': order.za_number,
                'oo_number': order.oo_number
            }
            backup_data['orders'].append(order_data)
        
        # Export palet
        items = PalletItem.query.all()
        for item in items:
            item_data = {
                'id': item.id,
                'order_id': item.order_id,
                'date_received': item.date_received.isoformat() if item.date_received else None,
                'lsa_designation': item.lsa_designation,
                'lsa': item.lsa,
                'name': item.name,
                'length_m': item.length_m,
                'width_m': item.width_m,
                'height_m': item.height_m,
                'weight': item.weight,
                'assigned_lane': item.assigned_lane,
                'import_order': item.import_order
            }
            backup_data['pallet_items'].append(item_data)
        
        # Export importovaných souborů
        files = ImportedFile.query.all()
        for file in files:
            file_data = {
                'id': file.id,
                'filename': file.filename,
                'file_hash': file.file_hash,
                'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None,
                'order_id': file.order_id,
                'rows_imported': file.rows_imported
            }
            backup_data['imported_files'].append(file_data)
        
        # Vytvoření response s JSON souborem
        backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False)
        
        response = make_response(backup_json)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=hueppe_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        return response
        
    except Exception as e:
        flash(f'Chyba při vytváření zálohy: {str(e)}', 'danger')
        return redirect(url_for('settings'))

@app.route('/restore_database', methods=['POST'])
def restore_database():
    """Import databáze z JSON souboru"""
    if 'backup_file' not in request.files:
        flash('Nebyl vybrán žádný soubor', 'danger')
        return redirect(url_for('settings'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('Nebyl vybrán žádný soubor', 'danger')
        return redirect(url_for('settings'))
    
    try:
        # Načtení JSON dat
        backup_data = json.loads(file.read().decode('utf-8'))
        
        # Kontrola formátu
        if 'orders' not in backup_data or 'pallet_items' not in backup_data:
            flash('Nevalidní formát záložního souboru', 'danger')
            return redirect(url_for('settings'))
        
        # Vymazání stávajících dat
        PalletItem.query.delete()
        ImportedFile.query.delete()
        Order.query.delete()
        db.session.commit()
        
        # Import zakázek
        order_id_mapping = {}  # Mapování starých ID na nová
        for order_data in backup_data['orders']:
            order = Order(
                name=order_data['name'],
                created_at=datetime.fromisoformat(order_data['created_at']) if order_data['created_at'] else datetime.utcnow(),
                closed=order_data.get('closed', False),
                saved_for_later=order_data.get('saved_for_later', False),
                capacity_m=order_data.get('capacity_m', 13.6),
                price_per_place=order_data.get('price_per_place', 1160.0),
                full_truck_price=order_data.get('full_truck_price', 25600.0),
                carrier_name=order_data.get('carrier_name'),
                pickup_datetime=datetime.fromisoformat(order_data['pickup_datetime']) if order_data.get('pickup_datetime') else None,
                truck_license_plate=order_data.get('truck_license_plate'),
                carrier_email=order_data.get('carrier_email'),
                loading_emails=order_data.get('loading_emails'),
                user_email=order_data.get('user_email'),
                is_loaded=order_data.get('is_loaded', False),
                delivered=order_data.get('delivered', False),
                za_number=order_data.get('za_number'),
                oo_number=order_data.get('oo_number')
            )
            db.session.add(order)
            db.session.flush()  # Získání nového ID
            order_id_mapping[order_data['id']] = order.id
        
        # Import palet
        for item_data in backup_data['pallet_items']:
            if item_data['order_id'] in order_id_mapping:
                item = PalletItem(
                    order_id=order_id_mapping[item_data['order_id']],
                    date_received=datetime.fromisoformat(item_data['date_received']) if item_data.get('date_received') else None,
                    lsa_designation=item_data.get('lsa_designation'),
                    lsa=item_data.get('lsa'),
                    name=item_data.get('name'),
                    length_m=item_data.get('length_m'),
                    width_m=item_data.get('width_m'),
                    height_m=item_data.get('height_m'),
                    weight=item_data.get('weight', 0.0),
                    assigned_lane=item_data.get('assigned_lane'),
                    import_order=item_data.get('import_order', 0)
                )
                db.session.add(item)
        
        # Import importovaných souborů
        for file_data in backup_data.get('imported_files', []):
            if file_data['order_id'] in order_id_mapping:
                imported_file = ImportedFile(
                    filename=file_data['filename'],
                    file_hash=file_data['file_hash'],
                    uploaded_at=datetime.fromisoformat(file_data['uploaded_at']) if file_data.get('uploaded_at') else datetime.utcnow(),
                    order_id=order_id_mapping[file_data['order_id']],
                    rows_imported=file_data.get('rows_imported', 0)
                )
                db.session.add(imported_file)
        
        db.session.commit()
        
        flash(f'Databáze byla úspěšně obnovena! Importováno: {len(backup_data["orders"])} zakázek, {len(backup_data["pallet_items"])} palet', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Chyba při obnově databáze: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

# LSA Table Management
@app.route('/lsa_tables')
def lsa_tables():
    """Stránka pro správu LSA tabulek"""
    tables = LSATable.query.order_by(LSATable.created_at.desc()).all()
    return render_template('lsa_tables.html', tables=tables)

@app.route('/upload_lsa_table', methods=['POST'])
def upload_lsa_table():
    """Upload nové LSA tabulky"""
    if 'file' not in request.files:
        flash('Nebyl vybrán žádný soubor', 'danger')
        return redirect(url_for('lsa_tables'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nebyl vybrán žádný soubor', 'danger')
        return redirect(url_for('lsa_tables'))
    
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        flash('Podporované formáty: .xlsx, .xls, .csv', 'danger')
        return redirect(url_for('lsa_tables'))
    
    try:
        # Spočítej hash souboru
        file_content = file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        
        # Zkontroluj duplicity
        existing_table = LSATable.query.filter_by(file_hash=file_hash).first()
        if existing_table:
            flash(f'Tabulka s tímto obsahem již existuje: {existing_table.name}', 'warning')
            return redirect(url_for('lsa_tables'))
        
        # Reset file pointer
        file.seek(0)
        
        # Načti data - přeskoč první 2 řádky (hlavička)
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file, skiprows=2)
        else:
            df = pd.read_excel(file, skiprows=2)
        
        # Pro Excel soubory přejmenuj sloupce na A, B, C, D, E pokud mají číselné názvy
        if len(df.columns) >= 5:
            df.columns = [f'{chr(65+i)}' for i in range(len(df.columns))]  # A, B, C, D, E, F, ...
        
        # Kontrola sloupců
        expected_columns = ['A', 'B', 'C', 'D', 'E']
        if not all(col in df.columns for col in expected_columns):
            available_columns = list(df.columns)
            flash(f'Soubor musí mít alespoň 5 sloupců. Nalezené sloupce: {", ".join(available_columns)}. Očekávané: {", ".join(expected_columns)}', 'danger')
            return redirect(url_for('lsa_tables'))
        
        # Vytvoř LSA tabulku
        table_name = request.form.get('table_name', '').strip()
        if not table_name:
            # Automatický název ze souboru
            table_name = os.path.splitext(file.filename)[0]
        
        lsa_table = LSATable(
            name=table_name,
            filename=file.filename,
            file_hash=file_hash,
            rows_count=len(df)
        )
        db.session.add(lsa_table)
        db.session.flush()  # Pro získání ID
        
        # Import dat
        imported_count = 0
        for index, row in df.iterrows():
            # Kontrola prázdných řádků a hlavičkových řádků
            if pd.isna(row['C']) or str(row['C']).strip() == '':
                continue
            
            # Přeskoč řádky s hlavičkami (např. "LSA kód", "Text palety" atd.)
            lsa_code = str(row['C']).strip()
            if lsa_code.lower() in ['lsa kód', 'lsa kod', 'lsa', 'lsa_kod', 'lsa_code']:
                continue
            
            # Přeskoč nečíselné LSA kódy (pravděpodobně hlavičky)
            if not any(char.isdigit() for char in lsa_code):
                continue
                
            try:
                length_val = float(row['E']) if pd.notna(row['E']) and str(row['E']).strip() != '' else 0.0
            except (ValueError, TypeError):
                length_val = 0.0
            
            lsa_item = LSAItem(
                table_id=lsa_table.id,
                date_received=str(row['A']) if pd.notna(row['A']) else '',
                lsa_designation=str(row['B']) if pd.notna(row['B']) else '',
                lsa=str(row['C']) if pd.notna(row['C']) else '',
                pallet_text=str(row['D']) if pd.notna(row['D']) else '',
                length_m=length_val,
                import_order=index + 1,
                used_in_orders='[]'  # Prázdný JSON array
            )
            db.session.add(lsa_item)
            imported_count += 1
        
        # Aktualizuj počet řádků
        lsa_table.rows_count = imported_count
        db.session.commit()
        
        flash(f'LSA tabulka "{table_name}" byla úspěšně importována ({imported_count} řádků)', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Chyba při importu LSA tabulky: {str(e)}', 'danger')
    
    return redirect(url_for('lsa_tables'))

@app.route('/delete_lsa_table/<int:table_id>', methods=['POST'])
def delete_lsa_table(table_id):
    """Smazání LSA tabulky"""
    table = LSATable.query.get_or_404(table_id)
    
    # Zkontroluj, zda nejsou LSA použita v zakázkách
    used_items = LSAItem.query.filter_by(table_id=table_id).filter(LSAItem.used_in_orders != '[]').all()
    if used_items:
        flash(f'Nelze smazat tabulku "{table.name}" - obsahuje LSA použitá v zakázkách', 'danger')
        return redirect(url_for('lsa_tables'))
    
    try:
        # Smaž všechny LSA itemy
        LSAItem.query.filter_by(table_id=table_id).delete()
        # Smaž tabulku
        db.session.delete(table)
        db.session.commit()
        
        flash(f'LSA tabulka "{table.name}" byla smazána', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Chyba při mazání tabulky: {str(e)}', 'danger')
    
    return redirect(url_for('lsa_tables'))

@app.route('/get_lsa_tables_list')
def get_lsa_tables_list():
    """API endpoint pro seznam LSA tabulek"""
    tables = LSATable.query.order_by(LSATable.created_at.desc()).all()
    
    result = {
        'tables': [{
            'id': table.id,
            'name': table.name,
            'filename': table.filename,
            'rows_count': table.rows_count,
            'created_at': table.created_at.isoformat()
        } for table in tables]
    }
    
    return jsonify(result)

@app.route('/get_lsa_table/<int:table_id>')
def get_lsa_table(table_id):
    """API endpoint pro získání obsahu LSA tabulky"""
    table = LSATable.query.get_or_404(table_id)
    items = LSAItem.query.filter_by(table_id=table_id).order_by(LSAItem.import_order).all()
    
    result = {
        'table': {
            'id': table.id,
            'name': table.name,
            'created_at': table.created_at.isoformat(),
            'rows_count': table.rows_count
        },
        'items': [{
            'id': item.id,
            'date_received': item.date_received,
            'lsa_designation': item.lsa_designation,
            'lsa': item.lsa,
            'pallet_text': item.pallet_text,
            'length_m': item.length_m,
            'used_in_orders': json.loads(item.used_in_orders or '[]')
        } for item in items]
    }
    
    return jsonify(result)

@app.route('/import_lsa_from_table', methods=['POST'])
def import_lsa_from_table():
    """Import vybraných LSA z tabulky do zakázky"""
    data = request.get_json()
    order_id = data.get('order_id')
    lsa_item_ids = data.get('lsa_item_ids', [])
    
    if not order_id or not lsa_item_ids:
        return jsonify({'success': False, 'message': 'Chybí parametry'})
    
    order = Order.query.get_or_404(order_id)
    
    try:
        imported_count = 0
        for lsa_item_id in lsa_item_ids:
            lsa_item = LSAItem.query.get(lsa_item_id)
            if not lsa_item:
                continue
            
            # Vytvoř pallet item z LSA item
            pallet_item = PalletItem(
                order_id=order_id,
                lsa_item_id=lsa_item_id,
                date_received=lsa_item.date_received,
                lsa_designation=lsa_item.lsa_designation,
                lsa=lsa_item.lsa,
                pallet_text=lsa_item.pallet_text,
                length_m=lsa_item.length_m,
                import_order=lsa_item.import_order,
                assigned_lane=0,
                loaded=False
            )
            db.session.add(pallet_item)
            
            # Aktualizuj used_in_orders v LSA item
            used_orders = json.loads(lsa_item.used_in_orders or '[]')
            if order_id not in used_orders:
                used_orders.append(order_id)
                lsa_item.used_in_orders = json.dumps(used_orders)
            
            imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Importováno {imported_count} LSA do zakázky "{order.name}"'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Chyba při importu: {str(e)}'
        })

if __name__ == '__main__':
    with app.app_context():
        init_db()
    print("Database initialized successfully!")
    
    # Production vs Development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    if debug_mode:
        print("Starting Flask application in DEVELOPMENT mode on http://127.0.0.1:5000")
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        print("Starting Flask application in PRODUCTION mode")
        app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Initialize database when imported (for WSGI)
try:
    with app.app_context():
        init_db()
    print("Database initialized successfully for WSGI!")
except Exception as e:
    print(f"Database initialization error: {e}")
