"""
PressKitLive — Solo Artist & XSS Security Verification Suite (test_section_a_b.py)
"""

import urllib.request
import json
import time

BASE_URL = "http://localhost:8080"

def make_request(url, method="GET", data=None, cookie=None):
    headers = {'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    encoded_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        res = urllib.request.urlopen(req)
        body = json.loads(res.read().decode('utf-8'))
        return res.status, body, res.headers.get('Set-Cookie')
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode('utf-8')) if e.fp else {}
        return e.code, body, None

def run_tests():
    print("==================================================")
    print("🧪 RUNNING SOLO ARTIST & SECURITY VERIFICATION SUITE")
    print("==================================================")

    ts = int(time.time())

    # 1. TEST SOLO ARTIST SIGNUP & AUTO ARTIST CREATION (Section A.3)
    print("\n🔹 Test 1: Testing Solo Artist Registration & Auto Artist Creation...")
    solo_email = f"solo_dj_{ts}@test.com"
    status1, body1, cookie1 = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": solo_email,
        "password": "password123Solo",
        "name": "DJ Maya Yılmaz",
        "accountType": "solo"
    })

    assert status1 == 200, f"Solo signup failed: {body1}"
    assert body1['user']['accountType'] == "solo", "accountType must be 'solo'"
    assert "index.html?artistId=dj-maya-yilmaz" in body1['redirect'], f"Must redirect to artist index: {body1['redirect']}"
    print(f"  ✅ Pass: Solo registration created account_type='solo' and redirected to: {body1['redirect']}")

    # 2. TEST INVALID accountType VALIDATION (Section A.7)
    print("\n🔹 Test 2: Testing Invalid accountType Validation...")
    status2, body2, _ = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": f"hacker_{ts}@test.com",
        "password": "password123Hacker",
        "name": "Hacker",
        "accountType": "invalid_type"
    })
    assert status2 == 400, f"Expected 400 Bad Request for invalid accountType, got {status2}"
    print(f"  ✅ Pass: Invalid accountType correctly rejected with HTTP 400 Bad Request ({body2.get('message')})")

    # 3. TEST XSS & SLUG SANITIZATION (Section B.1)
    print("\n🔹 Test 3: Testing XSS & Slug Sanitization with Malicious Artist Name...")
    agency_email = f"agency_xss_{ts}@test.com"
    _, _, cookie_agency = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": agency_email, "password": "password123Agency", "name": "Agency User", "accountType": "agency"
    })
    status3, body3, _ = make_request(f"{BASE_URL}/api/artists/create", "POST", {
        "name": "D'Artist <script>alert(1)</script>",
        "genre": "DJ"
    }, cookie=cookie_agency)

    assert status3 == 200, f"Artist creation failed: {body3}"
    clean_id = body3['artist']['id']
    assert "<script>" not in clean_id and "<" not in clean_id and "'" not in clean_id, f"Unsafe slug generated: {clean_id}"
    assert clean_id.startswith("dartist-scriptalert1script"), f"Unexpected slug format: {clean_id}"
    print(f"  ✅ Pass: Malicious name 'D'Artist <script>...' safely slugified to clean URL slug: '{clean_id}'")

    # 4. TEST MANAGER TITLE CUSTOMIZATION FOR SOLO ACCOUNTS (Section A.5)
    print("\n🔹 Test 4: Testing Solo Account Manager Title Customization...")
    status4, body4, _ = make_request(f"{BASE_URL}/api/artist?artistId=dj-maya-yilmaz", "GET")
    assert status4 == 200, "Artist fetch failed"
    mgr_title = body4['artist']['manager']['title']
    assert mgr_title == "Sanatçı / Doğrudan İletişim", f"Expected 'Sanatçı / Doğrudan İletişim', got '{mgr_title}'"
    print(f"  ✅ Pass: Public presskit for solo account correctly displays title: '{mgr_title}'")

    # 5. TEST iyzico CHECKOUT WITH NEW BIREYSEL PLAN (Section A.6)
    print("\n🔹 Test 5: Testing iyzico Checkout with 'bireysel' Plan...")
    status5, body5, _ = make_request(f"{BASE_URL}/api/checkout", "POST", {
        "planId": "bireysel",
        "email": solo_email,
        "identityNumber": "11111111111"
    })
    plan_obj = body5.get('plan', {}) if isinstance(body5, dict) else {}
    assert status5 == 200 and plan_obj.get('id') == "bireysel", f"Bireysel checkout failed: {body5}"
    print(f"  ✅ Pass: iyzico checkout initialized for 'bireysel' plan (Price: ₺{plan_obj.get('price')})")

    print("\n==================================================")
    print("🎉 ALL SOLO ARTIST & SECURITY TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
