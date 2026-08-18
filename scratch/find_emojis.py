import re

files_to_check = [
    'i18n.js',
    'landing.html',
    'index.html',
    'public.html',
    'agency_dashboard.html',
    'admin.html',
    'app.js'
]

# Regex for matching emoji characters
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002300-\U000023FF"  # misc technical
    "\U00002B50"             # star
    "\U000020E3"
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "]+", flags=re.UNICODE
)

found_emojis = []

for file_path in files_to_check:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for idx, line in enumerate(lines, 1):
        matches = emoji_pattern.findall(line)
        if matches:
            found_emojis.append((file_path, idx, matches, line.strip()))

print(f"Total lines with emojis found: {len(found_emojis)}")
for item in found_emojis:
    print(f"[{item[0]}:L{item[1]}] {item[2]} -> {item[3]}")
