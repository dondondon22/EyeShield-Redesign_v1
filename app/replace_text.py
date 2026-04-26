import os
import glob

replacements = [
    ('"scr_clinical_history": "Diabetic History"', '"scr_clinical_history": "Diabetic History"'),
    ('diabetic history, and eye side', 'diabetic history, and eye side'),
    ('<!-- Diabetic History & Diabetes Management -->', '<!-- Diabetic History & Diabetes Management -->'),
    ('{sec("Diabetic History & Diabetes Management")}', '{sec("Diabetic History & Diabetes Management")}'),
    ('section_title(c2, "DIABETIC HISTORY",', 'section_title(c2, "DIABETIC HISTORY",'),
    ('"Missing Diabetic History",', '"Missing Diabetic History",'),
    ('QGroupBox("Diabetic History")', 'QGroupBox("Diabetic History")'),
    ('self._section_header("📋  DIABETIC HISTORY")', 'self._section_header("📋  DIABETIC HISTORY")'),
    ('add_section("Diabetic History")', 'add_section("Diabetic History")'),
    ('self._card("Diabetic History")', 'self._card("Diabetic History")'),
    ('self._add_card_header(v, "Diabetic History",', 'self._add_card_header(v, "Diabetic History",'),
    ('form.addRow(QLabel("Diabetic History"))', 'form.addRow(QLabel("Diabetic History"))'),
]

files = glob.glob(r'c:\Users\Computer\Desktop\EyeShield\EyeShield-modelTest\app\*.py')
changed_files = []

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for old, new in replacements:
        content = content.replace(old, new)
        
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        changed_files.append(os.path.basename(filepath))

print('Changed files:', changed_files)
