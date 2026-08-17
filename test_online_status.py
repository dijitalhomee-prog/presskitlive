import urllib.request
import json
import sqlite3
import time
import os
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8080"

def make_request(url, method="GET", data=None, cookie=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    
    body = json.dumps(data).encode("utf-8") if data else None
    try:
        with urllib.request.urlopen(req, data=body) as res:
            res_body = res.read().decode("utf-8")
            set_cookie = res.headers.get("Set-Cookie")
            return res.status, json.loads(res_body) if res_body else {}, set_cookie
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        return e.code, json.loads(res_body) if res_body else {}, None

def run_tests():
    print("==================================================")
    print("🧪 RUNNING ONLINE USER ACTIVITY TRACKING TEST SUITE")
    print("==================================================")

    # Test 1: Verify database schema migration (last_activity_at column in sessions)
    print("\n🔹 Test 1: Verifying SQLite schema migration (last_activity_at column)...")
    db_path = "assets/data/presskit.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(sessions);")
    cols = [col[1] for col in cursor.fetchall()]
    assert "last_activity_at" in cols, "last_activity_at column missing from sessions table!"
    print("  ✅ Pass: 'last_activity_at' column verified in 'sessions' table.")

    # Test 2: Register manager and test touch_session_activity & isOnline
    print("\n🔹 Test 2: Registering active manager and verifying isOnline = True...")
    ts = int(time.time())
    status, body, cookie = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": f"online_mgr_{ts}@test.com",
        "password": "Password123!",
        "name": f"Online Manager {ts}",
        "agencyName": "Online Agency"
    })
    assert status == 200, f"Signup failed: {body}"
    online_mgr_id = body["user"]["id"]

    # Login as Super Admin to inspect GET /api/admin/managers
    status_admin, body_admin, cookie_admin = make_request(f"{BASE_URL}/api/login", "POST", {
        "email": "dijitalgru@gmail.com",
        "password": "Dgru2026#PressKit!"
    })
    assert status_admin == 200, "Super admin login failed"

    status_list, body_list, _ = make_request(f"{BASE_URL}/api/admin/managers", "GET", cookie=cookie_admin)
    assert status_list == 200, "GET /api/admin/managers failed"
    managers = body_list["managers"]

    target_mgr = next((m for m in managers if m["id"] == online_mgr_id), None)
    assert target_mgr is not None, "Newly registered manager not found in admin list"
    assert target_mgr["isOnline"] is True, f"Expected isOnline=True, got {target_mgr.get('isOnline')}"
    print(f"  ✅ Pass: Active manager '{target_mgr['name']}' returned isOnline=True in /api/admin/managers payload.")

    # Test 3: Simulating offline manager (>5 min inactivity)
    print("\n🔹 Test 3: Simulating inactive session (>5 minutes) and verifying isOnline = False...")
    old_time = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE sessions SET last_activity_at = ? WHERE manager_id = ?", (old_time, online_mgr_id))
    conn.commit()

    status_list2, body_list2, _ = make_request(f"{BASE_URL}/api/admin/managers", "GET", cookie=cookie_admin)
    managers2 = body_list2["managers"]
    target_mgr2 = next((m for m in managers2 if m["id"] == online_mgr_id), None)
    assert target_mgr2["isOnline"] is False, f"Expected isOnline=False for inactive manager, got {target_mgr2.get('isOnline')}"
    print("  ✅ Pass: Inactive manager (>5 min) correctly identified as isOnline=False.")

    # Test 4: Touching session activity (making request updates last_activity_at)
    print("\n🔹 Test 4: Making request with user session to touch activity...")
    make_request(f"{BASE_URL}/api/my-artists", "GET", cookie=cookie)
    
    status_list3, body_list3, _ = make_request(f"{BASE_URL}/api/admin/managers", "GET", cookie=cookie_admin)
    managers3 = body_list3["managers"]
    target_mgr3 = next((m for m in managers3 if m["id"] == online_mgr_id), None)
    assert target_mgr3["isOnline"] is True, "Session activity touch failed to set isOnline=True"
    print("  ✅ Pass: User request cleanly touched session activity and restored isOnline=True.")

    conn.close()

    print("\n==================================================")
    print("🎉 ALL ONLINE USER ACTIVITY TESTS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
