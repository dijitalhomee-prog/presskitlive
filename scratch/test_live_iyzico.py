import os
import json
import iyzipay

# Load live keys
api_key = os.getenv("IYZICO_API_KEY", "jhRCXfZH3RCEhT5DX6F5SPmE1mCX4j85")
secret_key = os.getenv("IYZICO_SECRET_KEY", "J6YBz6nvl4MyWr5YFSd7pc62B9LPr6Bn")
base_url = "https://api.iyzipay.com"
if base_url.startswith("https://"):
    base_url_clean = base_url.replace("https://", "")
elif base_url.startswith("http://"):
    base_url_clean = base_url.replace("http://", "")
else:
    base_url_clean = base_url

print(f"Testing live iyzico connection with API Key: {api_key[:6]}... Target: {base_url}")

options = {
    'api_key': api_key,
    'secret_key': secret_key,
    'base_url': base_url_clean
}

request = {
    'locale': 'tr',
    'conversationId': 'PKL_TEST_LIVE_001',
    'price': '1080.00',
    'paidPrice': '1080.00',
    'currency': 'TRY',
    'basketId': 'BASKET_PRO_LIVE_001',
    'paymentGroup': 'PRODUCT',
    'callbackUrl': 'https://presskitlive.com/iyzico_callback',
    'buyer': {
        'id': 'BY_TEST_001',
        'name': 'Furkan Egemen',
        'surname': 'Güneş',
        'gsmNumber': '+905376274415',
        'email': 'dijitalgru@gmail.com',
        'identityNumber': '43306654001',
        'registrationAddress': 'Gülbahar Mah. No 34 Kat 3 Daire 11, Şişli',
        'ip': '85.100.1.1',
        'city': 'Istanbul',
        'country': 'Turkey'
    },
    'shippingAddress': {
        'contactName': 'Furkan Egemen Güneş',
        'city': 'Istanbul',
        'country': 'Turkey',
        'address': 'Gülbahar Mah. No 34 Kat 3 Daire 11, Şişli',
        'zipCode': '34394'
    },
    'billingAddress': {
        'contactName': 'Furkan Egemen Güneş',
        'city': 'Istanbul',
        'country': 'Turkey',
        'address': 'Gülbahar Mah. No 34 Kat 3 Daire 11, Şişli',
        'zipCode': '34394'
    },
    'basketItems': [
        {
            'id': 'BI_PRO_PLAN',
            'name': 'PressKitLive Pro Menajer Ajansı Aboneliği',
            'category1': 'SaaS Platform',
            'category2': 'Presskit Membership',
            'itemType': 'VIRTUAL',
            'price': '1080.00'
        }
    ]
}

response = iyzipay.CheckoutFormInitialize().create(request, options)
res_dict = json.loads(response.read().decode('utf-8'))
print("\nResponse Status:", res_dict.get("status"))
print("Full Response:")
print(json.dumps(res_dict, indent=2, ensure_ascii=False))
