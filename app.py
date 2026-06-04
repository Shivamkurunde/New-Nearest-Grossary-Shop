import os
import re
import uuid
import math
import tempfile
import datetime
import csv
import openpyxl
import bson
import logging
import traceback
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import certifi
import mongomock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def get_shop_owner_id(username):
    """Retrieve ShopOwnerID (ObjectId) for a given owner username.
    Returns string ID or None if owner not found or username is None.
    """
    from bson.objectid import ObjectId
    if not username:
        return None
    try:
        owner = users_collection.find_one({'username': username, 'role': 'owner'})
        if not owner:
            logging.warning(f"Shop owner not found for username: {username}")
            return None
        return str(owner['_id'])
    except Exception as e:
        logging.error(f"get_shop_owner_id error for '{username}': {e}")
        return None

app = Flask(__name__)
app.secret_key = 'grocery-secret-key-2026'

@app.before_request
def redirect_to_localhost():
    """
    Browsers strictly block the Geolocation (GPS) popup on http://127.0.0.1
    but allow it on http://localhost. This automatically redirects the user
    so the permission popup works instantly.
    """
    if request.host.startswith('127.0.0.1'):
        return redirect(request.url.replace('127.0.0.1', 'localhost', 1))

# ── Upload config ─────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024   # 16 MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── MongoDB Setup ─────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://dbRurik:Rutik123@cluster0.dfeobzy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=50000)
# client = mongomock.MongoClient() # Using a local in-memory DB so you can run it without Atlas access
db = client.grocery_app
users_collection          = db.users
shops_collection          = db.shops
orders_collection         = db.orders
products_collection       = db.products
uploaded_files_collection = db.uploaded_files
order_items_collection    = db.order_items
notifications_collection  = db.notifications

def create_notification(user_id, shop_id, message, notification_type):
    try:
        from bson.objectid import ObjectId
        obj_id = ObjectId()
        notifications_collection.insert_one({
            '_id':              obj_id,
            'NotificationID':   str(obj_id),
            'UserID':           str(user_id),
            'ShopID':           shop_id,
            'Message':          message,
            'Type':             notification_type,
            'Status':           'unread',
            'CreatedAt':        datetime.datetime.utcnow()
        })
    except Exception as e:
        print(f"Error creating notification: {e}")

# ── Location definitions ──────────────────────────────────────────────────────
LOCATIONS = {
    'nanded_city': {
        'key':         'nanded_city',
        'name':        'Nanded City',
        'description': 'Modern township with multiple grocery stores and supermarkets.',
        'emoji':       '🏙️',
        'lat':         19.1620,
        'lng':         77.3178,
    },
    'waghala': {
        'key':         'waghala',
        'name':        'Waghala, Nanded',
        'description': 'Residential area with trusted local kirana shops and daily essentials.',
        'emoji':       '🏘️',
        'lat':         19.1388,
        'lng':         77.3025,
    },
    'degloor': {
        'key':         'degloor',
        'name':        'Degloor Naka, Nanded',
        'description': 'Busy junction with variety of grocery stores and fresh produce markets.',
        'emoji':       '🛒',
        'lat':         19.1597,
        'lng':         77.3318,
    },
}

# ── Static shop data per location ─────────────────────────────────────────────
SHOPS_BY_LOCATION = {
    'nanded_city': [
        {'id': 1, 'name': 'Jilawar General Store',  'owner': 'Ramesh Jilawar',  'phone': '+91 98765 43210', 'distance': '0.2 km', 'rating': '4.8', 'status': 'Open',   'lat': 19.1622, 'lng': 77.3180, 'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&q=80'},
        {'id': 2, 'name': 'Sharma Kirana Store',    'owner': 'Deepak Sharma',   'phone': '+91 98712 34567', 'distance': '0.5 km', 'rating': '4.5', 'status': 'Open',   'lat': 19.1628, 'lng': 77.3184, 'image': 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=600&q=80'},
        {'id': 3, 'name': 'Patel General Store',    'owner': 'Kamlesh Patel',   'phone': '+91 70123 45678', 'distance': '0.8 km', 'rating': '4.3', 'status': 'Open',   'lat': 19.1634, 'lng': 77.3190, 'image': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=600&q=80'},
        {'id': 4, 'name': 'R.K. Super Mart',        'owner': 'Rakesh Kumar',    'phone': '+91 94523 67890', 'distance': '1.1 km', 'rating': '4.1', 'status': 'Closed', 'lat': 19.1640, 'lng': 77.3196, 'image': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80'},
        {'id': 5, 'name': 'Annapurna Grocery',      'owner': 'Vijay Tiwari',    'phone': '+91 77234 56789', 'distance': '1.4 km', 'rating': '4.0', 'status': 'Open',   'lat': 19.1646, 'lng': 77.3202, 'image': 'https://images.unsplash.com/photo-1519566335946-e6f65f0f4fdf?w=600&q=80'},
    ],
    'waghala': [
        {'id': 6, 'name': 'Lucky Kirana Shop',      'owner': 'Dinesh Gupta',    'phone': '+91 98876 54321', 'distance': '0.4 km', 'rating': '4.6', 'status': 'Open',   'lat': 19.1390, 'lng': 77.3027, 'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&q=80'},
        {'id': 7, 'name': 'New India Mart',         'owner': 'Ashok Singh',     'phone': '+91 91234 56789', 'distance': '0.7 km', 'rating': '4.4', 'status': 'Open',   'lat': 19.1396, 'lng': 77.3033, 'image': 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=600&q=80'},
        {'id': 8, 'name': 'Royal Grocery Store',    'owner': 'Pooja Mehta',     'phone': '+91 87654 32109', 'distance': '1.0 km', 'rating': '4.2', 'status': 'Open',   'lat': 19.1402, 'lng': 77.3039, 'image': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=600&q=80'},
        {'id': 9, 'name': 'Jain Super Mart',        'owner': 'Suresh Jain',     'phone': '+91 76543 21098', 'distance': '1.3 km', 'rating': '4.0', 'status': 'Closed', 'lat': 19.1408, 'lng': 77.3045, 'image': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80'},
        {'id': 10, 'name': 'Balaji Kirana Store',    'owner': 'Mahesh Agrawal',  'phone': '+91 65432 10987', 'distance': '1.6 km', 'rating': '3.9', 'status': 'Open',   'lat': 19.1414, 'lng': 77.3051, 'image': 'https://images.unsplash.com/photo-1519566335946-e6f65f0f4fdf?w=600&q=80'},
    ],
    'degloor': [
        {'id': 11, 'name': 'Balaji Kirana Bhandar',  'owner': 'Gopal Yadav',     'phone': '+91 99887 76655', 'distance': '0.2 km', 'rating': '4.8', 'status': 'Open',   'lat': 19.1599, 'lng': 77.3320, 'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&q=80'},
        {'id': 12, 'name': 'Ganesh General Mart',    'owner': 'Naresh Chouhan',  'phone': '+91 88776 65544', 'distance': '0.5 km', 'rating': '4.5', 'status': 'Open',   'lat': 19.1605, 'lng': 77.3326, 'image': 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=600&q=80'},
        {'id': 13, 'name': 'City Super Store',       'owner': 'Bhavna Joshi',    'phone': '+91 77665 54433', 'distance': '0.8 km', 'rating': '4.3', 'status': 'Open',   'lat': 19.1611, 'lng': 77.3332, 'image': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=600&q=80'},
        {'id': 14, 'name': 'Krishna Mart',           'owner': 'Arun Krishna',    'phone': '+91 66554 43322', 'distance': '1.1 km', 'rating': '4.1', 'status': 'Closed', 'lat': 19.1617, 'lng': 77.3338, 'image': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80'},
        {'id': 15, 'name': 'Shree Nagar Grocery',    'owner': 'Priya Desai',     'phone': '+91 55443 32211', 'distance': '1.4 km', 'rating': '4.0', 'status': 'Open',   'lat': 19.1623, 'lng': 77.3344, 'image': 'https://images.unsplash.com/photo-1519566335946-e6f65f0f4fdf?w=600&q=80'},
    ],
}

# ── All shops flat list (for MongoDB seed & items lookup) ─────────────────────
ALL_SHOPS = [s for shops in SHOPS_BY_LOCATION.values() for s in shops]

# ── Seed fixed owner accounts ─────────────────────────────────────────────────
def seed_fixed_owners():
    for shop in ALL_SHOPS:
        full_name = shop.get('owner', '')
        if not full_name: continue
        username = full_name.split()[0].lower()
        if not users_collection.find_one({'username': username}):
            users_collection.insert_one({
                'username': username, 'email': f"{username}@example.com",
                'password': generate_password_hash('Pass@123'), 'role': 'owner',
                'delivery_name': full_name, 'delivery_location': shop.get('name', ''),
                'delivery_pincode': '', 'mobile': shop.get('phone', '')
            })

seed_fixed_owners()

# ── Product image map (verified Unsplash URLs) ────────────────────────────────
_PRODUCT_IMAGES = {
    'toor_dal':      'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=400&q=80',
    'basmati_rice':  'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&q=80',
    'mustard_oil':   'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&q=80',
    'milk':          'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&q=80',
    'atta':          'https://images.unsplash.com/photo-1626016120401-8e44bc1d73bc?w=400&q=80',
    'sugar':         'https://images.unsplash.com/photo-1559181567-c3190ca9be2b?w=400&q=80',
    'eggs':          'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400&q=80',
    'butter':        'https://images.unsplash.com/photo-1589985270958-bf087b5beb77?w=400&q=80',
    'onion':         'https://images.unsplash.com/photo-1518977956812-cd3dbadaaf31?w=400&q=80',
    'potato':        'https://images.unsplash.com/photo-1590165482129-1b8b27698780?w=400&q=80',
    'sunflower_oil': 'https://images.unsplash.com/photo-1620706857370-e1b9770e8bb1?w=400&q=80',
    'salt':          'https://images.unsplash.com/photo-1518110925495-5fe2fda0442c?w=400&q=80',
}

def url_image(key):
    return _PRODUCT_IMAGES.get(key, '/static/images/products/placeholder.png')

# ── Product catalogue ─────────────────────────────────────────────────────────
ITEMS = [
    {
        'id': 1,  'name': 'Toor Dal',
        'description': 'Split pigeon peas — rich in protein & fibre. Daily staple of every Indian kitchen.',
        'price': 140, 'unit': '/kg', 'category': 'Pulses',
        'image': url_image('toor_dal'),
        'badge': 'Organic', 'badge_color': '#2e7d32', 'stock': 'In Stock',
    },
    {
        'id': 2,  'name': 'Basmati Rice',
        'description': 'Premium long-grain aromatic basmati rice. Perfect for biryanis & pulao.',
        'price': 120, 'unit': '/kg', 'category': 'Grains',
        'image': url_image('basmati_rice'),
        'badge': 'Best Seller', 'badge_color': '#e65100', 'stock': 'In Stock',
    },
    {
        'id': 3,  'name': 'Mustard Oil',
        'description': 'Pure cold-pressed mustard oil (Kachi Ghani). Ideal for cooking & frying.',
        'price': 180, 'unit': '/litre', 'category': 'Oils',
        'image': url_image('mustard_oil'),
        'badge': 'Pure', 'badge_color': '#f9a825', 'stock': 'In Stock',
    },
    {
        'id': 4,  'name': 'Full Cream Milk',
        'description': 'Fresh full-cream milk delivered daily from trusted local farms.',
        'price': 60,  'unit': '/litre', 'category': 'Dairy',
        'image': url_image('milk'),
        'badge': 'Daily Fresh', 'badge_color': '#1565c0', 'stock': 'In Stock',
    },
    {
        'id': 5,  'name': 'Wheat Flour (Atta)',
        'description': 'Fine whole wheat atta. Makes soft fluffy rotis every time.',
        'price': 55,  'unit': '/kg', 'category': 'Grains',
        'image': url_image('atta'),
        'badge': None, 'badge_color': None, 'stock': 'In Stock',
    },
    {
        'id': 6,  'name': 'Sugar',
        'description': 'Premium refined white sugar. Perfect for cooking, tea & baking.',
        'price': 45,  'unit': '/kg', 'category': 'Essentials',
        'image': url_image('sugar'),
        'badge': None, 'badge_color': None, 'stock': 'In Stock',
    },
    {
        'id': 7,  'name': 'Eggs (12 Pack)',
        'description': 'Farm-fresh Grade-A eggs. Rich in protein and essential vitamins.',
        'price': 90,  'unit': '/dozen', 'category': 'Dairy',
        'image': url_image('eggs'),
        'badge': 'Farm Fresh', 'badge_color': '#f06292', 'stock': 'In Stock',
    },
    {
        'id': 8,  'name': 'Amul Butter',
        'description': 'Pasteurised salted table butter — the classic Indian kitchen staple.',
        'price': 55,  'unit': '/100g', 'category': 'Dairy',
        'image': url_image('butter'),
        'badge': 'Popular', 'badge_color': '#6a1b9a', 'stock': 'Low Stock',
    },
    {
        'id': 9,  'name': 'Onion',
        'description': 'Fresh locally-sourced onions. Essential for every Indian dish.',
        'price': 40,  'unit': '/kg', 'category': 'Vegetables',
        'image': url_image('onion'),
        'badge': None, 'badge_color': None, 'stock': 'In Stock',
    },
    {
        'id': 10, 'name': 'Potato',
        'description': 'Farm-fresh potatoes, perfect for curries, fries and snacks.',
        'price': 30,  'unit': '/kg', 'category': 'Vegetables',
        'image': url_image('potato'),
        'badge': None, 'badge_color': None, 'stock': 'In Stock',
    },
    {
        'id': 11, 'name': 'Sunflower Oil',
        'description': 'Light refined sunflower oil — ideal for everyday cooking.',
        'price': 150, 'unit': '/litre', 'category': 'Oils',
        'image': url_image('sunflower_oil'),
        'badge': None, 'badge_color': None, 'stock': 'In Stock',
    },
    {
        'id': 12, 'name': 'Salt',
        'description': 'Iodised table salt — enriched with essential minerals.',
        'price': 20,  'unit': '/kg', 'category': 'Essentials',
        'image': url_image('salt'),
        'badge': None, 'badge_color': None, 'stock': 'In Stock',
    },
]



# ── Haversine distance helper ─────────────────────────────────────────────────
def haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ── OCR helpers ───────────────────────────────────────────────────────────────
def ocr_image(path):
    """Extract text from an image file using Gemini Vision API."""
    logging.info(f"[OCR] Starting Gemini Vision OCR on image: {path}")
    try:
        import google.generativeai as genai
        from PIL import Image
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logging.error("[OCR] GEMINI_API_KEY not found in environment.")
            return ''
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        with Image.open(path) as img:
            prompt = (
                "You are an AI grocery list reader. Read the text from this image exactly as written. "
                "Each item should be on a new line. "
                "If there are no grocery items in the image, return nothing (an empty string). "
                "Only return the raw text, do not use markdown formatting."
            )
            response = model.generate_content([prompt, img])
            text = response.text.strip()
            
        logging.info(f"[OCR] Extracted text ({len(text)} chars): {repr(text[:200])}")
        return text
    except Exception as e:
        logging.error(f"[OCR] Gemini Image OCR failed: {e}")
        return ''

def ocr_pdf(path):
    """Extract text from a PDF file using pdfplumber, fallback to PyPDF2."""
    logging.info(f"[PDF] Starting PDF text extraction: {path}")
    text = ''
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                text += page_text + '\n'
        logging.info(f"[PDF] pdfplumber extracted {len(text)} chars")
        return text
    except ImportError:
        logging.warning("[PDF] pdfplumber not installed, trying PyPDF2")
    except Exception as e:
        logging.warning(f"[PDF] pdfplumber failed: {e}, trying PyPDF2")
    try:
        import PyPDF2
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += (page.extract_text() or '') + '\n'
        logging.info(f"[PDF] PyPDF2 extracted {len(text)} chars")
        return text
    except Exception as e:
        logging.error(f"[PDF] PyPDF2 also failed: {e}")
        return ''

def parse_grocery_items(raw_text):
    """
    Parse raw OCR text into a clean deduplicated list of title-cased item names.
    Handles lines like "Toor Dal – 2kg", "rice 5 kg", "MILK - 2 packets".
    """
    lines  = raw_text.splitlines()
    seen   = set()
    result = []
    # Remove quantity / symbols / digits, keep only the item name part
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Strip trailing quantity info: "– 2kg", "- 5kg", "2 packets", etc.
        name = re.split(r'[-–—:|/\\]|\d', line)[0].strip()
        name = re.sub(r'[^a-zA-Z\s\(\)]', '', name).strip()
        if len(name) < 2:
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            result.append(name.title())
    return result

def match_items_in_catalogue(names):
    """Return (found_items, missing_names) by fuzzy-matching against ITEMS."""
    found   = []
    missing = []
    catalogue_lower = {item['name'].lower(): item for item in ITEMS}
    for name in names:
        name_l = name.lower()
        matched = None
        # Exact match
        if name_l in catalogue_lower:
            matched = catalogue_lower[name_l]
        else:
            # Partial / word-level match
            for cat_name, cat_item in catalogue_lower.items():
                name_words = set(name_l.split())
                cat_words  = set(cat_name.split())
                if name_words & cat_words:
                    matched = cat_item
                    break
        if matched:
            found.append(matched)
        else:
            missing.append(name)
    return found, missing

# ── New File Parsers for Upload List feature ──────────────────────────────────
def parse_single_line(line):
    # Clean starting/ending pipe/whitespace first (handles markdown table boundaries)
    line = line.strip('| \t')
    if not line:
        return None
        
    # Ignore horizontal separators like "|---|---|", "----+----", or similar divider lines
    if re.match(r'^[\s|\-\+\:=]+$', line):
        return None
    
    # Ignore table header rows
    lower_line = line.lower()
    if ("item" in lower_line or "product" in lower_line) and ("qty" in lower_line or "quantity" in lower_line):
        return None
    if lower_line in ["shopping list", "list", "items", "quantity", "product", "item name", "qty"]:
        return None

    # Strip bullets/list numbers e.g. •, -, *, +, or "1.", "2)", "1 -" at the start
    # But do NOT strip numbers if it's the quantity (e.g. "5kg Rice" or "2 Milk")
    # A list indicator usually is followed by a dot, parenthesis, space, or separator: e.g. "1. ", "1) ", "• ", "- "
    line = re.sub(r'^[•\-\*\+]\s*', '', line).strip()
    line = re.sub(r'^\d+[\.\)\-]\s*', '', line).strip()
    if not line:
        return None

    # Automatic Units Regex
    units_rx = r'(?:kg|g|litre|ltr|l|ml|pack(?:et)?s?|pkts?|dozen|pcs|pieces?)'

    # Format 6: Milk (2), Bread (3), Rice (5kg)
    paren_match = re.search(r'\(\s*(\d+(?:\.\d+)?\s*' + units_rx + r'?)\s*\)', line, re.IGNORECASE)
    if paren_match:
        qty = paren_match.group(1).strip()
        name = line[:paren_match.start()].strip()
        name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', name).strip()
        if len(name) >= 2:
            return {'name': name, 'qty': qty}

    # Format 5: Milk x2, Bread x 3, Rice x5kg
    # Case 1: Trailing x with space before: Milk x2, Rice x 5kg
    x_match = re.search(r'\s+[xX]\s*(\d+(?:\.\d+)?\s*' + units_rx + r'?)$', line, re.IGNORECASE)
    if x_match:
        qty = x_match.group(1).strip()
        name = line[:x_match.start()].strip()
        name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', name).strip()
        if len(name) >= 2:
            return {'name': name, 'qty': qty}
            
    # Case 2: Trailing x without space before: Milkx2, Rice x5kg (but with space)
    x_nospace_match = re.search(r'([a-zA-Z\s]+)[xX](\d+(?:\.\d+)?\s*' + units_rx + r'?)$', line, re.IGNORECASE)
    if x_nospace_match:
        name = x_nospace_match.group(1).strip()
        qty = x_nospace_match.group(2).strip()
        name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', name).strip()
        if len(name) >= 2:
            return {'name': name, 'qty': qty}

    # Formats 1 & 4: Separators trailing: Milk - 2, Milk: 2, Bread:3, Rice - 5kg
    sep_match = re.search(r'[:=|–—\-]\s*(\d+(?:\.\d+)?\s*' + units_rx + r'?)$', line, re.IGNORECASE)
    if sep_match:
        qty = sep_match.group(1).strip()
        name = line[:sep_match.start()].strip()
        name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', name).strip()
        if len(name) >= 2:
            return {'name': name, 'qty': qty}

    # Format 3: Leading quantity: 2 Milk, 3 Bread, 5kg Rice, 2.5L Milk
    lead_qty_match = re.match(r'^(\d+(?:\.\d+)?\s*' + units_rx + r'?)\s+(.+)$', line, re.IGNORECASE)
    if lead_qty_match:
        qty = lead_qty_match.group(1).strip()
        name = lead_qty_match.group(2).strip()
        name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', name).strip()
        if len(name) >= 2:
            return {'name': name, 'qty': qty}

    # Formats 2 & 8: Trailing quantity with spaces: Milk 2, Bread 3, Rice 5kg, Milk       2
    trail_qty_match = re.search(r'\s+(\d+(?:\.\d+)?\s*' + units_rx + r'?)$', line, re.IGNORECASE)
    if trail_qty_match:
        qty = trail_qty_match.group(1).strip()
        name = line[:trail_qty_match.start()].strip()
        name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', name).strip()
        if len(name) >= 2:
            return {'name': name, 'qty': qty}

    # Fallback: No quantity found, default quantity = 1
    clean_name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9\(\)]+$', '', line).strip()
    if len(clean_name) >= 2:
        return {'name': clean_name, 'qty': '1'}
    
    return None

def parse_text_lines(text):
    items = []
    if not text:
        return items
    for line in text.splitlines():
        parsed = parse_single_line(line)
        if parsed:
            if parsed['name'].lower() in ['item name', 'product name', 'quantity', 'item', 'product', 'list', 'shopping list']:
                continue
            items.append(parsed)
    return items

def parse_pdf_list(path):
    text = ocr_pdf(path) or ''
    logging.info(f"[PARSE-PDF] Text for parsing ({len(text)} chars): {repr(text[:300])}")
    return parse_text_lines(text)

def parse_csv_list(path):
    items = []
    try:
        with open(path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                if len(row) >= 2:
                    name = str(row[0]).strip()
                    qty = str(row[1]).strip()
                    if name and name.lower() not in ['product', 'item', 'name', 'item name', 'product name']:
                        items.append({'name': name, 'qty': qty})
                elif len(row) == 1:
                    line = str(row[0]).strip()
                    if line:
                        parsed = parse_single_line(line)
                        if parsed:
                            items.append(parsed)
    except Exception:
        pass
    return items

def parse_excel_list(path):
    items = []
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        sheet = wb.active
        for row in sheet.iter_rows(values_only=True):
            if not row:
                continue
            row_vals = [str(x).strip() for x in row if x is not None]
            if not row_vals:
                continue
            if len(row_vals) >= 2:
                name = row_vals[0]
                qty = row_vals[1]
                if name.lower() not in ['product', 'item', 'name', 'item name', 'product name']:
                    items.append({'name': name, 'qty': qty})
            elif len(row_vals) == 1:
                line = row_vals[0]
                parsed = parse_single_line(line)
                if parsed:
                    items.append(parsed)
    except Exception:
        pass
    return items

def parse_txt_list(path):
    text = ''
    try:
        with open(path, mode='r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        try:
            with open(path, mode='r', encoding='latin-1') as f:
                text = f.read()
        except Exception:
            pass
    return parse_text_lines(text)


# ── Seed shops if DB is empty ─────────────────────────────────────────────────
try:
    if shops_collection.count_documents({}) == 0:
        shops_collection.insert_many(ALL_SHOPS)
except Exception:
    pass

# ── Before-request ────────────────────────────────────────────────────────────
@app.before_request
def make_session_permanent():
    session.permanent = True

# ── Home ──────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    if 'user' in session and session['user'].get('role') == 'owner':
        return redirect(url_for('owner_dashboard'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role             = 'customer'  # Public registration is strictly restricted to customers
        username         = request.form.get('username', '').strip()
        email            = request.form.get('email', '').strip()
        password         = request.form.get('password', '')
        confirm_password = request.form.get('confirmPassword', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        if users_collection.find_one({'email': email}):
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        if users_collection.find_one({'username': username}):
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))

        users_collection.insert_one({
            'username': username, 'email': email,
            'password': generate_password_hash(password),
            'role': role,
            'delivery_name': '', 'delivery_location': '',
            'delivery_pincode': '', 'mobile': ''
        })

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')

        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            role = user.get('role', 'customer')
            session['user'] = {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'role': role
            }
            flash(f'Welcome, {username}!', 'success')
            return redirect(url_for('owner_dashboard') if role == 'owner' else url_for('profile'))
        flash('Invalid credentials.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# ── Profile ───────────────────────────────────────────────────────────────────
@app.route('/api/pincode/<pin>', methods=['GET'])
def api_pincode(pin):
    import urllib.request
    import json
    import ssl
    try:
        url = f'https://api.postalpincode.in/pincode/{pin}'
        
        # Bypass SSL verification because the API's certificate has expired
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data = json.loads(response.read().decode())
        return jsonify(data)
    except Exception as e:
        return jsonify([{'Status': 'Error', 'Message': str(e)}]), 500

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    from bson.objectid import ObjectId
    user = users_collection.find_one({'_id': ObjectId(session['user']['id'])})

    if request.method == 'POST':
        new_username      = request.form.get('username', user.get('username')).strip()
        new_email         = request.form.get('email', user.get('email')).strip()
        delivery_name     = request.form.get('delivery_name', '').strip()
        mobile            = request.form.get('mobile', '').strip()
        delivery_pincode  = request.form.get('delivery_pincode', '').strip()
        delivery_state    = request.form.get('delivery_state', '').strip()
        delivery_district = request.form.get('delivery_district', '').strip()
        delivery_taluka   = request.form.get('delivery_taluka', '').strip()
        delivery_village  = request.form.get('delivery_village', '').strip()
        delivery_street   = request.form.get('delivery_street', '').strip()

        if len(delivery_name) < 3:
            flash('Full Name must be at least 3 characters.', 'error')
            return redirect(url_for('profile'))
        if not re.match(r'^\d{10}$', mobile):
            flash('Mobile number must be exactly 10 digits.', 'error')
            return redirect(url_for('profile'))
        if len(delivery_pincode) != 6:
            flash('Pincode must be exactly 6 digits.', 'error')
            return redirect(url_for('profile'))
        if not all([delivery_state, delivery_district, delivery_village, delivery_street]):
            flash('Please fill out all address fields.', 'error')
            return redirect(url_for('profile'))

        duplicate = users_collection.find_one({
            '$or': [{'username': new_username}, {'email': new_email}],
            '_id': {'$ne': ObjectId(session['user']['id'])}
        })
        if duplicate:
            flash('Username or Email already taken by another account.', 'error')
            return redirect(url_for('profile'))

        users_collection.update_one(
            {'_id': ObjectId(session['user']['id'])},
            {'$set': {'username': new_username, 'email': new_email,
                      'delivery_name': delivery_name,
                      'mobile': mobile,
                      'delivery_pincode': delivery_pincode,
                      'delivery_state': delivery_state,
                      'delivery_district': delivery_district,
                      'delivery_taluka': delivery_taluka,
                      'delivery_village': delivery_village,
                      'delivery_street': delivery_street}}
        )
        session['user'] = {
            'id': session['user']['id'], 'username': new_username,
            'email': new_email, 'role': session['user']['role']
        }
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', current_user=user)


# ── Shop Status Toggle ────────────────────────────────────────────────────────
@app.route('/api/toggle_shop_status', methods=['POST'])
def toggle_shop_status():
    if 'user' not in session or session['user'].get('role') != 'owner':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    username = session['user']['username']
    
    # Update the global in-memory ALL_SHOPS so the customer-facing pages update instantly
    shop_ref = None
    for s in ALL_SHOPS:
        if s.get('owner', '').lower().startswith(username):
            shop_ref = s
            break
            
    if not shop_ref:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
        
    new_status = 'Closed' if shop_ref.get('status') == 'Open' else 'Open'
    shop_ref['status'] = new_status
    
    # Persist to database so the owner dashboard loads the correct state next time
    shops_collection.update_one(
        {'owner': shop_ref['owner']},
        {'$set': {'status': new_status, 'name': shop_ref['name'], 'rating': shop_ref['rating']}},
        upsert=True
    )
    
    return jsonify({'success': True, 'new_status': new_status})

# ── Owner dashboard ───────────────────────────────────────────────────────────
@app.route('/owner_dashboard')
def owner_dashboard():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))
    if session['user']['role'] != 'owner':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('home'))

    # Retrieve the logged‑in owner user
    username = session['user']['username']
    owner_user = users_collection.find_one({'username': username, 'role': 'owner'})
    if not owner_user:
        flash('Owner not found.', 'error')
        return redirect(url_for('home'))
    owner_id = str(owner_user['_id'])

    # Fetch shop details for display
    shop = shops_collection.find_one({'owner': username}) or {'name': 'No Shop Assigned', 'owner': username, 'status': 'Closed', 'rating': '0.0'}

    # Retrieve all orders linked to this ShopOwnerID (both uploaded and standard)
    orders_raw = list(orders_collection.find({'ShopOwnerID': owner_id}).sort('timestamp', -1))
    orders = []
    uploaded_orders = []
    for o in orders_raw:
        o['_id'] = str(o['_id'])
        if 'timestamp' in o and hasattr(o['timestamp'], 'strftime'):
            o['timestamp_str'] = o['timestamp'].strftime('%d %b %Y, %I:%M %p')
        else:
            o['timestamp_str'] = 'N/A'
        if o.get('is_uploaded'):
            uploaded_orders.append(o)
        else:
            orders.append(o)

    # Compute statistics across all orders
    all_orders = orders + uploaded_orders
    total_rev = sum(o.get('total', 0) for o in all_orders)
    pending_count = sum(1 for o in all_orders if o.get('status') in ['Pending', 'placed'])
    delivered_count = sum(1 for o in all_orders if o.get('status') == 'Delivered')
    return render_template('owner_dashboard.html', shop=shop, orders=orders,
                           uploaded_orders=uploaded_orders,
                           total_rev=total_rev, pending_count=pending_count,
                           delivered_count=delivered_count)


# ── Location selection ────────────────────────────────────────────────────────
@app.route('/location')
def location():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    # Build location cards with shop counts
    location_cards = []
    for key, loc in LOCATIONS.items():
        shop_count = len(SHOPS_BY_LOCATION.get(key, []))
        open_count = sum(1 for s in SHOPS_BY_LOCATION.get(key, []) if s['status'] == 'Open')
        location_cards.append({
            **loc,
            'shop_count': shop_count,
            'open_count': open_count,
            'url':        url_for('shops', loc=key),
        })

    return render_template('location.html', location_cards=location_cards)

# ── Shops listing ─────────────────────────────────────────────────────────────
@app.route('/all_shops')
def all_shops():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    # Collect ALL shops from all locations
    all_shop_list = []
    for loc, shops in SHOPS_BY_LOCATION.items():
        for s in shops:
            s_copy = dict(s)
            s_copy['location_key'] = loc
            all_shop_list.append(s_copy)

    # Get user GPS (defaulting to Nanded center if missing)
    try:
        user_lat = float(request.args.get('lat', 19.1383))
        user_lng = float(request.args.get('lng', 77.3210))
    except (ValueError, TypeError):
        user_lat = 19.1383
        user_lng = 77.3210

    # Calculate distance and sort
    enriched = []
    for shop in all_shop_list:
        dist_km = haversine(user_lat, user_lng, shop.get('lat', user_lat), shop.get('lng', user_lng))
        enriched.append({**shop, 'distance': f'{dist_km:.1f} km', 'dist_raw': dist_km})
    
    enriched.sort(key=lambda s: s['dist_raw'])

    return render_template('all_shops.html', shops=enriched)

@app.route('/shops')
def shops():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    loc = request.args.get('loc', '').lower().strip()
    if not loc or loc not in LOCATIONS or loc not in SHOPS_BY_LOCATION:
        flash('⚠ No shops available for this area.', 'error')
        return redirect(url_for('location'))

    shop_list    = SHOPS_BY_LOCATION.get(loc, [])
    if not shop_list:
        flash('⚠ No shops available for this area.', 'error')
        return redirect(url_for('location'))

    location_info = LOCATIONS[loc]

    # Try to get user GPS from query params (sent by JS before redirect)
    try:
        user_lat = float(request.args.get('lat', location_info['lat']))
        user_lng = float(request.args.get('lng', location_info['lng']))
    except (ValueError, TypeError):
        user_lat = location_info['lat']
        user_lng = location_info['lng']

    # Calculate distance and sort
    enriched = []
    for shop in shop_list:
        dist_km = haversine(user_lat, user_lng, shop.get('lat', user_lat), shop.get('lng', user_lng))
        enriched.append({**shop, 'distance': f'{dist_km:.1f} km', 'dist_raw': dist_km})
    enriched.sort(key=lambda s: s['dist_raw'])

    return render_template('shops.html',
                           shops=enriched,
                           location=location_info['name'],
                           location_key=loc,
                           location_info=location_info)

# ── Items / product view ──────────────────────────────────────────────────────
@app.route('/items')
def items():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    shop_id = request.args.get('shop_id', '1')
    loc     = request.args.get('loc', '').lower().strip()

    if not loc or loc not in SHOPS_BY_LOCATION:
        loc = next(iter(SHOPS_BY_LOCATION.keys()), 'nanded_city')

    try:
        shop = shops_collection.find_one({'id': int(shop_id)})
    except (ValueError, TypeError):
        shop = None

    if not shop:
        # Fallback: search by loc
        shop_list = SHOPS_BY_LOCATION.get(loc, next(iter(SHOPS_BY_LOCATION.values()), []))
        shop = shop_list[0] if shop_list else (ALL_SHOPS[0] if ALL_SHOPS else None)

    # Convert ObjectId to str if present
    if shop and '_id' in shop:
        shop = {k: (str(v) if k == '_id' else v) for k, v in shop.items()}

    return render_template('items.html', items=ITEMS, shop=shop, loc=loc)

# ── Place order (API) ─────────────────────────────────────────────────────────
@app.route('/api/place_order', methods=['POST'])
def place_order():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        data = request.json
        if not data:
            logging.warning("[ORDER] place_order called with no JSON body")
            return jsonify({'success': False, 'message': 'No order data received.'}), 400

        logging.info(f"[ORDER] Place order request from user: {session['user']['username']}")

        # Validate cart
        items_data = data.get('items', [])
        if not items_data:
            logging.warning("[ORDER] Cart is empty")
            return jsonify({'success': False, 'message': 'Your cart is empty. Please add items before placing an order.'}), 400

        logging.info(f"[ORDER] Cart items: {len(items_data)}, Shop: {data.get('shop')}, Total: {data.get('total')}")

        from bson.objectid import ObjectId

        # ── Step 1: Get Customer Details safely ──────────────────────────────
        try:
            user = users_collection.find_one({'_id': ObjectId(session['user']['id'])})
        except Exception as ue:
            logging.error(f"[ORDER] User lookup failed: {ue}")
            user = None

        if not user:
            logging.warning("[ORDER] User not found in DB, using session fallback")
            customer_name = session['user'].get('username', 'Customer')
            phone   = 'Not Provided'
            address = 'Not Provided'
        else:
            customer_name = user.get('delivery_name') or user.get('username') or session['user']['username']
            phone   = user.get('mobile') or 'Not Provided'
            address = user.get('delivery_location') or 'Not Provided'
            if user.get('delivery_pincode'):
                address += f" (Pincode: {user.get('delivery_pincode')})"

        logging.info(f"[ORDER] Customer: {customer_name}")

        # ── Step 2: Get Shop Details safely ──────────────────────────────────
        shop_name = (data.get('shop') or '').strip()
        shop = None
        if shop_name:
            try:
                shop = shops_collection.find_one({'name': shop_name})
                logging.info(f"[ORDER] Shop lookup '{shop_name}': found={shop is not None}")
            except Exception as se:
                logging.error(f"[ORDER] Shop lookup error: {se}")

        if not shop:
            try:
                shop = shops_collection.find_one({})
                logging.info(f"[ORDER] Fallback shop: {shop.get('name') if shop else 'None'}")
            except Exception:
                shop = None

        if not shop:
            shop = {'name': shop_name or 'Jilawar General Store', 'id': 1, 'owner': None}
            logging.warning("[ORDER] No shop found in DB — using hardcoded default")

        shop_id = shop.get('id', 1)
        effective_shop_name = shop.get('name') or shop_name or 'Jilawar General Store'

        # ── Step 3: Resolve owner ID safely (get_shop_owner_id is already None-safe) ──
        owner_full = shop.get('owner', '')
        owner_username = owner_full.split()[0].lower() if owner_full else None
        shop_owner_id  = get_shop_owner_id(owner_username)
        logging.info(f"[ORDER] Owner: {owner_full} -> Username: {owner_username} → ID={shop_owner_id}")

        # ── Step 4: Generate Order ID ─────────────────────────────────────────
        order_obj_id = ObjectId()
        order_id     = str(order_obj_id)
        logging.info(f"[ORDER] Generated order_id: {order_id}")

        # ── Step 5: Save OrderItems ───────────────────────────────────────────
        for item in items_data:
            if not item:
                continue
            try:
                order_items_collection.insert_one({
                    'ItemID':      str(uuid.uuid4()),
                    'OrderID':     order_id,
                    'ProductName': item.get('name', 'Unknown'),
                    'Quantity':    str(item.get('qty', 1))
                })
            except Exception as oi_err:
                logging.error(f"[ORDER] OrderItems insert error: {oi_err}")

        # ── Step 6: Build Order document ──────────────────────────────────────
        order_doc = {
            '_id':                order_obj_id,
            'OrderID':            order_id,
            'UserID':             session['user']['id'],
            'ShopID':             shop_id,
            'ShopName':           effective_shop_name,
            'ShopOwnerID':        shop_owner_id,
            'OrderStatus':        'Pending',
            'TotalAmount':        data.get('total', 0),
            'CreatedDate':        datetime.datetime.utcnow(),
            'user':               session['user']['username'],
            'shop':               effective_shop_name,
            'items':              items_data,
            'total':              data.get('total', 0),
            'status':             'Pending',
            'timestamp':          datetime.datetime.utcnow(),
            'estimated_delivery': '30-45 minutes',
            'customer_name':      customer_name,
            'phone':              phone,
            'address':            address
        }

        # ── Step 7: Notify shop owner ─────────────────────────────────────────
        if owner_username:
            try:
                owner_user = users_collection.find_one({'username': owner_username, 'role': 'owner'})
                if owner_user and '_id' in owner_user:
                    order_doc['ShopOwnerID'] = str(owner_user['_id'])
                    create_notification(
                        user_id=str(owner_user['_id']),
                        shop_id=shop_id,
                        message=f"🔔 New order #ORD{order_id[:8].upper()} received from {customer_name}.",
                        notification_type="new_order"
                    )
            except Exception as ne:
                logging.warning(f"[ORDER] Owner notification failed (non-fatal): {ne}")

        # ── Step 8: Insert Order ──────────────────────────────────────────────
        orders_collection.insert_one(order_doc)
        logging.info(f"[ORDER] Saved to DB: {order_id}")

        # ── Step 9: Notify customer ───────────────────────────────────────────
        try:
            create_notification(
                user_id=session['user']['id'],
                shop_id=shop_id,
                message=f"🎉 Your order #ORD{order_id[:8].upper()} at {effective_shop_name} has been placed successfully!",
                notification_type="order_placed"
            )
        except Exception as ne:
            logging.warning(f"[ORDER] Customer notification failed (non-fatal): {ne}")

        logging.info(f"[ORDER] Complete — order_id={order_id}, customer={customer_name}, total={data.get('total')}")
        return jsonify({'success': True, 'order_id': order_id})

    except Exception as e:
        logging.exception(f"[ORDER] Unhandled exception in place_order: {e}")
        return jsonify({'success': False, 'message': f'Order could not be created: {str(e)}'}), 500



# ── Distance API ──────────────────────────────────────────────────────────────
@app.route('/api/shops_by_distance')
def shops_by_distance():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    loc = request.args.get('loc', '').lower().strip()
    if not loc or loc not in SHOPS_BY_LOCATION:
        loc = next(iter(SHOPS_BY_LOCATION.keys()), 'nanded_city')
    try:
        user_lat = float(request.args.get('lat'))
        user_lng = float(request.args.get('lng'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid coordinates'}), 400

    shop_list = SHOPS_BY_LOCATION.get(loc, [])
    enriched  = []
    for shop in shop_list:
        d = haversine(user_lat, user_lng, shop.get('lat', user_lat), shop.get('lng', user_lng))
        enriched.append({
            'id':       shop['id'],
            'name':     shop['name'],
            'owner':    shop['owner'],
            'status':   shop['status'],
            'rating':   shop['rating'],
            'distance': f'{d:.1f} km',
            'dist_raw': round(d, 3),
            'image':    shop['image'],
        })
    enriched.sort(key=lambda s: s['dist_raw'])
    return jsonify({'success': True, 'shops': enriched})

# ── Grocery list OCR upload ───────────────────────────────────────────────────
@app.route('/api/upload_grocery_list', methods=['POST'])
def upload_grocery_list():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Please login first.'}), 401

    if 'grocery_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400

    file = request.files['grocery_file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'}), 400

    logging.info(f"[UPLOAD] Received file: {file.filename}")

    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': 'Invalid file type. Allowed: PNG, JPG, JPEG.'
        }), 400

    ext       = file.filename.rsplit('.', 1)[1].lower()
    # Use a short hex instead of the full filename to avoid Windows 260-char path limit
    safe_name = secure_filename(f"{uuid.uuid4().hex[:12]}.{ext}")
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    logging.info(f"[UPLOAD] Extension: {ext} | Save path: {save_path}")

    try:
        # ── Step 1: Read & save uploaded bytes ───────────────────────────────
        file.seek(0)
        file_bytes = file.read()
        logging.info(f"[UPLOAD] File bytes read: {len(file_bytes)} bytes")

        if not file_bytes or len(file_bytes) == 0:
            return jsonify({'success': False, 'message': '⚠ Uploaded file is empty. Please upload a valid file.'}), 400

        # Verify upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        with open(save_path, 'wb') as f_disk:
            f_disk.write(file_bytes)

        if not os.path.exists(save_path):
            logging.error(f"[UPLOAD] File was NOT saved to disk: {save_path}")
            return jsonify({'success': False, 'message': '⚠ Failed to save uploaded file. Please try again.'}), 500
        logging.info(f"[UPLOAD] File saved to disk successfully: {save_path}")

        # ── Step 2: Parse file content based on extension ─────────────────────
        parsed_items = []
        parse_warning = None
        try:
            if ext == 'pdf':
                logging.info("[UPLOAD] Parsing as PDF")
                parsed_items = parse_pdf_list(save_path) or []
            elif ext == 'xlsx':
                logging.info("[UPLOAD] Parsing as Excel")
                parsed_items = parse_excel_list(save_path) or []
            elif ext == 'csv':
                logging.info("[UPLOAD] Parsing as CSV")
                parsed_items = parse_csv_list(save_path) or []
            elif ext == 'txt':
                logging.info("[UPLOAD] Parsing as TXT")
                parsed_items = parse_txt_list(save_path) or []
            else:  # Image: PNG, JPG, JPEG
                logging.info("[UPLOAD] Parsing as image via OCR")
                raw_text = ocr_image(save_path) or ''
                if not raw_text.strip():
                    logging.warning("[UPLOAD] OCR returned empty text")
                    parse_warning = "⚠ OCR extraction produced no text. The image may be blurry or contain non-grocery content."
                else:
                    logging.info(f"[UPLOAD] OCR raw text: {repr(raw_text[:300])}")
                parsed_items = parse_text_lines(raw_text) or []
        except Exception as parse_err:
            logging.error(f"[UPLOAD] File parsing error: {parse_err}")
            parsed_items = []
            parse_warning = f"⚠ Unable to process file content: {str(parse_err)}"

        logging.info(f"[UPLOAD] Parsed items ({len(parsed_items)}): {parsed_items}")

        if not parsed_items:
            # Reject the upload if nothing could be extracted
            msg = parse_warning if parse_warning else "We couldn't detect any readable grocery items in this file. Please ensure it's a clear, handwritten or typed list."
            try:
                if os.path.exists(save_path):
                    os.remove(save_path) # Clean up the bad file
            except OSError:
                pass
            return jsonify({'success': False, 'message': f"❌ Upload Rejected: {msg}"}), 400

        # ── Step 3: Match parsed items against product catalogue ──────────────
        extracted_names = [it['name'] for it in parsed_items if it and 'name' in it]
        logging.info(f"[UPLOAD] Extracted item names: {extracted_names}")

        found_items, missing_names = match_items_in_catalogue(extracted_names)
        logging.info(f"[UPLOAD] Catalogue matched: {len(found_items)} found, {len(missing_names)} missing")

        if not found_items:
            try:
                if os.path.exists(save_path):
                    os.remove(save_path) # Clean up the bad file
            except OSError:
                pass
            sample = ", ".join(missing_names[:3])
            return jsonify({
                'success': False, 
                'message': f"❌ Upload Rejected: We read {len(missing_names)} item(s) from your list (like '{sample}'), but NONE of them are currently available in our shops. Please check available stock."
            }), 400

        # Build matched items list with quantities and totals
        matched_items_list = []
        seen_ids   = set()
        total_amount = 0
        qty_map = {it['name'].lower(): it.get('qty', '1') for it in parsed_items if it and 'name' in it}

        for it in found_items:
            if it['id'] not in seen_ids:
                seen_ids.add(it['id'])
                qty_str = qty_map.get(it['name'].lower(), '1')

                qty_num = 1
                num_match = re.search(r'\d+', str(qty_str))
                if num_match:
                    try:
                        qty_num = int(num_match.group(0))
                    except ValueError:
                        qty_num = 1

                price      = it.get('price', 0)
                item_total = price * qty_num
                total_amount += item_total

                matched_items_list.append({
                    'id':      it['id'],
                    'name':    it['name'],
                    'price':   price,
                    'unit':    it.get('unit', ''),
                    'qty':     qty_num,
                    'qty_str': qty_str,
                    'image':   it.get('image', '/static/images/products/placeholder.png')
                })

        # Add unmatched items as custom entries (price 0)
        for name in missing_names:
            qty_str = qty_map.get(name.lower(), '1')
            matched_items_list.append({
                'id':        f"custom_{uuid.uuid4().hex[:8]}",
                'name':      name,
                'price':     0,
                'unit':      '',
                'qty':       qty_str,
                'qty_str':   qty_str,
                'image':     '/static/images/products/placeholder.png',
                'is_custom': True
            })

        # ── Step 4: Generate Order ID ─────────────────────────────────────────
        from bson.objectid import ObjectId
        order_obj_id = ObjectId()
        order_id     = str(order_obj_id)
        logging.info(f"[UPLOAD] Generated order_id: {order_id}")

        # ── Step 5: Get Customer Details ──────────────────────────────────────
        try:
            user = users_collection.find_one({'_id': ObjectId(session['user']['id'])})
        except Exception as user_err:
            logging.error(f"[UPLOAD] User lookup failed: {user_err}")
            user = None

        if not user:
            logging.warning("[UPLOAD] User record not found in DB, using session data")
            customer_name = session['user'].get('username', 'Customer')
            phone   = 'Not Provided'
            address = 'Not Provided'
        else:
            customer_name = user.get('delivery_name') or user.get('username') or session['user']['username']
            phone   = user.get('mobile') or 'Not Provided'
            address = user.get('delivery_location') or 'Not Provided'
            if user.get('delivery_pincode'):
                address += f" (Pincode: {user.get('delivery_pincode')})"
        logging.info(f"[UPLOAD] Customer: {customer_name}, Phone: {phone}")

        # ── Step 6: Get Shop Details ──────────────────────────────────────────
        shop_id_form  = request.form.get('shop_id')
        shop_name_form = request.form.get('shop_name')
        shop = None

        if shop_id_form:
            try:
                shop = shops_collection.find_one({'id': int(shop_id_form)})
                logging.info(f"[UPLOAD] Shop lookup by id={shop_id_form}: {shop}")
            except (ValueError, Exception) as se:
                logging.warning(f"[UPLOAD] Shop lookup by ID failed: {se}")

        if not shop and shop_name_form:
            shop = shops_collection.find_one({'name': shop_name_form})
            logging.info(f"[UPLOAD] Shop lookup by name='{shop_name_form}': {shop}")

        if not shop:
            shop = shops_collection.find_one({})
            logging.info(f"[UPLOAD] Fallback shop: {shop}")

        # Final safe default if DB is empty
        if not shop:
            shop = {'name': 'Jilawar General Store', 'id': 1, 'owner': None}
            logging.warning("[UPLOAD] No shop found in DB — using hardcoded default")

        # ── Step 7: Resolve Shop Owner ID safely ──────────────────────────────
        shop_owner_id = None
        owner_full = shop.get('owner', '')
        owner_username = owner_full.split()[0].lower() if owner_full else None
        if owner_username:
            try:
                owner_doc = users_collection.find_one({'username': owner_username, 'role': 'owner'})
                if owner_doc and '_id' in owner_doc:
                    shop_owner_id = str(owner_doc['_id'])
                    logging.info(f"[UPLOAD] Shop owner resolved: {owner_username} → {shop_owner_id}")
                else:
                    logging.warning(f"[UPLOAD] No owner user found for username '{owner_username}'")
            except Exception as oe:
                logging.error(f"[UPLOAD] Owner lookup error: {oe}")
        else:
            logging.info("[UPLOAD] Shop has no owner field set")

        # ── Step 8: Save to UploadedFiles collection ──────────────────────────
        file_id = str(uuid.uuid4())
        try:
            uploaded_files_collection.insert_one({
                'FileID':      file_id,
                'UserID':      session['user']['id'],
                'FileName':    file.filename,
                'FileType':    ext,
                'FilePath':    f"/static/uploads/{safe_name}",
                'FileSize':    len(file_bytes),
                'UploadDate':  datetime.datetime.utcnow(),
                'OrderID':     order_id,
                'FileData':    bson.Binary(file_bytes)
            })
            logging.info(f"[UPLOAD] File record saved to DB: FileID={file_id}")
        except Exception as fdb_err:
            logging.error(f"[UPLOAD] Failed to save file record to DB: {fdb_err}")

        # ── Step 9: Save to OrderItems collection ─────────────────────────────
        for parsed_item in parsed_items:
            if not parsed_item or 'name' not in parsed_item:
                continue
            try:
                order_items_collection.insert_one({
                    'ItemID':      str(uuid.uuid4()),
                    'OrderID':     order_id,
                    'ProductName': parsed_item['name'],
                    'Quantity':    str(parsed_item.get('qty', '1'))
                })
            except Exception as oi_err:
                logging.error(f"[UPLOAD] OrderItems insert failed for '{parsed_item.get('name')}': {oi_err}")

        # ── Step 10: Save to Orders collection ───────────────────────────────
        order_doc = {
            '_id':                order_obj_id,
            'OrderID':            order_id,
            'UserID':             session['user']['id'],
            'ShopOwnerID':        shop_owner_id,
            'ShopID':             shop.get('id', 1),
            'OrderStatus':        'Pending',
            'TotalAmount':        total_amount,
            'CreatedDate':        datetime.datetime.utcnow(),
            'user':               session['user']['username'],
            'shop':               shop.get('name', 'Jilawar General Store'),
            'items':              matched_items_list,
            'total':              total_amount,
            'status':             'Pending',
            'timestamp':          datetime.datetime.utcnow(),
            'estimated_delivery': '30-45 minutes',
            'is_uploaded':        True,
            'uploaded_file':      file.filename,
            'uploaded_file_path': f"/static/uploads/{safe_name}",
            'customer_name':      customer_name,
            'phone':              phone,
            'address':            address
        }
        try:
            orders_collection.insert_one(order_doc)
            logging.info(f"[UPLOAD] Order saved: {order_id}")
        except Exception as ord_err:
            logging.error(f"[UPLOAD] Order insert failed: {ord_err}")

        # ── Step 11: Notifications ────────────────────────────────────────────
        try:
            create_notification(
                user_id=session['user']['id'],
                shop_id=shop.get('id', 1),
                message=f"📄 Your uploaded shopping list has been processed successfully. Order #ORD{order_id[:8].upper()} created.",
                notification_type="uploaded_list_processed"
            )
            if owner_username and shop_owner_id:
                owner_for_notif = users_collection.find_one({'username': owner_username, 'role': 'owner'})
                if owner_for_notif:
                    create_notification(
                        user_id=str(owner_for_notif['_id']),
                        shop_id=shop.get('id', 1),
                        message=f"📄 New uploaded shopping list! Review order #ORD{order_id[:8].upper()} from customer {customer_name}.",
                        notification_type="new_uploaded_list"
                    )
        except Exception as notif_err:
            logging.warning(f"[UPLOAD] Notification error (non-fatal): {notif_err}")

        # Build final warning message
        if not matched_items_list:
            warning_msg = parse_warning or "⚠ No grocery items were detected. Please review and add items manually."
        elif parse_warning:
            warning_msg = parse_warning
        else:
            warning_msg = "⚠ Some items could not be identified completely. Extracted valid items successfully. Please review and edit before placing your order."

        logging.info(f"[UPLOAD] Success — order_id={order_id}, items={len(matched_items_list)}, total={total_amount}")

        return jsonify({
            'success':        True,
            'order_id':       order_id,
            'customer_name':  customer_name,
            'phone':          phone,
            'address':        address,
            'total':          total_amount,
            'found_count':    len(found_items),
            'missing_count':  len(missing_names),
            'items':          matched_items_list,
            'warning':        warning_msg
        })

    except Exception as e:
        logging.exception(f"[UPLOAD] Unhandled exception in upload_grocery_list: {e}")
        # Provide a friendly message — never expose raw Python errors to the user
        friendly = str(e)
        if 'NoneType' in friendly and 'subscriptable' in friendly:
            friendly = '⚠ Internal data lookup returned no result. Please try again or contact support.'
        elif 'No such file' in friendly:
            friendly = f'⚠ File could not be saved. Debug: {traceback.format_exc()}'
        elif 'codec' in friendly or 'decode' in friendly:
            friendly = '⚠ File encoding error. Please save your file as UTF-8 and try again.'
        else:
            friendly = f'⚠ Unable to process file: {friendly}'
        return jsonify({'success': False, 'message': friendly}), 500

    finally:
        # Keep the file on disk for web downloads — do not delete
        pass

# ── Update uploaded order items (API) ─────────────────────────────────────────
@app.route('/api/update_uploaded_order', methods=['POST'])
def update_uploaded_order():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Please login first.'}), 401
    
    data = request.json
    order_id = data.get('order_id')
    updated_items = data.get('items', [])
    
    if not order_id:
        return jsonify({'success': False, 'message': 'Missing Order ID.'}), 400
        
    try:
        # Calculate new total amount based on updated items
        total_amount = 0
        for it in updated_items:
            price = 0
            try:
                price = float(it.get('price', 0))
            except (ValueError, TypeError):
                price = 0
            
            qty_str = str(it.get('qty_str') or it.get('qty') or '1')
            
            # Extract numeric quantity to calculate item total
            qty_num = 1
            num_match = re.search(r'\d+', qty_str)
            if num_match:
                try:
                    qty_num = int(num_match.group(0))
                except ValueError:
                    qty_num = 1
            
            # Sanitize data types before saving to database
            it['price'] = price
            it['qty'] = qty_num
            it['qty_str'] = qty_str
            
            total_amount += price * qty_num

        from bson.objectid import ObjectId
        # Update standard order document in Orders collection
        orders_collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {
                'items': updated_items,
                'total': total_amount,
                'TotalAmount': total_amount
            }}
        )
        
        # Update OrderItems collection (delete old items for this order and insert new ones)
        order_items_collection.delete_many({'OrderID': order_id})
        for it in updated_items:
            order_items_collection.insert_one({
                'ItemID': str(uuid.uuid4()),
                'OrderID': order_id,
                'ProductName': it.get('name'),
                'Quantity': str(it.get('qty_str') or it.get('qty') or '1')
            })
            
        # Get order details to notify customer and shop owner
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        if order:
            shop_name = order.get('shop')
            shop = shops_collection.find_one({'name': shop_name})
            shop_id = shop.get('id', 1) if shop else 1
            
            # Customer notification
            create_notification(
                user_id=session['user']['id'],
                shop_id=shop_id,
                message=f"📝 Your order #ORD{order_id[:8].upper()} items have been updated.",
                notification_type="order_updated"
            )
            
            # Shop Owner notification
            if shop:
                owner_username = shop.get('owner')
                owner_user = users_collection.find_one({'username': owner_username, 'role': 'owner'})
                if owner_user:
                    customer_name = order.get('customer_name') or order.get('user') or 'Customer'
                    create_notification(
                        user_id=str(owner_user['_id']),
                        shop_id=shop_id,
                        message=f"📝 Customer {customer_name} updated items for order #ORD{order_id[:8].upper()}.",
                        notification_type="customer_order_update"
                    )
            
        return jsonify({'success': True, 'new_total': total_amount})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Update error: {str(e)}'}), 500



# ── Update order status (owner API) ───────────────────────────────────────────
@app.route('/api/update_order_status', methods=['POST'])
def update_order_status():
    if 'user' not in session or session['user']['role'] != 'owner':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    from bson.objectid import ObjectId
    data       = request.json
    order_id   = data.get('order_id')
    new_status = data.get('status')
    valid = ['Pending', 'placed', 'Accepted', 'Rejected', 'Preparing', 'Processing', 'Ready', 'Out for Delivery', 'Delivered', 'Cancelled']
    if new_status not in valid:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    try:
        orders_collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': new_status, 'OrderStatus': new_status}}
        )

        # Get order to find the customer to notify
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        if order:
            cust_username = order.get('user')
            cust_user = users_collection.find_one({'username': cust_username, 'role': 'customer'})
            if cust_user:
                cust_id = str(cust_user['_id'])
                shop_name = order.get('shop', 'the shop')
                
                # Format nice message
                msg = f"Your order #ORD{order_id[:8].upper()} status was updated to '{new_status}' by {shop_name}."
                if new_status == 'Accepted':
                    msg = f"🟢 Your order #ORD{order_id[:8].upper()} has been accepted by {shop_name}."
                elif new_status == 'Rejected' or new_status == 'Cancelled':
                    msg = f"❌ Your order #ORD{order_id[:8].upper()} was rejected/cancelled by {shop_name}."
                elif new_status == 'Preparing' or new_status == 'Processing':
                    msg = f"🔵 Your order #ORD{order_id[:8].upper()} is now being processed at {shop_name}."
                elif new_status == 'Ready':
                    msg = f"🟣 Your order #ORD{order_id[:8].upper()} is ready at {shop_name}."
                elif new_status == 'Out for Delivery':
                    msg = f"🚚 Your order #ORD{order_id[:8].upper()} is out for delivery from {shop_name}."
                elif new_status == 'Delivered':
                    msg = f"✅ Your order #ORD{order_id[:8].upper()} has been delivered successfully. Thank you!"
                    
                create_notification(
                    user_id=cust_id,
                    shop_id=order.get('ShopID', 1),
                    message=msg,
                    notification_type=f"order_{new_status.lower().replace(' ', '_')}"
                )

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── Get order status (customer polling) ───────────────────────────────────────
@app.route('/api/order_status/<order_id>')
def order_status_api(order_id):
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    from bson.objectid import ObjectId
    try:
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        return jsonify({
            'success':            True,
            'status':             order.get('status', 'Pending'),
            'estimated_delivery': order.get('estimated_delivery', '30-45 minutes'),
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── Notification APIs ──────────────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    try:
        user_id = session['user']['id']
        notifications_raw = list(notifications_collection.find({'UserID': user_id}).sort('CreatedAt', -1).limit(30))
        notifications = []
        unread_count = 0
        for n in notifications_raw:
            n_id = str(n['_id'])
            created_at = n.get('CreatedAt')
            if created_at and hasattr(created_at, 'strftime'):
                created_at_str = created_at.strftime('%d %b, %I:%M %p')
            else:
                created_at_str = 'N/A'
                
            is_unread = n.get('Status', 'unread') == 'unread'
            if is_unread:
                unread_count += 1
                
            notifications.append({
                'NotificationID': n_id,
                'Message': n.get('Message', ''),
                'Type': n.get('Type', ''),
                'Status': n.get('Status', 'unread'),
                'CreatedAt': created_at_str
            })
        return jsonify({
            'success': True,
            'unread_count': unread_count,
            'notifications': notifications
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/notifications/mark_read', methods=['POST'])
def mark_notifications_read():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    try:
        user_id = session['user']['id']
        data = request.json or {}
        notification_id = data.get('notification_id')
        
        if notification_id:
            from bson.objectid import ObjectId
            notifications_collection.update_one(
                {'_id': ObjectId(notification_id), 'UserID': user_id},
                {'$set': {'Status': 'read'}}
            )
        else:
            notifications_collection.update_many(
                {'UserID': user_id, 'Status': 'unread'},
                {'$set': {'Status': 'read'}}
            )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── My orders page (customer) ─────────────────────────────────────────────────
@app.route('/my_orders')
def my_orders():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))
    if session['user']['role'] != 'customer':
        flash('This page is for customers only.', 'error')
        return redirect(url_for('home'))
    username   = session['user']['username']
    orders_raw = list(orders_collection.find({'user': username}).sort('timestamp', -1))
    orders = []
    for o in orders_raw:
        o['_id'] = str(o['_id'])
        if 'timestamp' in o and hasattr(o['timestamp'], 'strftime'):
            o['timestamp_str'] = o['timestamp'].strftime('%d %b %Y, %I:%M %p')
        else:
            o['timestamp_str'] = 'N/A'
        orders.append(o)
    return render_template('my_orders.html', orders=orders)

# ── Track order page (customer) ───────────────────────────────────────────────
@app.route('/track_order/<order_id>')
def track_order(order_id):
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))
    from bson.objectid import ObjectId
    
    # Validate order ID format
    if not order_id or not ObjectId.is_valid(order_id):
        flash('⚠ Order not found', 'error')
        return redirect(url_for('my_orders'))

    try:
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        if not order:
            flash('⚠ Order not found', 'error')
            return redirect(url_for('my_orders'))
        order['_id'] = str(order['_id'])
        if 'timestamp' in order and hasattr(order['timestamp'], 'strftime'):
            order['timestamp_str'] = order['timestamp'].strftime('%d %b %Y, %I:%M %p')
        else:
            order['timestamp_str'] = 'N/A'
        return render_template('track_order.html', order=order)
    except Exception:
        flash('⚠ Unable to load tracking details', 'error')
        return redirect(url_for('my_orders'))

# ── Shops map data API ────────────────────────────────────────────────────────
@app.route('/api/shops_map_data')
def shops_map_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    loc = request.args.get('loc', '').lower().strip()
    if not loc or loc not in LOCATIONS or loc not in SHOPS_BY_LOCATION:
        return jsonify({'success': False, 'message': '❌ Location not found'}), 404
    location_info = LOCATIONS[loc]
    shop_list     = SHOPS_BY_LOCATION.get(loc, [])
    shops_data    = []
    for shop in shop_list:
        shops_data.append({
            'id':       shop['id'],
            'name':     shop['name'],
            'owner':    shop['owner'],
            'phone':    shop.get('phone', 'N/A'),
            'distance': shop.get('distance', 'N/A'),
            'rating':   shop['rating'],
            'status':   shop['status'],
            'lat':      shop.get('lat', location_info['lat']),
            'lng':      shop.get('lng', location_info['lng']),
        })
    return jsonify({
        'success':  True,
        'location': {'name': location_info['name'], 'lat': location_info['lat'], 'lng': location_info['lng']},
        'shops':    shops_data,
    })

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
