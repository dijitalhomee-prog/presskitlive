import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from iyzico_payment import create_iyzico_checkout_form, create_subscription_checkout

print("--- Testing create_iyzico_checkout_form ---")
res1 = create_iyzico_checkout_form("pro", "dijitalgru@gmail.com", "+905376274415", "Furkan Egemen Güneş", "43306654001")
print("Status:", res1.get("status"))
print("Token:", res1.get("token"))
print("Has paymentPageUrl:", bool(res1.get("paymentPageUrl")))
print("Has checkoutFormContent:", bool(res1.get("checkoutFormContent")))

print("\n--- Testing create_subscription_checkout ---")
res2 = create_subscription_checkout("pro", "dijitalgru@gmail.com", "+905376274415", "Furkan Egemen Güneş", "43306654001")
print("Status:", res2.get("status"))
print("Token:", res2.get("token"))
print("ErrorMessage:", res2.get("raw", {}).get("errorMessage"))
