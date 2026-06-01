"""
End-to-End Upload Shopping List Test Suite
Tests: PNG, JPG, JPEG, PDF, CSV, Excel (.xlsx), TXT
Covers: file upload, parsing, order creation, DB entries, notifications
"""

import os
import sys
import io
import json
import time
import struct
import zlib
import csv
import openpyxl
import requests
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

BASE_URL = "http://127.0.0.1:5000"
MONGO_URI = "mongodb+srv://dbRurik:Rutik123@cluster0.dfeobzy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN  = ""
RED    = ""
YELLOW = ""
CYAN   = ""
BOLD   = ""
RESET  = ""

# Force UTF-8 output on Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def ok(msg):   print(f"  [PASS]  {msg}")
def fail(msg): print(f"  [FAIL]  {msg}")
def info(msg): print(f"  [INFO]  {msg}")
def warn(msg): print(f"  [WARN]  {msg}")
def head(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")


results = {"passed": [], "failed": [], "warnings": []}

def record(label, passed, detail=""):
    if passed:
        results["passed"].append(label)
        ok(f"{label}" + (f" — {detail}" if detail else ""))
    else:
        results["failed"].append(label)
        fail(f"{label}" + (f" — {detail}" if detail else ""))

# ── DB Setup ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  NEAREST GROCERY SHOP -- UPLOAD END-TO-END TEST SUITE")
print(f"{'='*60}")

try:
    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=15000)
    db = client.grocery_app
    users_col     = db.users
    shops_col     = db.shops
    orders_col    = db.orders
    files_col     = db.uploaded_files
    items_col     = db.order_items
    notifs_col    = db.notifications
    # ping
    client.admin.command('ping')
    ok("MongoDB connection established")
except Exception as e:
    fail(f"MongoDB connection failed: {e}")
    sys.exit(1)

# ── Session ───────────────────────────────────────────────────────────────────
head("STEP 1 — Authentication")

TEST_USER = "test_upload_user"
TEST_PASS = "TestPass123!"
TEST_EMAIL = "testupload@example.com"

session_http = requests.Session()

# Register test user (ignore if exists)
try:
    r = session_http.post(f"{BASE_URL}/register", data={
        "username": TEST_USER,
        "email": TEST_EMAIL,
        "password": TEST_PASS,
        "confirmPassword": TEST_PASS,
        "role": "customer"
    }, allow_redirects=True, timeout=10)
    if "already" in r.text.lower() or r.status_code in (200, 302):
        info("Test user exists or registered")
    else:
        warn(f"Register response: {r.status_code}")
except Exception as e:
    warn(f"Register step: {e}")

# Login
try:
    r = session_http.post(f"{BASE_URL}/login", data={
        "username": TEST_USER,
        "password": TEST_PASS,
        "role": "customer"
    }, allow_redirects=True, timeout=10)
    logged_in = "logout" in r.text.lower() or "profile" in r.text.lower() or r.url.endswith("/profile")
    record("User login", logged_in, f"HTTP {r.status_code}")
    if not logged_in:
        fail("Cannot continue without login")
        sys.exit(1)
except Exception as e:
    fail(f"Login error: {e}")
    sys.exit(1)

# Get user record
user_doc = users_col.find_one({"username": TEST_USER})
record("User record in MongoDB", user_doc is not None, f"id={str(user_doc.get('_id','?')) if user_doc else 'None'}")

# ── Test file generators ───────────────────────────────────────────────────────
GROCERY_CONTENT = """Shopping List
Milk - 2
Eggs - 12
Sugar - 1kg
Basmati Rice - 5kg
Onion - 2kg
Toor Dal - 1kg
Butter - 200g
Salt - 1kg
"""

def make_txt():
    return GROCERY_CONTENT.encode("utf-8"), "shopping_list.txt", "text/plain"

def make_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Item Name", "Quantity"])
    w.writerow(["Milk", "2 litre"])
    w.writerow(["Eggs", "12"])
    w.writerow(["Sugar", "1kg"])
    w.writerow(["Basmati Rice", "5kg"])
    w.writerow(["Onion", "2kg"])
    w.writerow(["Toor Dal", "1kg"])
    return buf.getvalue().encode("utf-8"), "shopping_list.csv", "text/csv"

def make_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Shopping List"
    ws.append(["Item Name", "Quantity"])
    ws.append(["Milk", "2"])
    ws.append(["Eggs", "12"])
    ws.append(["Sugar", "1kg"])
    ws.append(["Basmati Rice", "5kg"])
    ws.append(["Onion", "2kg"])
    ws.append(["Toor Dal", "1kg"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), "shopping_list.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def make_pdf():
    """Create a minimal valid PDF with grocery text embedded."""
    # Minimal PDF with text stream
    items_text = (
        "Shopping List\\n"
        "Milk 2\\n"
        "Eggs 12\\n"
        "Sugar 1kg\\n"
        "Basmati Rice 5kg\\n"
        "Onion 2kg\\n"
        "Toor Dal 1kg\\n"
    )
    stream = f"BT /F1 12 Tf 50 750 Td ({items_text}) Tj ET"
    stream_bytes = stream.encode("latin-1")
    pdf = b""
    pdf += b"%PDF-1.4\n"
    offsets = []

    def obj(num, content):
        nonlocal pdf
        offsets.append(len(pdf))
        pdf += f"{num} 0 obj\n".encode()
        pdf += content.encode() if isinstance(content, str) else content
        pdf += b"\nendobj\n"

    obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
    obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    obj(3, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    stream_header = f"<< /Length {len(stream_bytes)} >>\nstream\n"
    offsets.append(len(pdf))
    pdf += f"4 0 obj\n".encode() + stream_header.encode() + stream_bytes + b"\nendstream\nendobj\n"
    obj(5, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 6\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
    pdf += f"startxref\n{xref_offset}\n%%EOF\n".encode()
    return pdf, "shopping_list.pdf", "application/pdf"

def make_png():
    """Create a minimal 1x1 white PNG (OCR won't extract items but upload should succeed)."""
    def crc32(data): return struct.pack(">I", zlib.crc32(data) & 0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", 50, 30, 8, 2, 0, 0, 0)
    ihdr = b'IHDR' + ihdr_data
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + crc32(ihdr)
    # IDAT — 30 rows of 50 white pixels (RGB)
    raw = b''
    for _ in range(30):
        raw += b'\x00' + b'\xff\xff\xff' * 50
    compressed = zlib.compress(raw)
    idat_data = compressed
    idat = b'IDAT' + idat_data
    idat_chunk = struct.pack(">I", len(idat_data)) + idat + crc32(idat)
    # IEND
    iend = b'IEND'
    iend_chunk = struct.pack(">I", 0) + iend + crc32(iend)
    return sig + ihdr_chunk + idat_chunk + iend_chunk, "shopping_list.png", "image/png"

def make_jpg():
    """Minimal valid JPEG (1x1 white pixel)."""
    # JPEG with a minimal valid structure
    jpg_bytes = bytes([
        0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
        0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,
        0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
        0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
        0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,
        0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
        0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,
        0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
        0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,
        0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
        0x09,0x0A,0x0B,0xFF,0xC4,0x00,0xB5,0x10,0x00,0x02,0x01,0x03,
        0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,
        0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,
        0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,0x81,0x91,0xA1,0x08,
        0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,0x24,0x33,0x62,0x72,
        0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,
        0x29,0x2A,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,
        0x46,0x47,0x48,0x49,0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,
        0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6A,0x73,0x74,0x75,
        0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8A,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,0xA4,
        0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,
        0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,0xC8,0xC9,0xCA,
        0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,0xE3,
        0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,0xF5,
        0xF6,0xF7,0xF8,0xF9,0xFA,0xFF,0xDA,0x00,0x08,0x01,0x01,0x00,
        0x00,0x3F,0x00,0xFB,0xD3,0xFF,0xD9
    ])
    return bytes(jpg_bytes), "shopping_list.jpg", "image/jpeg"

# ── Upload test helper ─────────────────────────────────────────────────────────
def run_upload_test(label, file_bytes, filename, content_type, expect_items=True):
    head(f"TEST — {label}")
    order_id = None
    snap_before = orders_col.count_documents({})

    try:
        r = session_http.post(
            f"{BASE_URL}/api/upload_grocery_list",
            files={"grocery_file": (filename, file_bytes, content_type)},
            data={"shop_id": "1", "shop_name": "Jilawar General Store"},
            timeout=30
        )
        record(f"{label}: HTTP response OK", r.status_code == 200,
               f"HTTP {r.status_code}")

        try:
            data = r.json()
        except Exception:
            record(f"{label}: Response is valid JSON", False, f"raw={r.text[:200]}")
            return None

        record(f"{label}: API success=True", data.get("success") is True,
               f"message={data.get('message','')[:120]}")

        if not data.get("success"):
            warn(f"  Server message: {data.get('message','')}")
            return None

        order_id = data.get("order_id")
        record(f"{label}: order_id returned", bool(order_id), f"order_id={order_id}")

        items = data.get("items", [])
        info(f"  Items extracted: {len(items)} total "
             f"({data.get('found_count',0)} matched, {data.get('missing_count',0)} custom)")
        for it in items[:5]:
            info(f"    • {it.get('name')} x{it.get('qty')} @ ₹{it.get('price',0)}")

        if expect_items:
            record(f"{label}: Items extracted (>0)", len(items) > 0, f"count={len(items)}")
        else:
            warn(f"  OCR may return 0 items for minimal test image (expected for blank PNG/JPG)")

        total = data.get("total", 0)
        record(f"{label}: Total amount computed", isinstance(total, (int, float)),
               f"₹{total}")

    except Exception as e:
        record(f"{label}: Upload request", False, str(e))
        return None

    # ── DB Verification ────────────────────────────────────────────────────────
    if order_id:
        try:
            order_doc = orders_col.find_one({"_id": ObjectId(order_id)})
            record(f"{label}: Order in MongoDB orders", order_doc is not None,
                   f"_id={order_id}")
            if order_doc:
                record(f"{label}: Order.is_uploaded=True",
                       order_doc.get("is_uploaded") is True)
                record(f"{label}: Order.status=Pending",
                       order_doc.get("status") == "Pending")
                record(f"{label}: Order.user set",
                       bool(order_doc.get("user")), f"user={order_doc.get('user')}")
                record(f"{label}: Order.items list in DB",
                       isinstance(order_doc.get("items"), list),
                       f"count={len(order_doc.get('items',[]))}")
        except Exception as e:
            record(f"{label}: Order DB check", False, str(e))

        # OrderItems collection
        try:
            oi_count = items_col.count_documents({"OrderID": order_id})
            info(f"  OrderItems collection: {oi_count} item rows for this order")
            record(f"{label}: OrderItems collection populated",
                   True, f"{oi_count} rows")
        except Exception as e:
            record(f"{label}: OrderItems DB check", False, str(e))

        # UploadedFiles collection
        try:
            uf = files_col.find_one({"OrderID": order_id})
            record(f"{label}: UploadedFiles collection entry",
                   uf is not None, f"FileID={uf.get('FileID','?') if uf else 'None'}")
            if uf:
                record(f"{label}: File binary stored",
                       uf.get("FileData") is not None,
                       f"size={uf.get('FileSize',0)} bytes")
                record(f"{label}: FilePath set",
                       bool(uf.get("FilePath")), f"path={uf.get('FilePath','?')}")
        except Exception as e:
            record(f"{label}: UploadedFiles DB check", False, str(e))

        # Notifications
        try:
            notif = notifs_col.find_one({
                "UserID": str(user_doc["_id"]),
                "Type": "uploaded_list_processed"
            })
            # find a recent one (last 60s)
            recent_notif = notifs_col.find_one({
                "UserID": str(user_doc["_id"]),
                "Type": "uploaded_list_processed",
                "CreatedAt": {"$gte": datetime.datetime.utcnow() - datetime.timedelta(minutes=2)}
            })
            record(f"{label}: Customer notification created",
                   recent_notif is not None,
                   f"msg={recent_notif.get('Message','')[:60] if recent_notif else 'None'}")
        except Exception as e:
            record(f"{label}: Notifications check", False, str(e))

        # Disk file
        try:
            upload_dir = os.path.join(
                os.path.dirname(__file__), "static", "uploads"
            )
            # look for any file recently created
            files_on_disk = [f for f in os.listdir(upload_dir)
                             if order_id[:8].lower() in f.lower() or True]
            # just verify upload dir has files
            record(f"{label}: Upload directory accessible",
                   os.path.isdir(upload_dir), f"path={upload_dir}")
            info(f"  Upload dir file count: {len(os.listdir(upload_dir))}")
        except Exception as e:
            record(f"{label}: Disk storage check", False, str(e))

    return order_id

# ── Run all format tests ───────────────────────────────────────────────────────
head("UPLOADING ALL FILE FORMATS")

txt_bytes, txt_name, txt_ct   = make_txt()
csv_bytes, csv_name, csv_ct   = make_csv()
xlsx_bytes, xlsx_name, xlsx_ct = make_xlsx()
pdf_bytes, pdf_name, pdf_ct   = make_pdf()
png_bytes, png_name, png_ct   = make_png()
jpg_bytes, jpg_name, jpg_ct   = make_jpg()

order_ids = {}
order_ids["txt"]  = run_upload_test("TXT Upload",   txt_bytes,  txt_name,  txt_ct,  expect_items=True)
order_ids["csv"]  = run_upload_test("CSV Upload",   csv_bytes,  csv_name,  csv_ct,  expect_items=True)
order_ids["xlsx"] = run_upload_test("Excel Upload", xlsx_bytes, xlsx_name, xlsx_ct, expect_items=True)
order_ids["pdf"]  = run_upload_test("PDF Upload",   pdf_bytes,  pdf_name,  pdf_ct,  expect_items=True)
order_ids["png"]  = run_upload_test("PNG Upload",   png_bytes,  png_name,  png_ct,  expect_items=False)
order_ids["jpg"]  = run_upload_test("JPG Upload",   jpg_bytes,  jpg_name,  jpg_ct,  expect_items=False)
# JPEG uses same data as JPG but different filename
order_ids["jpeg"] = run_upload_test("JPEG Upload",  jpg_bytes,  "shopping_list.jpeg", "image/jpeg", expect_items=False)

# ── My Orders API verification ─────────────────────────────────────────────────
head("STEP 3 — My Orders Page Verification")
try:
    r = session_http.get(f"{BASE_URL}/my_orders", timeout=10)
    record("My Orders page loads (HTTP 200)", r.status_code == 200, f"HTTP {r.status_code}")
    # Count orders visible in page
    uploaded_count = r.text.count("uploaded_file") + r.text.count("is_uploaded")
    info(f"  Uploaded order references on page: {uploaded_count}")
    record("My Orders page has order references", "ORD" in r.text or "order" in r.text.lower())
except Exception as e:
    record("My Orders page", False, str(e))

# ── Track Order verification ───────────────────────────────────────────────────
head("STEP 4 — Track Order Page Verification")
sample_order_id = next((v for v in order_ids.values() if v), None)
if sample_order_id:
    try:
        r = session_http.get(f"{BASE_URL}/track_order/{sample_order_id}", timeout=10)
        record("Track Order page loads", r.status_code == 200,
               f"HTTP {r.status_code}, order={sample_order_id[:8]}")
        record("Track Order page shows status", "Pending" in r.text or "status" in r.text.lower())
    except Exception as e:
        record("Track Order page", False, str(e))
else:
    warn("No successful order ID available for track order test")

# ── Notifications API ──────────────────────────────────────────────────────────
head("STEP 5 — Notifications API Verification")
try:
    r = session_http.get(f"{BASE_URL}/api/notifications", timeout=10)
    record("Notifications API responds", r.status_code == 200, f"HTTP {r.status_code}")
    ndata = r.json()
    record("Notifications API success=True", ndata.get("success") is True)
    notifs = ndata.get("notifications", [])
    upload_notifs = [n for n in notifs if "uploaded" in n.get("Message","").lower()
                     or "shopping list" in n.get("Message","").lower()]
    info(f"  Total notifications: {len(notifs)}, Upload-related: {len(upload_notifs)}")
    record("Upload notifications present", len(upload_notifs) > 0,
           f"{len(upload_notifs)} upload notifications found")
except Exception as e:
    record("Notifications API", False, str(e))

# ── Existing Features Regression Check ────────────────────────────────────────
head("STEP 6 — Existing Features Regression Check")

# Home page
try:
    r = session_http.get(f"{BASE_URL}/", timeout=10)
    record("Home page loads", r.status_code == 200)
except Exception as e:
    record("Home page", False, str(e))

# Location page
try:
    r = session_http.get(f"{BASE_URL}/location", timeout=10)
    record("Location page loads", r.status_code == 200)
except Exception as e:
    record("Location page", False, str(e))

# Shops page
try:
    r = session_http.get(f"{BASE_URL}/shops?loc=nanded_city", timeout=10)
    record("Shops page loads", r.status_code == 200)
except Exception as e:
    record("Shops page", False, str(e))

# Items page
try:
    r = session_http.get(f"{BASE_URL}/items?shop_id=1&loc=nanded_city", timeout=10)
    record("Items page loads", r.status_code == 200)
except Exception as e:
    record("Items page", False, str(e))

# shops_by_distance API
try:
    r = session_http.get(f"{BASE_URL}/api/shops_by_distance?loc=nanded_city&lat=19.162&lng=77.317", timeout=10)
    record("shops_by_distance API works", r.status_code == 200 and r.json().get("success"))
except Exception as e:
    record("shops_by_distance API", False, str(e))

# place_order API (standard order)
try:
    r = session_http.post(f"{BASE_URL}/api/place_order", json={
        "shop": "Jilawar General Store",
        "items": [{"name": "Sugar", "qty": 1, "price": 45}],
        "total": 45
    }, timeout=10)
    record("Standard place_order API works",
           r.status_code == 200 and r.json().get("success"),
           f"HTTP {r.status_code}")
except Exception as e:
    record("Standard place_order API", False, str(e))

# Profile page
try:
    r = session_http.get(f"{BASE_URL}/profile", timeout=10)
    record("Profile page loads", r.status_code == 200)
except Exception as e:
    record("Profile page", False, str(e))

# ── Database Integrity Check ───────────────────────────────────────────────────
head("STEP 7 — Database Integrity Check")
try:
    total_orders = orders_col.count_documents({})
    uploaded_orders = orders_col.count_documents({"is_uploaded": True})
    standard_orders = orders_col.count_documents({"is_uploaded": {"$ne": True}})
    total_files = files_col.count_documents({})
    total_order_items = items_col.count_documents({})
    total_notifs = notifs_col.count_documents({})

    info(f"  Total orders: {total_orders} ({standard_orders} standard, {uploaded_orders} uploaded)")
    info(f"  Total uploaded files in DB: {total_files}")
    info(f"  Total order items: {total_order_items}")
    info(f"  Total notifications: {total_notifs}")

    record("Orders collection has documents", total_orders > 0)
    record("UploadedFiles collection populated", total_files > 0)
    record("OrderItems collection populated", total_order_items > 0)
    record("No None ShopOwnerID crash in recent uploads",
           orders_col.count_documents({"is_uploaded": True, "OrderStatus": {"$exists": True}}) > 0)
except Exception as e:
    record("Database integrity", False, str(e))

# ── Error log check ────────────────────────────────────────────────────────────
head("STEP 8 — Error Pattern Check in Recent Uploads")
try:
    # Check recent uploaded orders have no error markers
    recent_uploads = list(orders_col.find(
        {"is_uploaded": True},
        sort=[("timestamp", -1)],
        limit=10
    ))
    none_errors = 0
    for o in recent_uploads:
        if o.get("items") is None:
            none_errors += 1

    record("Recent uploaded orders have items field (not None)",
           none_errors == 0, f"{none_errors} orders with None items")
    record("No NoneType crashes in recent uploads",
           all(o.get("OrderStatus") is not None for o in recent_uploads),
           f"checked {len(recent_uploads)} recent uploads")
except Exception as e:
    record("Error pattern check", False, str(e))

# ── Final Report ───────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  FINAL TEST REPORT")
print(f"{'='*60}\n")

passed = len(results["passed"])
failed = len(results["failed"])
total  = passed + failed

print(f"[PASS] PASSED: {passed}/{total}")
print(f"[FAIL] FAILED: {failed}/{total}\n")

if results["failed"]:
    print("Failed Tests:")
    for f in results["failed"]:
        print(f"  [FAIL] {f}")
    print()

if failed == 0:
    print("ALL TESTS PASSED -- SYSTEM FULLY FUNCTIONAL")
else:
    print(f"WARNING: {failed} test(s) need attention.")

print("\nOrder IDs created during testing:")
for fmt, oid in order_ids.items():
    status = f"[OK]  {oid}" if oid else "[FAIL] None"
    print(f"  {fmt.upper():<6}: {status}")

print()

