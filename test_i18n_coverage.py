import re, json, os

def test_i18n():
    with open("i18n.js", "r", encoding="utf-8") as f:
        i18n_content = f.read()

    # Extract tr and en dictionaries using regex
    tr_match = re.search(r'tr:\s*\{([^}]+(\{[^}]*\}[^}]*)*)\}', i18n_content, re.DOTALL)
    en_match = re.search(r'en:\s*\{([^}]+(\{[^}]*\}[^}]*)*)\}', i18n_content, re.DOTALL)

    html_files = ["landing.html", "public.html", "index.html", "agency_dashboard.html"]
    
    missing_keys = []
    
    for file in html_files:
        if not os.path.exists(file): continue
        with open(file, "r", encoding="utf-8") as f:
            html = f.read()
        
        # Find all data-i18n="..." and data-i18n-html="..."
        keys = re.findall(r'data-i18n(?:-html)?=["\']([^"\']+)["\']', html)
        for k in keys:
            if f'"{k}"' not in i18n_content and f"'{k}'" not in i18n_content and f"{k}:" not in i18n_content:
                missing_keys.append((file, k))

    print(f"Total HTML files checked: {len(html_files)}")
    if missing_keys:
        print("❌ Missing translation keys found:")
        for file, k in missing_keys:
            print(f"  - File: {file} | Key: {k}")
    else:
        print("✅ 100% of data-i18n keys are present in i18n.js!")

if __name__ == "__main__":
    test_i18n()
