"""
PressKitLive — Phase 2 Verification Suite (test_phase2.py)
Tests Artist Quota Enforcement (Section A) & Dynamic /artist/<slug> URL Structure (Section B)
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
        body = json.loads(res.read().decode('utf-8')) if res.headers.get('Content-Type', '').startswith('application/json') else res.read().decode('utf-8')
        return res.status, body, res.headers.get('Set-Cookie')
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode('utf-8')) if e.fp and e.headers.get('Content-Type', '').startswith('application/json') else e.read().decode('utf-8')
        return e.code, body, None

def run_tests():
    print("==================================================")
    print("🧪 RUNNING PHASE 2 VERIFICATION SUITE")
    print("==================================================")

    ts = int(time.time())

    # TEST 1: Starter Manager Quota Limit (Limit = 4)
    print("\n🔹 Test 1: Testing Starter Manager Quota Enforcement (Limit = 4)...")
    email_starter = f"mgr_starter_{ts}@test.com"
    status_s, body_s, cookie_s = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": email_starter, "password": "password123Starter", "name": "Starter Manager", "accountType": "agency"
    })
    assert status_s == 200, f"Starter signup failed: {body_s}"

    # Create 4 artists
    for i in range(1, 5):
        s_art, b_art, _ = make_request(f"{BASE_URL}/api/artists/create", "POST", {
            "name": f"Starter Artist {i} {ts}", "genre": "Pop"
        }, cookie=cookie_s)
        assert s_art == 200, f"Artist {i} creation failed: {b_art}"
    print("  🎵 4 Artists successfully created for Starter manager.")

    # Attempt 5th artist creation -> HTTP 403 Forbidden
    s_art5, b_art5, _ = make_request(f"{BASE_URL}/api/artists/create", "POST", {
        "name": f"Starter Artist 5 {ts}", "genre": "Pop"
    }, cookie=cookie_s)

    assert s_art5 == 403, f"Expected 403 Forbidden for exceeding Starter quota, got {s_art5}"
    assert "Plan limitinize ulaştınız (4 sanatçı)" in b_art5.get('message', ''), f"Unexpected message: {b_art5}"
    print(f"  ✅ Pass: 5th Artist creation correctly blocked with HTTP 403 Forbidden ({b_art5.get('message')})")

    # TEST 2: Solo Account Quota Limit (Limit = 1)
    print("\n🔹 Test 2: Testing Solo Account Quota Enforcement (Limit = 1)...")
    email_solo = f"solo_artist_{ts}@test.com"
    status_solo, body_solo, cookie_solo = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": email_solo, "password": "password123Solo", "name": "Solo DJ", "accountType": "solo"
    })
    assert status_solo == 200, "Solo signup failed"

    # Solo signup auto-creates 1 artist. Attempting a 2nd artist creation via API -> HTTP 403 Forbidden
    s_solo2, b_solo2, _ = make_request(f"{BASE_URL}/api/artists/create", "POST", {
        "name": "Second Solo Artist", "genre": "DJ"
    }, cookie=cookie_solo)

    assert s_solo2 == 403, f"Expected 403 Forbidden for exceeding Solo quota, got {s_solo2}"
    assert "Plan limitinize ulaştınız (1 sanatçı)" in b_solo2.get('message', ''), f"Unexpected message: {b_solo2}"
    print(f"  ✅ Pass: 2nd Artist creation for Solo account blocked with HTTP 403 Forbidden ({b_solo2.get('message')})")

    # TEST 3: GET /api/session & GET /api/my-artists quotaLimit Verification
    print("\n🔹 Test 3: Testing quotaLimit Payload in /api/session & /api/my-artists...")
    status_sess, body_sess, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie_s)
    status_myart, body_myart, _ = make_request(f"{BASE_URL}/api/my-artists", "GET", cookie=cookie_s)

    assert body_sess['user']['quotaLimit'] == 4, f"Expected session quotaLimit=4, got {body_sess['user'].get('quotaLimit')}"
    assert body_myart['quotaLimit'] == 4, f"Expected my-artists quotaLimit=4, got {body_myart.get('quotaLimit')}"
    print("  ✅ Pass: Server returns accurate quotaLimit=4 for Starter plan.")

    # TEST 4: Clean Dynamic /artist/<slug> URL Rewrite
    print("\n🔹 Test 4: Testing Clean Dynamic /artist/<slug> URL Rewrite...")
    status_clean, body_clean, _ = make_request(f"{BASE_URL}/artist/yagmur-hizal", "GET")
    assert status_clean == 200 and ("PressKitLive" in str(body_clean) or "public.html" in str(body_clean)), "Clean URL /artist/yagmur-hizal fetch failed"
    print("  ✅ Pass: /artist/yagmur-hizal successfully served clean presskit page (200 OK).")

    # TEST 5: Custom 404 Page for Invalid Slug
    print("\n🔹 Test 5: Testing Custom 404 Page for Invalid Slug...")
    status_404, body_404, _ = make_request(f"{BASE_URL}/artist/non-existent-artist-slug-999", "GET")
    assert status_404 == 404 and "Sanatçı Bulunamadı" in str(body_404), f"Expected 404 custom page, got status {status_404}"
    print("  ✅ Pass: /artist/non-existent-artist-slug-999 correctly returns custom 404.html page (404 Not Found).")

    # TEST 6: Legacy URL Compatibility
    print("\n🔹 Test 6: Verifying Legacy public.html?artistId=... URL Compatibility...")
    status_leg, body_leg, _ = make_request(f"{BASE_URL}/public.html?artistId=yagmur-hizal", "GET")
    assert status_leg == 200 and ("PressKitLive" in str(body_leg) or "public.html" in str(body_leg)), "Legacy public.html URL fetch failed"
    print("  ✅ Pass: Legacy public.html?artistId=yagmur-hizal remains fully operational.")

    print("\n==================================================")
    print("🎉 ALL PHASE 2 TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
