import os

file_path = r'c:\Users\Computer\Desktop\EyeShield\EyeShield-modelTest\app\doctor_diagnosis_form.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Update addItems for diabetes_type in edit dialog (missed before)
for i, l in enumerate(lines):
    if 'in_dm_type.addItems(["Select", "Type 1", "Type 2", "Gestational", "Other"])' in l:
        lines[i] = l.replace(
            '["Select", "Type 1", "Type 2", "Gestational", "Other"]',
            '["Select", "Type 1", "Type 2", "Gestational", "Type 1 + Type 2", "Type 1 + Gestational", "Type 2 + Gestational"]'
        )

# 2. Update duration in edit dialog (if I want to be thorough)
# Actually, the user specifically mentioned assessment form.
# But for consistency, let's at least fix the diabetes_type.

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Updated doctor_diagnosis_form.py')
