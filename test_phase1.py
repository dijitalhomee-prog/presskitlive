"""
PressKitLive — Phase 1 Multi-Manager Verification Suite (test_phase1.py)
Tests all 6 required test scenarios + Phase 1 Corrections.
"""

import urllib.request
import json
import time
import os

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
    print("🧪 RUNNING PHASE 1 MULTI-MANAGER VERIFICATION TEST SUITE")
    print("==================================================")

    ts = int(time.time())
    email_a = f"manager_a_{ts}@test.com"
    email_b = f"manager_b_{ts}@test.com"
    pass_a = "password123A"
    pass_b = "password123B"

    # TEST 1: Register two different managers
    print("\n🔹 Test 1: Registering Manager A and Manager B...")
    status1_a, body1_a, cookie_a = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": email_a, "password": pass_a, "name": "Manager A", "agencyName": "Agency A"
    })
    status1_b, body1_b, cookie_b = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": email_b, "password": pass_b, "name": "Manager B", "agencyName": "Agency B"
    })

    assert status1_a == 200, f"Manager A signup failed: {body1_a}"
    assert status1_b == 200, f"Manager B signup failed: {body1_b}"
    assert cookie_a != cookie_b, "Session tokens must be unique!"
    print(f"  ✅ Pass: Manager A ({body1_a['user']['id']}) & Manager B ({body1_b['user']['id']}) registered with unique sessions.")

    # Manager A creates an artist
    status_art, body_art, _ = make_request(f"{BASE_URL}/api/artists/create", "POST", {
        "name": f"Artist A {ts}", "genre": "Indie Rock"
    }, cookie=cookie_a)
    assert status_art == 200, f"Artist A creation failed: {body_art}"
    artist_a_id = body_art['artist']['id']
    print(f"  🎵 Manager A created Artist: '{artist_a_id}'")

    # TEST 2: Ownership Guard (Manager B attempts write operation on Manager A's artist)
    print("\n🔹 Test 2: Testing Ownership Guard (Manager B accessing Manager A's artist)...")
    status2, body2, _ = make_request(f"{BASE_URL}/api/folders/add", "POST", {
        "artistId": artist_a_id, "name": "Hacked Folder", "isLocked": False
    }, cookie=cookie_b)

    assert status2 == 403, f"Expected 403 Forbidden, got {status2}"
    print(f"  ✅ Pass: Manager B unauthorized access correctly blocked with HTTP 403 Forbidden ({body2.get('message')})")

    # TEST 3: Manager-scoped Isolation (GET /api/my-artists) & Empty State
    print("\n🔹 Test 3: Testing Manager Data Isolation & Dynamic Dashboard Loading...")
    status3_a, body3_a, _ = make_request(f"{BASE_URL}/api/my-artists", "GET", cookie=cookie_a)
    status3_b, body3_b, _ = make_request(f"{BASE_URL}/api/my-artists", "GET", cookie=cookie_b)

    mgr_a_artists = [a['id'] for a in body3_a['artists']]
    mgr_b_artists = [a['id'] for a in body3_b['artists']]

    assert artist_a_id in mgr_a_artists, "Manager A should see Artist A"
    assert artist_a_id not in mgr_b_artists, "Manager B MUST NOT see Artist A!"
    assert len(mgr_b_artists) == 0, "Manager B has 0 artists initially (Empty State)"
    print(f"  ✅ Pass: Manager A sees {mgr_a_artists}, Manager B sees {mgr_b_artists} (Empty state verified, zero data leakage).")

    # TEST 4: Persistent SQLite Sessions
    print("\n🔹 Test 4: Testing Persistent SQLite Sessions...")
    status4, body4, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie_a)
    assert status4 == 200 and body4['authenticated'] == True, "Session must be valid in SQLite database"
    print(f"  ✅ Pass: Manager A session valid in SQLite DB for user: {body4['user']['email']}")

    # TEST 5: Public Presskit Lock Redaction & Phone PII Protection
    print("\n🔹 Test 5: Testing Public Presskit Lock Redaction & Manager Phone PII Protection...")
    status5, body5, _ = make_request(f"{BASE_URL}/api/artist?artistId=yagmur-hizal", "GET")
    assert status5 == 200, "Public presskit fetch failed"
    locked_folders = set(f['id'] for f in body5['artist']['folders'] if f['isLocked'])
    public_photos = body5['artist']['pressPhotos']
    has_locked_photo = any(p['folderId'] in locked_folders for p in public_photos)
    assert not has_locked_photo, "Locked photos MUST NOT be returned to public guests!"

    # Verify Manager A's artist phone is empty (no fallback to Aycan Yağcı's phone)
    status5_a, body5_a, _ = make_request(f"{BASE_URL}/api/artist?artistId={artist_a_id}", "GET")
    assert body5_a['artist']['manager']['phone'] == "", "Manager A phone must be empty string if not provided!"
    print(f"  ✅ Pass: Public view redacts locked folder photos. Phone fallback removed (phone='').")

    # TEST 6: Legacy Migration Verification
    print("\n🔹 Test 6: Verifying Legacy Migration (Yağmur Hızal)...")
    status6, body6, _ = make_request(f"{BASE_URL}/api/artist?artistId=yagmur-hizal", "GET")
    assert status6 == 200 and body6['artist']['name'] == "Yağmur Hızal", "Legacy Yağmur Hızal artist must exist in SQLite DB"
    print(f"  ✅ Pass: Yağmur Hızal presskit page operational in SQLite DB with {len(body6['artist']['pressPhotos'])} photos.")

    # TEST 7: auth.json Cleanup Verification
    auth_json_exists = os.path.exists("assets/data/auth.json")
    assert not auth_json_exists, "Unused auth.json file must be deleted!"
    print("  ✅ Pass: Legacy auth.json file cleanly removed from project.")

    print("\n==================================================")
    print("🎉 ALL PHASE 1 CORRECTION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
