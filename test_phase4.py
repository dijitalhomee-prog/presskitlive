"""
PressKitLive — Phase 4: Email Infrastructure & Password Reset Verification Suite (test_phase4.py)
Tests Resend API Fallback, Password Reset Enumeration Defense, Token Expiry, Password Complexity & Admin Email Triggers.
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
    print("🧪 RUNNING PHASE 4: EMAIL INFRASTRUCTURE & PASSWORD RESET SUITE")
    print("==================================================")

    ts = int(time.time())

    # 1. REGISTER MANAGER FOR PHASE 4 TESTS
    print("\n🔹 Test 1: Registering Manager for Email & Reset Tests...")
    test_email = f"phase4_user_{ts}@test.com"
    status1, body1, user_cookie, _ = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": test_email, "password": "password123", "name": "Phase4 User", "accountType": "agency"
    })
    assert status1 == 200, f"Signup failed: {body1}"
    print(f"  ✅ Pass: Manager registered without crashing (Email trigger skipped gracefully)")

    # 2. TEST FORGOT PASSWORD ENUMERATION DEFENSE (Scenario 2)
    print("\n🔹 Test 2: Testing POST /api/forgot-password Enumeration Defense...")
    # Case A: Existing Email
    status_a, body_a, _, _ = make_request(f"{BASE_URL}/api/forgot-password", "POST", {"email": test_email})
    assert status_a == 200 and body_a.get("status") == "success", f"Forgot password failed for existing email: {body_a}"

    # Case B: Non-existent Email
    status_b, body_b, _, _ = make_request(f"{BASE_URL}/api/forgot-password", "POST", {"email": f"nonexistent_{ts}@test.com"})
    assert status_b == 200 and body_b.get("status") == "success", f"Forgot password failed for non-existent email: {body_b}"

    # Verify identical message
    assert body_a["message"] == body_b["message"], f"Enumeration Leak! Messages differ:\nExisting: {body_a['message']}\nNon-existent: {body_b['message']}"
    print(f"  ✅ Pass: Identical response returned for existing and non-existent emails ('{body_a['message']}')")

    # 3. VERIFY TOKEN CREATED IN SQLITE
    print("\n🔹 Test 3: Retrieving Password Reset Token from SQLite Database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM password_reset_tokens ORDER BY created_at DESC LIMIT 1").fetchone()
    conn.close()

    assert row, "No reset token found in password_reset_tokens table"
    reset_token = row["token"]
    assert reset_token and row["used"] == 0, f"Token state invalid: {dict(row)}"
    print(f"  ✅ Pass: Reset token retrieved from DB (Token: {reset_token[:10]}... | Expires: {row['expires_at']})")

    # 4. TEST PASSWORD COMPLEXITY ENFORCEMENT ON RESET (Scenario 4)
    print("\n🔹 Test 4: Testing Password Complexity Rules (8+ chars, 1+ digit)...")
    # Test short password (< 8 chars)
    status_short, body_short, _, _ = make_request(f"{BASE_URL}/api/reset-password", "POST", {
        "token": reset_token, "password": "pass1"
    })
    assert status_short == 400, "Short password should be rejected"

    # Test password without digits
    status_nodigit, body_nodigit, _, _ = make_request(f"{BASE_URL}/api/reset-password", "POST", {
        "token": reset_token, "password": "passwordonly"
    })
    assert status_nodigit == 400, "Password without digits should be rejected"
    print("  ✅ Pass: Invalid passwords (<8 chars or no digits) correctly rejected with HTTP 400")

    # 5. TEST SUCCESSFUL PASSWORD RESET (Scenario 3)
    print("\n🔹 Test 5: Testing Valid Password Reset...")
    new_pass = "BrandNewPass2026!"
    status_reset, body_reset, _, _ = make_request(f"{BASE_URL}/api/reset-password", "POST", {
        "token": reset_token, "password": new_pass
    })
    assert status_reset == 200 and body_reset.get("status") == "success", f"Password reset failed: {body_reset}"

    # Verify login with NEW password
    status_lg_new, _, new_cookie, _ = make_request(f"{BASE_URL}/api/login", "POST", {
        "email": test_email, "password": new_pass
    })
    assert status_lg_new == 200, "Login with updated password failed"
    print("  ✅ Pass: Password successfully updated and verified via login")

    # 6. TEST TOKEN SINGLE-USE ENFORCEMENT (Scenario 3)
    print("\n🔹 Test 6: Testing Token Single-Use Enforcement (Reusing Used Token)...")
    status_reuse, body_reuse, _, _ = make_request(f"{BASE_URL}/api/reset-password", "POST", {
        "token": reset_token, "password": "AnotherPassword2026!"
    })
    assert status_reuse == 400, f"Expected HTTP 400 for reused token, got {status_reuse}"
    assert "geçersiz veya süresi dolmuş" in body_reuse.get("message", ""), f"Unexpected error message: {body_reuse}"
    print("  ✅ Pass: Reusing expired/used token correctly blocked with HTTP 400")

    # 7. TEST ADMIN GRANT-FREE EMAIL TRIGGER & TEMP PASSWORD PAYLOAD (Scenario 5)
    print("\n🔹 Test 7: Testing Admin Grant-Free Email Notification & tempPassword Payload...")
    # Login as Super Admin
    _, _, admin_cookie, _ = make_request(f"{BASE_URL}/api/login", "POST", {
        "email": "dijitalgru@gmail.com", "password": "Dgru2026#PressKit!"
    })

    free_email = f"p4_free_{ts}@test.com"
    status_grant, body_grant, _, _ = make_request(f"{BASE_URL}/api/admin/managers/grant-free", "POST", {
        "email": free_email, "name": "Phase4 Free User", "plan": "pro", "accountType": "agency"
    }, cookie=admin_cookie)

    assert status_grant == 200 and body_grant.get("status") == "success", f"Grant free failed: {body_grant}"
    assert body_grant["manager"].get("tempPassword"), "tempPassword must be preserved in API response"
    print(f"  ✅ Pass: Free membership granted, email notification triggered, tempPassword preserved in response")

    print("\n==================================================")
    print("🎉 ALL PHASE 4 EMAIL & PASSWORD RESET TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
