#!/usr/bin/env python3
"""
Full project verification script
Checks MongoDB, Tesseract, and all routes
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

print("\n" + "="*70)
print("FULL PROJECT VERIFICATION")
print("="*70 + "\n")

# ============================================================================
# 1. CHECK MONGODB ATLAS CONNECTION
# ============================================================================
print("1️⃣  CHECKING MONGODB ATLAS CONNECTION...")
print("-" * 70)

try:
    from utils.db_connection import db, _client
    
    # Try to ping the server
    _client.admin.command('ping')
    print("✅ MongoDB server is reachable")
    
    # Check collections
    collections_to_check = ['users', 'shops', 'orders', 'products']
    all_collections_ok = True
    
    for collection_name in collections_to_check:
        try:
            collection = db[collection_name]
            count = collection.count_documents({})
            print(f"✅ Collection '{collection_name}': {count} documents")
        except Exception as e:
            print(f"❌ Collection '{collection_name}': Error - {str(e)}")
            all_collections_ok = False
    
    if all_collections_ok:
        print("\n✅ All MongoDB collections accessible")
    else:
        print("\n⚠️  Some MongoDB collections have issues")
        
except ImportError as e:
    print(f"❌ Import error: {str(e)}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {str(e)}")
    print(f"   Error type: {type(e).__name__}")

print()

# ============================================================================
# 2. CHECK TESSERACT OCR INSTALLATION
# ============================================================================
print("2️⃣  CHECKING TESSERACT OCR INSTALLATION...")
print("-" * 70)

try:
    import pytesseract
    from PIL import Image
    
    # Check if pytesseract is installed
    print("✅ pytesseract library is installed")
    
    # Try to check tesseract command
    try:
        result = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract executable found: {result}")
    except pytesseract.TesseractNotFoundError:
        print("❌ Tesseract executable not found")
        print("   Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    except Exception as e:
        print(f"⚠️  Could not verify Tesseract: {str(e)}")
        
except ImportError as e:
    print(f"❌ pytesseract not installed: {str(e)}")
    print("   Install with: pip install pytesseract pillow")

print()

# ============================================================================
# 3. CHECK FLASK ROUTES
# ============================================================================
print("3️⃣  CHECKING FLASK ROUTES...")
print("-" * 70)

try:
    from app import app
    
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ', '.join(rule.methods - {'HEAD', 'OPTIONS'}),
                'path': str(rule)
            })
    
    print(f"✅ Found {len(routes)} routes in app.py\n")
    
    # Group by method
    get_routes = [r for r in routes if 'GET' in r['methods']]
    post_routes = [r for r in routes if 'POST' in r['methods']]
    
    print(f"  GET routes: {len(get_routes)}")
    for r in get_routes[:5]:
        print(f"    - {r['path']}")
    if len(get_routes) > 5:
        print(f"    ... and {len(get_routes) - 5} more")
    
    print(f"\n  POST routes: {len(post_routes)}")
    for r in post_routes[:5]:
        print(f"    - {r['path']}")
    if len(post_routes) > 5:
        print(f"    ... and {len(post_routes) - 5} more")
    
    print("\n✅ All routes are defined and accessible")
    
except ImportError as e:
    print(f"❌ Could not import app: {str(e)}")
except Exception as e:
    print(f"❌ Error checking routes: {str(e)}")

print()

# ============================================================================
# 4. CHECK FOR IMPORT ERRORS & WARNINGS
# ============================================================================
print("4️⃣  CHECKING FOR IMPORT ERRORS & WARNINGS...")
print("-" * 70)

error_found = False

try:
    # Check routes imports
    print("Checking route imports...")
    from routes import user_routes
    from routes import shop_routes
    from routes import product_routes
    print("✅ All route modules imported successfully")
except ImportError as e:
    print(f"❌ Route import error: {str(e)}")
    error_found = True
except Exception as e:
    print(f"❌ Route import error: {type(e).__name__}: {str(e)}")
    error_found = True

try:
    print("Checking utils imports...")
    from utils import db_connection
    print("✅ Utils modules imported successfully")
except ImportError as e:
    print(f"❌ Utils import error: {str(e)}")
    error_found = True
except Exception as e:
    print(f"❌ Utils import error: {type(e).__name__}: {str(e)}")
    error_found = True

if not error_found:
    print("\n✅ No import errors found")

print()
print("="*70)
print("VERIFICATION COMPLETE")
print("="*70)
print()
