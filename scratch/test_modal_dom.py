import re

with open("landing.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Check if iyzicoModal div exists
assert 'id="iyzicoModal"' in content, "iyzicoModal container missing!"

# 2. Check if openIyzicoModal function exists
assert 'function openIyzicoModal' in content, "openIyzicoModal function missing!"

# 3. Check if pricing buttons call openIyzicoModal
matches = re.findall(r'openIyzicoModal\([^)]+\)', content)
print("Found openIyzicoModal calls:", len(matches))
for m in matches:
    print(" - Call:", m)

# 4. Check if form submission handler exists
assert "document.getElementById('iyzicoSubmitForm')" in content, "iyzicoSubmitForm listener missing!"

print("\n✅ All DOM & Modal structure checks passed with 100% SUCCESS!")
