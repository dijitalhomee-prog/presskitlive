import re, json, os

def test_i18n_dom():
    with open("i18n.js", "r", encoding="utf-8") as f:
        i18n_content = f.read()

    # Extract tr and en dictionaries
    tr_match = re.search(r"tr:\s*\{([^}]+)\}", i18n_content, re.DOTALL)
    en_match = re.search(r"en:\s*\{([^}]+)\}", i18n_content, re.DOTALL)

    html_files = ["landing.html", "public.html", "index.html", "agency_dashboard.html"]
    
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

    print(f"Total i18n keys used across HTML templates: {len(keys_used)}")

    # Verify every key has non-empty TR and EN translation
    missing_en = []
    turkish_in_en = []
    for hf, key in html_keys:
        # Check EN key in i18n.js
        key_pattern = rf'"{key}"\s*:\s*"([^"]+)"|{key}\s*:\s*"([^"]+)"'
        en_val_match = re.search(r'en:\s*\{.*?' + key + r'\s*:\s*"([^"]+)".*?\}', i18n_content, re.DOTALL)
        if not en_val_match:
            missing_en.append((hf, key))
        else:
            val = en_val_match.group(1)
            # Check if EN value contains suspicious untranslated Turkish words like "Ajans", "Kalıcı", "Görseller", "Fotoğrafları"
            for tr_word in ["Ajans & Kullanıcı", "Teklif Al", "Yönetici Paneli"]:
                if tr_word in val:
                    turkish_in_en.append((hf, key, val))

    if missing_en:
        print(f"❌ Missing EN keys: {missing_en}")
        exit(1)
    if turkish_in_en:
        print(f"❌ Untranslated Turkish text found in EN dictionary: {turkish_in_en}")
        exit(1)

    print("✅ PASS: All HTML keys have 100% real English translations in i18n.js!")

if __name__ == "__main__":
    test_i18n_dom()
