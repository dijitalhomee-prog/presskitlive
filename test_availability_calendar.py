import unittest
import requests
import json
import time
import db

BASE_URL = "http://127.0.0.1:8080"

class TestAvailabilityCalendar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create test manager 1 & artist
        cls.mgr1_email = f"cal_mgr1_{int(time.time())}@test.com"
        cls.mgr1_pwd = "Password123"
        cls.session1 = requests.Session()

        res1 = cls.session1.post(f"{BASE_URL}/api/signup", json={
            "email": cls.mgr1_email,
            "password": cls.mgr1_pwd,
            "name": "Calendar Manager 1",
            "agencyName": "Cal Agency",
            "phone": "+905551112233",
            "accountType": "agency"
        })
        assert res1.status_code == 200, f"Signup failed: {res1.text}"

        # Create artist for mgr 1
        res_art = cls.session1.post(f"{BASE_URL}/api/artists/create", json={
            "name": "Calendar Test Artist",
            "genre": "Actor / Stage"
        })
        assert res_art.status_code == 200, f"Artist create failed: {res_art.text}"
        cls.artist1 = res_art.json()["artist"]

        # Create test manager 2 (unauthorized)
        cls.mgr2_email = f"cal_mgr2_{int(time.time())}@test.com"
        cls.session2 = requests.Session()
        res2 = cls.session2.post(f"{BASE_URL}/api/signup", json={
            "email": cls.mgr2_email,
            "password": cls.mgr1_pwd,
            "name": "Calendar Manager 2",
            "agencyName": "Other Agency",
            "phone": "+905559998877",
            "accountType": "agency"
        })
        assert res2.status_code == 200

    def test_01_get_empty_availability(self):
        """Test fetching availability for newly created artist."""
        res = self.session1.get(f"{BASE_URL}/api/artist/availability?artistId={self.artist1['id']}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["availability"], list)

    def test_02_toggle_date_availability(self):
        """Test adding/updating availability status and notes."""
        date_str = "2026-09-15"
        res = self.session1.post(f"{BASE_URL}/api/artist/availability/toggle", json={
            "artistId": self.artist1["id"],
            "date": date_str,
            "status": "booked",
            "title": "Harbiye Open Air Concert"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

        # Verify via GET
        res_get = self.session1.get(f"{BASE_URL}/api/artist/availability?artistId={self.artist1['id']}")
        self.assertEqual(res_get.status_code, 200)
        avail = res_get.json()["availability"]
        matched = [a for a in avail if a["date"] == date_str]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["status"], "booked")
        self.assertEqual(matched[0]["title"], "Harbiye Open Air Concert")

    def test_02b_multi_date_availability_range(self):
        """Test drag-to-select range setting multiple dates at once."""
        dates = ["2026-09-18", "2026-09-19", "2026-09-20"]
        res = self.session1.post(f"{BASE_URL}/api/artist/availability/toggle", json={
            "artistId": self.artist1["id"],
            "dates": dates,
            "status": "option",
            "title": "Turne Opsiyonu"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

        res_get = self.session1.get(f"{BASE_URL}/api/artist/availability?artistId={self.artist1['id']}")
        avail = res_get.json()["availability"]
        matched = [a for a in avail if a["date"] in dates]
        self.assertEqual(len(matched), 3)
        for m in matched:
            self.assertEqual(m["status"], "option")
            self.assertEqual(m["title"], "Turne Opsiyonu")

    def test_03_unauthorized_update_blocked(self):
        """Test that manager 2 cannot modify manager 1's artist availability."""
        res = self.session2.post(f"{BASE_URL}/api/artist/availability/toggle", json={
            "artistId": self.artist1["id"],
            "date": "2026-09-20",
            "status": "available",
            "title": "Unauthorized Edit"
        })
        self.assertEqual(res.status_code, 403)

    def test_04_clear_date_availability(self):
        """Test clearing date availability."""
        date_str = "2026-09-15"
        res = self.session1.post(f"{BASE_URL}/api/artist/availability/toggle", json={
            "artistId": self.artist1["id"],
            "date": date_str,
            "status": "clear"
        })
        self.assertEqual(res.status_code, 200)

        res_get = self.session1.get(f"{BASE_URL}/api/artist/availability?artistId={self.artist1['id']}")
        avail = res_get.json()["availability"]
        matched = [a for a in avail if a["date"] == date_str]
        self.assertEqual(len(matched), 0)

if __name__ == "__main__":
    print("🧪 Running Availability Calendar Automated Test Suite...")
    unittest.main()
