import unittest
import requests
import json
import time
import sys
import os
import threading
from datetime import datetime, timedelta
import server

PORT = int(os.getenv("PORT", 8080))
BASE_URL = f"http://127.0.0.1:{PORT}"

class TestTrialSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_thread = threading.Thread(target=server.run, daemon=True)
        cls.server_thread.start()
        for _ in range(30):
            try:
                r = requests.get(f"{BASE_URL}/api/session")
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)

    def test_7_day_trial_flow(self):
        print("\n==================================================")
        print("🧪 RUNNING 7-DAY FREE TRIAL VERIFICATION SUITE")
        print("==================================================")

        test_email = f"trial_user_{int(time.time())}@test.com"
        
        # 1. Test Trial Signup
        print("\n🔹 Test 1: Registering 7-Day Free Trial User...")
        res = requests.post(f"{BASE_URL}/api/signup-trial", json={
            "email": test_email,
            "password": "Password123",
            "name": "Test Trial Manager",
            "agencyName": "Trial Agency",
            "phone": "+905551112233",
            "accountType": "agency",
            "isTrial": True
        })
        self.assertEqual(res.status_code, 200, f"Trial signup failed: {res.text}")
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["subscriptionStatus"], "trial_active")
        self.assertIsNotNone(data["user"]["trialEndsAt"])
        self.assertGreaterEqual(data["user"]["trialDaysLeft"], 1)
        session_cookie = res.cookies.get("presskit_session")
        print(f"  ✅ Pass: Trial user created with subscriptionStatus='trial_active' (Ends: {data['user']['trialEndsAt']})")

        # 2. Test Active Session Status
        print("\n🔹 Test 2: Checking GET /api/session for Trial Status...")
        sess_res = requests.get(f"{BASE_URL}/api/session", cookies={"presskit_session": session_cookie})
        self.assertEqual(sess_res.status_code, 200)
        sess_data = sess_res.json()
        self.assertTrue(sess_data["authenticated"])
        self.assertEqual(sess_data["user"]["subscriptionStatus"], "trial_active")
        self.assertTrue(sess_data["user"]["isTrialActive"])
        self.assertFalse(sess_data["user"]["isTrialExpired"])
        print(f"  ✅ Pass: Active trial session verified (Days Left: {sess_data['user']['trialDaysLeft']})")

        # 3. Simulate Trial Expiration in SQLite DB
        print("\n🔹 Test 3: Simulating 7-Day Expiration in SQLite DB...")
        import db
        past_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with db.get_connection() as conn:
            conn.execute("UPDATE managers SET trial_ends_at = ? WHERE email = ?", (past_date, test_email))
            conn.commit()
        print(f"  ✅ Pass: Fast-forwarded trial_ends_at to past date ({past_date})")

        # 4. Test Automatic Expiration Trigger
        print("\n🔹 Test 4: Verifying Automatic Transition to 'trial_expired' (Passive Status)...")
        expired_res = requests.get(f"{BASE_URL}/api/session", cookies={"presskit_session": session_cookie})
        self.assertEqual(expired_res.status_code, 200)
        expired_data = expired_res.json()
        self.assertEqual(expired_data["user"]["subscriptionStatus"], "trial_expired")
        self.assertTrue(expired_data["user"]["isTrialExpired"])
        self.assertEqual(expired_data["user"]["trialDaysLeft"], 0)
        print("  ✅ Pass: Account automatically transitioned to 'trial_expired' (Passive Status) after 7 days!")

        print("\n==================================================")
        print("🎉 7-DAY FREE TRIAL SYSTEM VERIFIED WITH 100% SUCCESS!")
        print("==================================================")

if __name__ == "__main__":
    unittest.main()
