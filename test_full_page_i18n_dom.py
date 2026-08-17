import re, json, os

def test_i18n_dom():
    with open("i18n.js", "r", encoding="utf-8") as f:
        i18n_content = f.read()

    html_files = ["landing.html", "login.html", "public.html", "index.html", "agency_dashboard.html"]
    
    # Parse keys used in HTML files
    keys_used = set()
    html_keys = []
    for hf in html_files:
        with open(hf, "r", encoding="utf-8") as f:
            content = f.read()
        for match in re.finditer(r'data-i18n(-html)?=["\']([^"\']+)["\']', content):
            key = match.group(2)
            keys_used.add(key)
            html_keys.append((hf, key))

    print(f"Total i18n keys used across {len(html_files)} HTML templates: {len(keys_used)}")

    # Verify every key has non-empty TR and EN translation in i18n.js
    missing_tr = []
    missing_en = []
    
    for hf, key in html_keys:
        # Check TR
        tr_val = re.search(r'tr:\s*\{.*?' + key + r'\s*:\s*"([^"]+)".*?\}', i18n_content, re.DOTALL)
        if not tr_val:
            missing_tr.append((hf, key))
        # Check EN
        en_val = re.search(r'en:\s*\{.*?' + key + r'\s*:\s*"([^"]+)".*?\}', i18n_content, re.DOTALL)
        if not en_val:
            missing_en.append((hf, key))

    if missing_tr:
        print(f"❌ Missing TR keys: {missing_tr}")
        exit(1)
    if missing_en:
        print(f"❌ Missing EN keys: {missing_en}")
        exit(1)

    print(f"✅ PASS: All {len(keys_used)} HTML keys have 100% real TR and EN translations in i18n.js!")

if __name__ == "__main__":
    test_i18n_dom()
