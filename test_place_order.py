"""
Dedicated Place Order API Test
Tests: cart-empty guard, valid order, DB save, notifications, My Orders, Track Order
"""
import io, sys, json, datetime, requests
from pymongo import MongoClient
from bson.objectid import ObjectId

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:5000"
MONGO_URI = "mongodb+srv://dbRurik:Rutik123@cluster0.dfeobzy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

results = {"passed": [], "failed": []}

def ok(msg):   results["passed"].append(msg); print(f"  [PASS]  {msg}")
def fail(msg): results["failed"].append(msg); print(f"  [FAIL]  {msg}")
def info(msg): print(f"  [INFO]  {msg}")
def head(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")

print("\n" + "="*60)
print("  PLACE ORDER — DEDICATED API TEST SUITE")
print("="*60)

# MongoDB
client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=15000)
db = client.grocery_app
orders_col    = db.orders
items_col     = db.order_items
notifs_col    = db.notifications
users_col     = db.users

# Session
s = requests.Session()

# Login with test user
TEST_USER = "test_upload_user"
TEST_PASS = "TestPass123!"
r = s.post(f"{BASE_URL}/login", data={"username": TEST_USER, "password": TEST_PASS, "role": "customer"}, allow_redirects=True, timeout=10)
logged_in = "logout" in r.text.lower() or "profile" in r.text.lower()
if logged_in:
    ok("Login successful")
else:
    fail("Login failed — cannot continue")
    sys.exit(1)

user_doc = users_col.find_one({"username": TEST_USER})

# ── TEST 1: Empty cart should return 400 ────────────────────────────────────
head("TEST 1 — Empty Cart Guard")
r = s.post(f"{BASE_URL}/api/place_order",
           json={"shop": "Jilawar General Store", "items": [], "total": 0},
           timeout=10)
info(f"HTTP {r.status_code} — {r.text[:120]}")
ok("Empty cart returns 400") if r.status_code == 400 else fail(f"Empty cart should return 400, got {r.status_code}")
try:
    data = r.json()
    ok("Empty cart response is JSON") if not data.get("success") else fail("Empty cart should return success=False")
except:
    fail("Empty cart response is not JSON")

# ── TEST 2: Valid order with items ───────────────────────────────────────────
head("TEST 2 — Valid Place Order")

CART_ITEMS = [
    {"id": 1, "name": "Full Cream Milk", "price": 60, "qty": 2, "image": "/static/images/products/milk.jpg"},
    {"id": 2, "name": "Eggs (12 Pack)",  "price": 90, "qty": 1, "image": "/static/images/products/eggs.jpg"},
    {"id": 3, "name": "Sugar",           "price": 45, "qty": 3, "image": "/static/images/products/sugar.jpg"},
]
TOTAL = sum(i["price"] * i["qty"] for i in CART_ITEMS)
info(f"Cart: {len(CART_ITEMS)} items, Total: Rs.{TOTAL}")

orders_before = orders_col.count_documents({})

r = s.post(f"{BASE_URL}/api/place_order",
           json={"shop": "Jilawar General Store", "items": CART_ITEMS, "total": TOTAL},
           timeout=15)
info(f"HTTP {r.status_code}")

ok("Place Order HTTP 200") if r.status_code == 200 else fail(f"Place Order got HTTP {r.status_code}: {r.text[:150]}")

try:
    data = r.json()
    info(f"Response: {json.dumps(data)[:200]}")
except Exception as e:
    fail(f"Response not valid JSON: {r.text[:200]}")
    sys.exit(1)

ok("success=True") if data.get("success") else fail(f"success=False — message: {data.get('message')}")
order_id = data.get("order_id")
ok(f"order_id returned: {order_id}") if order_id else fail("No order_id in response")

# ── TEST 3: Database Verification ────────────────────────────────────────────
head("TEST 3 — Database Order Verification")

if order_id:
    try:
        order_doc = orders_col.find_one({"_id": ObjectId(order_id)})
        ok("Order in orders collection") if order_doc else fail("Order NOT found in DB")

        if order_doc:
            ok("order.status = Pending") if order_doc.get("status") == "Pending" else fail(f"status = {order_doc.get('status')}")
            ok("order.OrderStatus = Pending") if order_doc.get("OrderStatus") == "Pending" else fail(f"OrderStatus = {order_doc.get('OrderStatus')}")
            ok("order.user set") if order_doc.get("user") else fail("order.user is empty")
            ok("order.items is list") if isinstance(order_doc.get("items"), list) else fail("order.items is not list")
            ok(f"order.items count={len(order_doc.get('items',[]))}") if len(order_doc.get("items", [])) == 3 else fail(f"Expected 3 items, got {len(order_doc.get('items', []))}")
            ok("order.total correct") if order_doc.get("total") == TOTAL else fail(f"order.total={order_doc.get('total')}, expected {TOTAL}")
            ok("order.shop set") if order_doc.get("shop") else fail("order.shop is empty")
            ok("order.customer_name set") if order_doc.get("customer_name") else fail("order.customer_name is empty")
            ok("order.timestamp set") if order_doc.get("timestamp") else fail("order.timestamp is None")
            ok("order.estimated_delivery set") if order_doc.get("estimated_delivery") else fail("order.estimated_delivery is None")
            info(f"  Customer: {order_doc.get('customer_name')}, Shop: {order_doc.get('shop')}, Total: Rs.{order_doc.get('total')}")
    except Exception as e:
        fail(f"DB order lookup error: {e}")

    # OrderItems
    try:
        oi_count = items_col.count_documents({"OrderID": order_id})
        ok(f"OrderItems rows saved: {oi_count}") if oi_count == 3 else fail(f"Expected 3 OrderItems rows, got {oi_count}")
    except Exception as e:
        fail(f"OrderItems lookup error: {e}")

    # Total order count increased
    orders_after = orders_col.count_documents({})
    ok("Orders count increased by 1") if orders_after == orders_before + 1 else fail(f"Orders count: before={orders_before}, after={orders_after}")

# ── TEST 4: Notifications ─────────────────────────────────────────────────────
head("TEST 4 — Notification Verification")

if user_doc and order_id:
    try:
        # Customer notification
        notif = notifs_col.find_one({
            "UserID": str(user_doc["_id"]),
            "Type": "order_placed",
            "CreatedAt": {"$gte": datetime.datetime.utcnow() - datetime.timedelta(minutes=2)}
        })
        ok(f"Customer notification created") if notif else fail("Customer order_placed notification NOT found")
        if notif:
            info(f"  Notification: {notif.get('Message', '')[:80]}")
    except Exception as e:
        fail(f"Customer notification lookup: {e}")

# Check via API
try:
    r_notif = s.get(f"{BASE_URL}/api/notifications", timeout=10)
    ok("Notifications API 200") if r_notif.status_code == 200 else fail(f"Notifications API {r_notif.status_code}")
    nd = r_notif.json()
    notifs = nd.get("notifications", [])
    order_notifs = [n for n in notifs if order_id and order_id[:8].upper() in n.get("Message", "")]
    ok(f"Order notification visible in API ({len(order_notifs)} found)") if order_notifs else fail("Order notification not visible in notifications API")
except Exception as e:
    fail(f"Notifications API error: {e}")

# ── TEST 5: My Orders page ─────────────────────────────────────────────────────
head("TEST 5 — My Orders Page")
try:
    r = s.get(f"{BASE_URL}/my_orders", timeout=10)
    ok("My Orders page loads (200)") if r.status_code == 200 else fail(f"My Orders page: HTTP {r.status_code}")
    if order_id:
        order_short = order_id[:8].upper()
        ok(f"Order #{order_short} visible on My Orders page") if order_short in r.text or order_id in r.text else fail(f"Order #{order_short} not found in My Orders HTML")
    ok("My Orders page has Pending status") if "Pending" in r.text else fail("'Pending' not found in My Orders page")
except Exception as e:
    fail(f"My Orders page error: {e}")

# ── TEST 6: Track Order page ────────────────────────────────────────────────────
head("TEST 6 — Track Order Page")
if order_id:
    try:
        r = s.get(f"{BASE_URL}/track_order/{order_id}", timeout=10)
        ok("Track Order page loads (200)") if r.status_code == 200 else fail(f"Track Order: HTTP {r.status_code}")
        ok("Track Order shows Pending status") if "Pending" in r.text or "pending" in r.text.lower() else fail("Pending status not on Track Order page")
        ok("Track Order shows order ID") if order_id[:8] in r.text or order_id in r.text else fail("Order ID not on Track Order page")
    except Exception as e:
        fail(f"Track Order page error: {e}")

# ── TEST 7: Regression — existing features ──────────────────────────────────────
head("TEST 7 — Existing Features Regression")
for label, url in [
    ("Home page", "/"),
    ("Location page", "/location"),
    ("Shops page", "/shops?loc=nanded_city"),
    ("Items page", "/items?shop_id=1&loc=nanded_city"),
    ("Profile page", "/profile"),
]:
    try:
        r = s.get(f"{BASE_URL}{url}", timeout=10)
        ok(f"{label} loads") if r.status_code == 200 else fail(f"{label}: HTTP {r.status_code}")
    except Exception as e:
        fail(f"{label}: {e}")

try:
    r = s.get(f"{BASE_URL}/api/notifications", timeout=10)
    ok("Notifications API OK") if r.status_code == 200 else fail(f"Notifications API: {r.status_code}")
except Exception as e:
    fail(f"Notifications API: {e}")

try:
    r = s.get(f"{BASE_URL}/api/shops_by_distance?loc=nanded_city&lat=19.162&lng=77.317", timeout=10)
    ok("shops_by_distance API OK") if r.status_code == 200 and r.json().get("success") else fail(f"shops_by_distance: {r.status_code}")
except Exception as e:
    fail(f"shops_by_distance API: {e}")

# ── TEST 8: DB Integrity ──────────────────────────────────────────────────────
head("TEST 8 — Database Integrity")
total_orders   = orders_col.count_documents({})
std_orders     = orders_col.count_documents({"is_uploaded": {"$ne": True}})
none_item_orders = orders_col.count_documents({"items": None})
info(f"Total orders: {total_orders} ({std_orders} standard)")
info(f"Orders with None items: {none_item_orders}")
ok("No orders have None items") if none_item_orders == 0 else fail(f"{none_item_orders} orders have None items field")
ok("Standard orders exist") if std_orders > 0 else fail("No standard orders found")

# ── Final Report ──────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  FINAL PLACE ORDER TEST REPORT")
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
    print("ALL TESTS PASSED -- PLACE ORDER FULLY FUNCTIONAL")
else:
    print(f"WARNING: {failed} test(s) need attention.")

if order_id:
    print(f"\nTest order created: {order_id}")
    print(f"  Track order: http://127.0.0.1:5000/track_order/{order_id}")
    print(f"  My Orders:   http://127.0.0.1:5000/my_orders")
print()
