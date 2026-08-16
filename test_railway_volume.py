"""
Test Suite: PressKitLive™ Railway Volume & DATA_ROOT Persistence Verification
"""
import os
import shutil
import json
import urllib.request
import base64
import sqlite3
import time
import unittest

BASE_URL = "http://localhost:8080"
TEST_DATA_ROOT = "/tmp/presskit_railway_test_volume"

class TestRailwayVolumePersistence(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_DATA_ROOT):
            shutil.rmtree(TEST_DATA_ROOT, ignore_errors=True)

    def tearDown(self):
        if os.path.exists(TEST_DATA_ROOT):
            shutil.rmtree(TEST_DATA_ROOT, ignore_errors=True)

    def test_01_railway_json_exists_and_configured(self):
        print("\n🔹 Test 1: Verifying railway.json configuration...")
        railway_json_path = os.path.join(os.path.dirname(__file__), "railway.json")
        self.assertTrue(os.path.exists(railway_json_path), "railway.json file must exist in project root")
        
        with open(railway_json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        self.assertEqual(config.get("build", {}).get("builder"), "NIXPACKS")
        self.assertEqual(config.get("deploy", {}).get("startCommand"), "python3 server.py")
        self.assertEqual(config.get("deploy", {}).get("overlapSeconds"), 0, "overlapSeconds must be 0 for SQLite safety")
        print("  ✅ Pass: railway.json valid with NIXPACKS & overlapSeconds=0")

    def test_02_gitignore_database_rules(self):
        print("\n🔹 Test 2: Verifying .gitignore rules for SQLite database security...")
        gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path))
        
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.assertIn("assets/data/*.db", content)
        self.assertIn("*.db", content)
        print("  ✅ Pass: .gitignore properly excludes local database files")

    def test_03_data_root_isolation(self):
        print("\n🔹 Test 3: Verifying DATA_ROOT unified directory structure & image saving...")
        os.environ["DATA_ROOT"] = TEST_DATA_ROOT
        import importlib
        import db
        importlib.reload(db)
        
        self.assertEqual(db.DATA_ROOT, TEST_DATA_ROOT)
        self.assertEqual(db.DB_PATH, os.path.join(TEST_DATA_ROOT, "data", "presskit.db"))
        self.assertEqual(db.IMAGES_ROOT, os.path.join(TEST_DATA_ROOT, "images"))
        
        self.assertTrue(os.path.exists(os.path.join(TEST_DATA_ROOT, "data")))
        self.assertTrue(os.path.exists(os.path.join(TEST_DATA_ROOT, "images")))
        
        # Test base64 image upload saving
        sample_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        saved_url = db.save_uploaded_image(sample_b64, "test_upload")
        
        self.assertTrue(saved_url.startswith("/assets/images/test_upload_"))
        filename = saved_url.replace("/assets/images/", "")
        saved_file_path = os.path.join(db.IMAGES_ROOT, filename)
        
        self.assertTrue(os.path.exists(saved_file_path), f"File {saved_file_path} must exist in IMAGES_ROOT")
        self.assertGreater(os.path.getsize(saved_file_path), 0)
        print(f"  ✅ Pass: Uploaded image saved to unified Volume directory: {saved_file_path}")
        
        # Cleanup env override
        del os.environ["DATA_ROOT"]
        importlib.reload(db)

    def test_04_live_server_api_upload_endpoint(self):
        print("\n🔹 Test 4: Testing POST /api/upload endpoint on live server...")
        # 1. Register & login a test manager to get session cookie
        signup_payload = json.dumps({
            "name": "Volume Test Manager",
            "email": f"volume_test_{int(time.time())}@test.com",
            "password": "Password123!",
            "phone": "05551234567"
        }).encode('utf-8')
        
        signup_req = urllib.request.Request(
            f"{BASE_URL}/api/signup",
            data=signup_payload,
            headers={"Content-Type": "application/json"}
        )
        
        cookie_header = None
        with urllib.request.urlopen(signup_req) as s_resp:
            cookie_header = s_resp.headers.get("Set-Cookie")
        
        self.assertIsNotNone(cookie_header)

        # 2. Upload image via POST /api/upload with session cookie
        sample_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        payload = json.dumps({"dataUrl": sample_b64}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/upload",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Cookie": cookie_header
            }
        )
        
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        self.assertEqual(data.get("status"), "success")
        uploaded_url = data.get("url")
        self.assertTrue(uploaded_url.startswith("/assets/images/user_upload_"))
        print(f"  ✅ Pass: Real binary image upload succeeded -> {uploaded_url}")
        
        # Test fetching the uploaded image via GET /assets/images/...
        img_req = urllib.request.Request(f"{BASE_URL}{uploaded_url}")
        with urllib.request.urlopen(img_req) as img_resp:
            self.assertEqual(img_resp.status, 200)
            self.assertEqual(img_resp.headers.get("Content-Type"), "image/png")
            img_content = img_resp.read()
            self.assertGreater(len(img_content), 0)
        print("  ✅ Pass: Served uploaded image via HTTP 200 OK from IMAGES_ROOT")

if __name__ == "__main__":
    unittest.main()
