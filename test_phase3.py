"""
PressKitLive — Phase 3 Subscription Verification Suite (test_phase3.py)
Tests Recurring Payments, Upgrades, Cancellations, and Webhook Notifications.
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
    print("🧪 RUNNING PHASE 3 SUBSCRIPTION VERIFICATION SUITE")
    print("==================================================")

    ts = int(time.time())

    # 1. REGISTER MANAGER ACCOUNT
    print("\n🔹 Test 1: Registering Manager for Subscription Flow...")
    email = f"sub_manager_{ts}@test.com"
    status_reg, body_reg, cookie = make_request(f"{BASE_URL}/api/signup", "POST", {
        "email": email, "password": "password123Sub", "name": "Sub Manager", "accountType": "agency"
    })
    assert status_reg == 200, "Manager signup failed"
    print(f"  ✅ Pass: Manager registered successfully ({email})")

    # 2. SUBSCRIBE INITIALIZE (POST /api/subscribe)
    print("\n🔹 Test 2: Testing POST /api/subscribe (Subscription Checkout Initialization)...")
    status_sub, body_sub, _ = make_request(f"{BASE_URL}/api/subscribe", "POST", {
        "planId": "starter",
        "identityNumber": "11111111111"
    }, cookie=cookie)

    assert status_sub == 200 and body_sub.get("status") == "success", f"Subscribe failed: {body_sub}"
    token = body_sub.get("token")
    assert token, "Token must be returned in subscription checkout"
    print(f"  ✅ Pass: Subscription checkout form initialized with token: {token}")

    # Verify session status is pending
    _, sess_b1, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie)
    assert sess_b1['user']['subscriptionStatus'] == "pending", f"Expected 'pending', got {sess_b1['user']['subscriptionStatus']}"
    print("  ✅ Pass: Session status correctly updated to 'pending'")

    # 3. CALLBACK ACTIVATION (POST /iyzico_callback)
    print("\n🔹 Test 3: Simulating Callback Activation...")
    callback_data = f"token={token}"
    req_cb = urllib.request.Request(f"{BASE_URL}/iyzico_callback", data=callback_data.encode(), headers={'Cookie': cookie, 'Content-Type': 'application/x-www-form-urlencoded'}, method="POST")
    res_cb = urllib.request.urlopen(req_cb)
    assert res_cb.status == 200, "Callback failed"

    # Verify session status is now active
    _, sess_b2, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie)
    assert sess_b2['user']['subscriptionStatus'] == "active", f"Expected 'active', got {sess_b2['user']['subscriptionStatus']}"
    print("  ✅ Pass: Subscription activated via callback (Status: active)")

    # 4. SUBSCRIPTION UPGRADE (POST /api/subscription/upgrade)
    print("\n🔹 Test 4: Testing Subscription Upgrade (Starter -> Pro)...")
    status_up, body_up, _ = make_request(f"{BASE_URL}/api/subscription/upgrade", "POST", {
        "planId": "pro"
    }, cookie=cookie)

    assert status_up == 200 and body_up.get("status") == "success", f"Upgrade failed: {body_up}"
    assert body_up.get("quotaLimit") == 10, f"Expected quotaLimit=10, got {body_up.get('quotaLimit')}"

    # Verify session reflects new plan and quota limit
    _, sess_b3, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie)
    assert sess_b3['user']['plan'] == "pro" and sess_b3['user']['quotaLimit'] == 10, "Upgrade failed to update session"
    print("  ✅ Pass: Subscription upgraded to PRO (New Quota Limit: 10 Artists)")

    # 5. SUBSCRIPTION CANCEL (POST /api/subscription/cancel)
    print("\n🔹 Test 5: Testing Subscription Cancellation (POST /api/subscription/cancel)...")
    status_can, body_can, _ = make_request(f"{BASE_URL}/api/subscription/cancel", "POST", {}, cookie=cookie)

    assert status_can == 200 and body_can.get("status") == "success", f"Cancel failed: {body_can}"
    assert body_can.get("subscriptionStatus") == "cancelling", "Status must be 'cancelling'"

    # Verify session reflects cancelling status
    _, sess_b4, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie)
    assert sess_b4['user']['subscriptionStatus'] == "cancelling", f"Expected 'cancelling', got {sess_b4['user']['subscriptionStatus']}"
    print(f"  ✅ Pass: Cancel request recorded safely ({body_can.get('message')})")

    # 6. WEBHOOK NOTIFICATION (POST /iyzico/webhook)
    print("\n🔹 Test 6: Testing Webhook Notification Handling (Payment Failure Simulation)...")
    status_wh, body_wh, _ = make_request(f"{BASE_URL}/iyzico/webhook", "POST", {
        "event": "subscription.payment.failed",
        "subscriptionReferenceCode": token,
        "status": "FAILURE"
    }, cookie=cookie)

    assert status_wh == 200 and body_wh.get("status") == "success", f"Webhook failed: {body_wh}"

    # Verify session reflects payment_failed status
    _, sess_b5, _ = make_request(f"{BASE_URL}/api/session", "GET", cookie=cookie)
    assert sess_b5['user']['subscriptionStatus'] == "payment_failed", f"Expected 'payment_failed', got {sess_b5['user']['subscriptionStatus']}"
    print("  ✅ Pass: Webhook correctly updated manager subscriptionStatus to 'payment_failed'")

    print("\n==================================================")
    print("🎉 ALL PHASE 3 SUBSCRIPTION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
