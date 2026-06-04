import os
import re
import uuid
import math
import tempfile
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, jsonify, current_app)
from werkzeug.utils import secure_filename
from utils.db_connection import db
from datetime import datetime

product_bp = Blueprint('product', __name__)

# ── Allowed file extensions ───────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def _img(key):
    return _PRODUCT_IMAGES.get(key, '/static/images/products/placeholder.png')

# ── Grocery item catalogue ─────────────────────────────────────────────────────
GROCERY_ITEMS = [
    {
        'id': 'toor_dal',
        'name': 'Toor Dal',
        'category': 'Pulses',
        'price': 140,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('toor_dal'),
        'description': 'Split pigeon peas — rich in protein & fibre.',
        'badge': 'Organic',
        'badge_color': '#2e7d32',
    },
    {
        'id': 'basmati_rice',
        'name': 'Basmati Rice',
        'category': 'Grains',
        'price': 120,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('basmati_rice'),
        'description': 'Premium long-grain aromatic basmati rice.',
        'badge': 'Best Seller',
        'badge_color': '#e65100',
    },
    {
        'id': 'mustard_oil',
        'name': 'Mustard Oil',
        'category': 'Oils',
        'price': 180,
        'unit': 'per litre',
        'stock': 'In Stock',
        'image': _img('mustard_oil'),
        'description': 'Pure cold-pressed mustard oil, kachi ghani.',
        'badge': 'Pure',
        'badge_color': '#f9a825',
    },
    {
        'id': 'full_cream_milk',
        'name': 'Full Cream Milk',
        'category': 'Dairy',
        'price': 60,
        'unit': 'per litre',
        'stock': 'In Stock',
        'image': _img('milk'),
        'description': 'Fresh full-cream milk delivered daily.',
        'badge': 'Daily Fresh',
        'badge_color': '#1565c0',
    },
    {
        'id': 'wheat_flour',
        'name': 'Wheat Flour (Atta)',
        'category': 'Grains',
        'price': 55,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('atta'),
        'description': 'Fine whole wheat atta for soft rotis.',
        'badge': None,
        'badge_color': None,
    },
    {
        'id': 'sugar',
        'name': 'Sugar',
        'category': 'Essentials',
        'price': 45,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('sugar'),
        'description': 'Premium granulated white sugar.',
        'badge': None,
        'badge_color': None,
    },
    {
        'id': 'eggs_dozen',
        'name': 'Eggs (12 Pack)',
        'category': 'Dairy',
        'price': 90,
        'unit': 'per dozen',
        'stock': 'In Stock',
        'image': _img('eggs'),
        'description': 'Farm-fresh eggs, grade A.',
        'badge': 'Farm Fresh',
        'badge_color': '#f06292',
    },
    {
        'id': 'amul_butter',
        'name': 'Amul Butter',
        'category': 'Dairy',
        'price': 55,
        'unit': 'per 100g',
        'stock': 'Low Stock',
        'image': _img('butter'),
        'description': 'Pasteurised table butter, salted.',
        'badge': 'Popular',
        'badge_color': '#6a1b9a',
    },
    {
        'id': 'onion',
        'name': 'Onion',
        'category': 'Vegetables',
        'price': 40,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('onion'),
        'description': 'Fresh locally-sourced onions.',
        'badge': None,
        'badge_color': None,
    },
    {
        'id': 'potato',
        'name': 'Potato',
        'category': 'Vegetables',
        'price': 30,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('potato'),
        'description': 'Farm-fresh potatoes, perfect for curries.',
        'badge': None,
        'badge_color': None,
    },
    {
        'id': 'sunflower_oil',
        'name': 'Sunflower Oil',
        'category': 'Oils',
        'price': 150,
        'unit': 'per litre',
        'stock': 'In Stock',
        'image': _img('sunflower_oil'),
        'description': 'Light refined sunflower oil.',
        'badge': None,
        'badge_color': None,
    },
    {
        'id': 'salt',
        'name': 'Salt',
        'category': 'Essentials',
        'price': 20,
        'unit': 'per kg',
        'stock': 'In Stock',
        'image': _img('salt'),
        'description': 'Iodised table salt — enriched with minerals.',
        'badge': None,
        'badge_color': None,
    },
]

# ── Shop name map ─────────────────────────────────────────────────────────────
SHOP_NAMES = {
    'shree_ram_kirana': 'Shree Ram Kirana Store',
    'patel_general':    'Patel General Store',
    'annapurna_grocery':'Annapurna Grocery Mart',
    'fresh_daily':      'Fresh Daily Mart',
    'sharma_brothers':  'Sharma Brothers Store',
    'lucky_kirana':     'Lucky Kirana Shop',
    'new_india_mart':   'New India Mart',
    'royal_grocery':    'Royal Grocery Store',
    'jain_supermart':   'Jain Super Mart',
    'balaji_kirana':    'Balaji Kirana Store',
    'ganesh_mart':      'Ganesh General Mart',
    'city_superstore':  'City Super Store',
    'krishna_kirana':   'Krishna Kirana Bhandar',
}

# ── Login decorator ───────────────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('current_user') and not session.get('user'):
            flash('Please login to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── OCR helpers ───────────────────────────────────────────────────────────────
def _ocr_image(path):
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(path), lang='eng')
    except ImportError:
        return None
    except Exception:
        return None

def _ocr_pdf(path):
    text = ''
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or '') + '\n'
        return text
    except ImportError:
        pass
    except Exception:
        pass
    try:
        import PyPDF2
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += (page.extract_text() or '') + '\n'
        return text
    except Exception:
        return None

def _parse_items(raw_text):
    lines  = raw_text.splitlines()
    seen   = set()
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        name = re.split(r'[-–—:|/\\]|\d', line)[0].strip()
        name = re.sub(r'[^a-zA-Z\s\(\)]', '', name).strip()
        if len(name) < 2:
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            result.append(name.title())
    return result

def _match_catalogue(names):
    catalogue = {item['name'].lower(): item for item in GROCERY_ITEMS}
    found, missing = [], []
    for name in names:
        name_l  = name.lower()
        matched = None
        if name_l in catalogue:
            matched = catalogue[name_l]
        else:
            for cat_name, cat_item in catalogue.items():
                if set(name_l.split()) & set(cat_name.split()):
                    matched = cat_item
                    break
        if matched:
            found.append(matched)
        else:
            missing.append(name)
    return found, missing

# ── Routes ────────────────────────────────────────────────────────────────────
@product_bp.route('/products')
@login_required
def products():
    shop_id  = request.args.get('shop_id', 'shree_ram_kirana')
    location = request.args.get('location', '')
    shop_name = SHOP_NAMES.get(shop_id, 'Grocery Store')
    current_user = session.get('current_user') or session.get('user')

    uploads = []
    try:
        uploads = list(db.uploads.find({'shop_id': shop_id}).sort('uploaded_at', -1).limit(10))
        for u in uploads:
            u['_id'] = str(u['_id'])
    except Exception:
        pass

    return render_template(
        'products.html',
        items=GROCERY_ITEMS,
        shop_id=shop_id,
        shop_name=shop_name,
        location=location,
        current_user=current_user,
        uploads=uploads,
    )


@product_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    shop_id  = request.form.get('shop_id', 'shree_ram_kirana')
    location = request.form.get('location', '')

    if 'image' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('product.products', shop_id=shop_id, location=location))

    file = request.files['image']
    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('product.products', shop_id=shop_id, location=location))

    if not allowed_file(file.filename):
        flash('Invalid file type. Allowed: PNG, JPG, JPEG, PDF.', 'error')
        return redirect(url_for('product.products', shop_id=shop_id, location=location))

    ext       = file.filename.rsplit('.', 1)[1].lower()
    safe_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
    file.save(save_path)

    current_user = session.get('current_user') or session.get('user') or {}
    username = (current_user.get('username') if isinstance(current_user, dict)
                else 'anonymous')
    try:
        db.uploads.insert_one({
            'filename':      safe_name,
            'original_name': secure_filename(file.filename),
            'shop_id':       shop_id,
            'location':      location,
            'uploaded_by':   username,
            'uploaded_at':   datetime.utcnow(),
        })
    except Exception:
        pass

    flash('File uploaded successfully! 🎉', 'success')
    return redirect(url_for('product.products', shop_id=shop_id, location=location))


@product_bp.route('/api/grocery_ocr', methods=['POST'])
@login_required
def grocery_ocr():
    """OCR endpoint for the products page (blueprint version)."""
    if 'grocery_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400

    file = request.files['grocery_file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid type. Use PDF, JPG, JPEG, or PNG.'}), 400

    ext      = file.filename.rsplit('.', 1)[1].lower()
    tmp_path = os.path.join(tempfile.gettempdir(), f"ocr_{uuid.uuid4().hex}.{ext}")
    try:
        file.save(tmp_path)
        raw_text = _ocr_pdf(tmp_path) if ext == 'pdf' else _ocr_image(tmp_path)

        if not raw_text or not raw_text.strip():
            msg = ('Could not extract text from PDF.' if ext == 'pdf'
                   else 'OCR failed. Ensure Tesseract is installed.')
            return jsonify({'success': False, 'message': msg}), 422

        names = _parse_items(raw_text)
        if not names:
            return jsonify({'success': False, 'message': 'No items found in file.'}), 422

        found_items, missing_names = _match_catalogue(names)

        # Deduplicate
        seen_ids, unique_found = set(), []
        for it in found_items:
            if it['id'] not in seen_ids:
                seen_ids.add(it['id'])
                unique_found.append({
                    'id':    it['id'],
                    'name':  it['name'],
                    'price': it['price'],
                    'unit':  it['unit'],
                    'image': it['image'],
                })

        return jsonify({
            'success':       True,
            'found':         unique_found,
            'missing':       missing_names,
            'found_count':   len(unique_found),
            'missing_count': len(missing_names),
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@product_bp.route('/compare')
def compare():
    return render_template('compare.html')
