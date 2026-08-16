"""
PressKitLive — Super Admin, Complimentary Memberships & Impersonation Suite (test_admin_impersonation.py)
Tests Super Admin Security Guards, Free Granting, Member Listing, Impersonation & Audit Logs.
"""

import urllib.request
import urllib.parse
import json
import time
import sqlite3
import os

BASE_URL = "http://localhost:8080"
DB_PATH = "assets/data/presskit.db"

def make_request(url, method="GET", data=None, cookie=None, follow_redirects=False):
    headers = {'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    encoded_data = json.dumps(data).encode('utf-8') if data else None

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not follow_redirects:
                return None
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(NoRedirectHandler())
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        res = opener.open(req)
        body = json.loads(res.read().decode('utf-8')) if res.headers.get('Content-Type', '').startswith('application/json') else res.read().decode('utf-8')
        return res.status, body, res.headers.get('Set-Cookie'), res.headers.get('Location')
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode('utf-8')) if e.fp and e.headers.get('Content-Type', '').startswith('application/json') else e.read().decode('utf-8')
        return e.code, body, e.headers.get('Set-Cookie'), e.headers.get('Location')

def run_tests():
    print("==================================================")
    print("🧪 RUNNING SUPER ADMIN & IMPERSONATION SUITE")
    print("==================================================")

    ts = int(time.time())

    # 1. REGISTER NORMAL MANAGER (is_super_admin = 0)
    print("\n🔹 Test 1: Registering Normal Non-Admin Manager...")
    normal_email = f"normal_mgr_{ts}@test.com"
    status1, body1, normal_cookie, _ = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": normal_email, "password": "password123", "name": "Normal Manager", "accountType": "agency"
    })
    assert status1 == 200, f"Normal manager signup failed: {body1}"
    print(f"  ✅ Pass: Normal manager registered ({normal_email})")

    # 2. TEST UNAUTHORIZED /admin.html ACCESS (Scenario 1)
    print("\n🔹 Test 2: Testing /admin.html Page Guard for Normal Manager...")
    status2, _, _, loc2 = make_request(f"{BASE_URL}/admin.html", "GET", cookie=normal_cookie, follow_redirects=False)
    assert status2 == 302 and loc2 == "/login.html", f"Expected 302 redirect to /login.html, got {status2} (Loc: {loc2})"
    print("  ✅ Pass: Normal manager correctly redirected away from /admin.html (302 -> /login.html)")

    # 3. TEST UNAUTHORIZED /api/admin/managers ACCESS (Scenario 2)
    print("\n🔹 Test 3: Testing /api/admin/managers API Guard for Normal Manager...")
    status3, body3, _, _ = make_request(f"{BASE_URL}/api/admin/managers", "GET", cookie=normal_cookie)
    assert status3 == 403, f"Expected HTTP 403 Forbidden, got {status3}"
    print("  ✅ Pass: Unauthorized API call correctly blocked with HTTP 403 Forbidden")

    # 4. LOGIN AS SUPER ADMINS (dijitalgru@gmail.com & hilalbalbayyy@gmail.com)
    print("\n🔹 Test 4: Logging in as Primary Super Admin (dijitalgru@gmail.com)...")
    status_ad, body_ad, admin_cookie, _ = make_request(f"{BASE_URL}/api/login", "POST", {
        "email": "dijitalgru@gmail.com", "password": "Dgru2026#PressKit!"
    })
    assert status_ad == 200, f"Super admin login failed: {body_ad}"
    print("  ✅ Pass: Primary Super Admin (dijitalgru@gmail.com) logged in successfully")

    print("\n🔹 Test 4b: Logging in as Second Super Admin (hilalbalbayyy@gmail.com)...")
    status_ad2, body_ad2, admin_cookie2, _ = make_request(f"{BASE_URL}/api/login", "POST", {
        "email": "hilalbalbayyy@gmail.com", "password": "Dgru2026#PressKit!"
    })
    assert status_ad2 == 200, f"Second super admin login failed: {body_ad2}"
    print("  ✅ Pass: Second Super Admin (hilalbalbayyy@gmail.com) logged in successfully")

    # 5. GRANT FREE COMPLIMENTARY MEMBERSHIP (Scenario 3)
    print("\n🔹 Test 5: Testing POST /api/admin/managers/grant-free...")
    free_email = f"free_user_{ts}@test.com"
    status5, body5, _, _ = make_request(f"{BASE_URL}/api/admin/managers/grant-free", "POST", {
        "email": free_email, "name": "Free User", "plan": "pro", "accountType": "agency"
    }, cookie=admin_cookie)

    assert status5 == 200 and body5.get("status") == "success", f"Grant free failed: {body5}"
    temp_pwd = body5["manager"]["tempPassword"]
    assert temp_pwd, "tempPassword must be returned"
    print(f"  ✅ Pass: Free membership created for {free_email} (Temp Password: {temp_pwd})")

    # Test login with temp password
    status_lg_free, body_lg_free, free_cookie, _ = make_request(f"{BASE_URL}/api/login", "POST", {
        "email": free_email, "password": temp_pwd
    })
    assert status_lg_free == 200, "Free manager login with temp password failed"
    _, free_sess, _, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=free_cookie)
    assert free_sess["user"]["subscriptionStatus"] == "complimentary", f"Expected 'complimentary', got {free_sess['user']['subscriptionStatus']}"
    print("  ✅ Pass: Free manager logged in cleanly; verified subscriptionStatus = 'complimentary'")

    # 6. GET ALL MANAGERS LIST (Scenario 4)
    print("\n🔹 Test 6: Testing GET /api/admin/managers Data Payload & Sanitization...")
    status6, body6, _, _ = make_request(f"{BASE_URL}/api/admin/managers", "GET", cookie=admin_cookie)
    assert status6 == 200 and body6.get("status") == "success", f"Get managers failed: {body6}"
    managers = body6.get("managers", [])
    assert len(managers) >= 2, "Must return registered managers"
    
    for m in managers:
        assert "password_hash" not in m and "salt" not in m, f"PII Security Leak: password_hash or salt found in manager {m['id']}"
    print(f"  ✅ Pass: Returned {len(managers)} managers; verified zero password_hash/salt data leakage")

    # 7. START IMPERSONATION (Scenario 5)
    print("\n🔹 Test 7: Testing Support Impersonation (POST /api/admin/impersonate)...")
    target_mgr = [m for m in managers if m["email"] == normal_email][0]
    status7, body7, imp_cookie, _ = make_request(f"{BASE_URL}/api/admin/impersonate", "POST", {
        "managerId": target_mgr["id"]
    }, cookie=admin_cookie)

    assert status7 == 200 and body7.get("redirect") == "/agency_dashboard.html", f"Impersonation failed: {body7}"
    print(f"  ✅ Pass: Impersonation session created for target: {normal_email}")

    # Verify accessing target manager's artists with imp_cookie
    status_art, body_art, _, _ = make_request(f"{BASE_URL}/api/my-artists", "GET", cookie=imp_cookie)
    assert status_art == 200, "Impersonated my-artists fetch failed"
    print("  ✅ Pass: Impersonated session successfully fetched target manager's artists")

    # 8. VERIFY IMPERSONATION SESSION PAYLOAD (Scenario 6)
    print("\n🔹 Test 8: Verifying GET /api/session Impersonation Flag...")
    status8, body8, _, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=imp_cookie)
    assert status8 == 200 and body8.get("authenticated") is True, f"Session check failed: {body8}"
    imp_data = body8["user"].get("impersonation")
    assert imp_data and imp_data.get("active") is True, f"Expected impersonation.active=True, got {imp_data}"
    log_id = imp_data.get("logId")
    assert log_id, "logId must be present in impersonation payload"
    print(f"  ✅ Pass: GET /api/session returned impersonation.active = True (Admin: {imp_data.get('adminName')})")

    # 9. END IMPERSONATION (Scenario 7)
    print("\n🔹 Test 9: Testing POST /api/admin/end-impersonation...")
    status9, body9, restored_admin_cookie, _ = make_request(f"{BASE_URL}/api/admin/end-impersonation", "POST", {}, cookie=imp_cookie)
    assert status9 == 200 and body9.get("redirect") == "/admin.html", f"End impersonation failed: {body9}"

    # Verify session is restored back to Super Admin
    _, body9_sess, _, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=restored_admin_cookie)
    assert body9_sess["user"]["isSuperAdmin"] is True, "Restored session must be Super Admin"
    assert body9_sess["user"].get("impersonation") is None, "Impersonation info must be cleared"
    print("  ✅ Pass: Restored session back to Super Admin cleanly (impersonation = None)")

    # 10. VERIFY AUDIT LOG IN SQLITE (Scenario 8)
    print("\n🔹 Test 10: Verifying impersonation_log SQLite Database Audit Trail...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM impersonation_log WHERE id = ?", (log_id,)).fetchone()
    conn.close()

    assert row, f"Log entry {log_id} not found in database"
    log_dict = dict(row)
    assert log_dict["started_at"] and log_dict["ended_at"], f"Audit trail incomplete: {log_dict}"
    print(f"  ✅ Pass: Audit log verified in SQLite DB (Started: {log_dict['started_at']} | Ended: {log_dict['ended_at']})")

    print("\n==================================================")
    print("🎉 ALL SUPER ADMIN & IMPERSONATION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
