import re
import os

html_files = [
    'landing.html',
    'index.html',
    'public.html',
    'agency_dashboard.html',
    'admin.html'
]

# Match text between tags that contains Turkish characters or non-ascii, or hardcoded text
turkish_chars = re.compile(r'[çğıöşüÇĞİÖŞÜ]')

untranslated = []

for file_name in html_files:
    if not os.path.exists(file_name):
        continue
    with open(file_name, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for idx, line in enumerate(lines, 1):
        # ignore script / style
        if '<script' in line or '<style' in line or '<!--' in line or 'svg' in line:
            continue
        
        # find text nodes between > and <
        matches = re.findall(r'>([^<]+)<', line)
        for text in matches:
            clean_text = text.strip()
            if not clean_text or clean_text.startswith('{') or clean_text.isdigit() or len(clean_text) < 2:
                continue
            
            # Check if line contains data-i18n or data-i18n-html
            if 'data-i18n' not in line:
                if turkish_chars.search(clean_text) or any(w in clean_text for w in ['Ajans', 'Sanatçı', 'Giriş', 'Detay', 'Yükle', 'Yönetici', 'Menajer']):
                    untranslated.append((file_name, idx, clean_text, line.strip()))

print(f"Found {len(untranslated)} potentially missing data-i18n tags across HTML files:")
for item in untranslated:
    print(f"[{item[0]}:L{item[1]}] {item[2]} --> {item[3]}")
