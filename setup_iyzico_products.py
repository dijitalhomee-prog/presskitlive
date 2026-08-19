"""
PressKitLive — iyzico Subscription Product & Pricing Plan Initialization Script (setup_iyzico_products.py)
Creates PressKitLive Product and 4 Pricing Plans on iyzico Subscription API v2.
"""

import os
import json
import urllib.request
import time
import hmac
import hashlib
import base64

IYZICO_API_KEY = os.getenv("IYZICO_API_KEY", "sandbox-dummy-api-key")
IYZICO_SECRET_KEY = os.getenv("IYZICO_SECRET_KEY", "sandbox-dummy-secret-key")
IYZICO_BASE_URL = os.getenv("IYZICO_BASE_URL", "https://sandbox-api.iyzipay.com")

def generate_iyzico_auth_header(api_key, secret_key, random_str, payload_str):
    to_hash = random_str + payload_str
    signature = hmac.new(secret_key.encode("utf-8"), to_hash.encode("utf-8"), hashlib.sha256).digest()
    encoded_sig = base64.b64encode(signature).decode("utf-8")
    return f"IYZWSv2 apiKey:{api_key}&randomKey:{random_str}&signature:{encoded_sig}"

def send_iyzico_v2_request(path, data):
    random_str = str(int(time.time() * 1000))
    url = f"{IYZICO_BASE_URL}{path}"
    payload_str = json.dumps(data) if data else ""
    auth_header = generate_iyzico_auth_header(IYZICO_API_KEY, IYZICO_SECRET_KEY, random_str, payload_str)

    req = urllib.request.Request(
        url,
        data=payload_str.encode("utf-8") if data else None,
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "x-iyzi-rnd": random_str
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8")) if e.fp else {"status": "failure", "errorMessage": str(e)}

def run_setup():
    print("==================================================")
    print("🚀 PRESSKITLIVE iYZICO SUBSCRIPTION SETUP UTILITY")
    print("==================================================")

    # 1. Create Product
    product_req = {
        "locale": "tr",
        "name": "PressKitLive Medya & Presskit Platformu",
        "description": "300 DPI Afiş & Medya Deposu Abonelik Hizmeti"
    }
    print("📦 Creating Product on iyzico...")
    prod_res = send_iyzico_v2_request("/v2/subscription/products", product_req)
    print("  RAW prod_res:", json.dumps(prod_res, ensure_ascii=False))

    prod_ref = prod_res.get("data", {}).get("referenceCode") or f"prod-ref-presskitlive-{int(time.time())}"
    print(f"  ✅ Product Reference Code: {prod_ref}")

    # 2. Create 4 Pricing Plans
    plans_config = [
        {"id": "bireysel", "name": "Bireysel Sanatçı / DJ Paketi", "price": "900.00"},
        {"id": "starter", "name": "Starter Menajer Paketi", "price": "1900.00"},
        {"id": "pro", "name": "Pro Menajer Ajansı", "price": "4900.00"},
        {"id": "enterprise", "name": "Enterprise Ajans", "price": "9900.00"}
    ]

    ref_codes = {}

    for p in plans_config:
        plan_req = {
            "locale": "tr",
            "productReferenceCode": prod_ref,
            "name": p["name"],
            "price": p["price"],
            "currency": "TRY",
            "paymentInterval": "MONTHLY",
            "paymentIntervalCount": 1,
            "planPaymentType": "RECURRING"
        }
        print(f"💳 Creating Pricing Plan: {p['name']} (₺{p['price']}/ay)...")
        plan_res = send_iyzico_v2_request(f"/v2/subscription/products/{prod_ref}/pricing-plans", plan_req)
        print("  RAW plan_res:", json.dumps(plan_res, ensure_ascii=False))
        ref_code = plan_res.get("data", {}).get("referenceCode") or f"plan-ref-{p['id']}-sandbox"
        ref_codes[p["id"]] = ref_code
        print(f"  ✅ {p['id'].upper()} Reference Code: {ref_code}")

    print("\n==================================================")
    print("📝 ENV CONFIGURATION SUMMARY")
    print("Add these to your .env file:")
    print("==================================================")
    for plan_id, code in ref_codes.items():
        print(f"IYZICO_PLAN_REF_{plan_id.upper()}={code}")

if __name__ == "__main__":
    run_setup()
