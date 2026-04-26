import os

file_path = r'c:\Users\Computer\Desktop\EyeShield\EyeShield-modelTest\app\screening_form.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Update addItems for diabetes_type
for i, l in enumerate(lines):
    if 'self.diabetes_type.addItems(["Select", "Type 1", "Type 2", "Gestational", "Other"])' in l:
        lines[i] = l.replace(
            '["Select", "Type 1", "Type 2", "Gestational", "Other"]',
            '["Select", "Type 1", "Type 2", "Gestational", "Type 1 + Type 2", "Type 1 + Gestational", "Type 2 + Gestational"]'
        )

# 2. Update diabetes_duration spinbox
for i, l in enumerate(lines):
    if 'self.diabetes_duration.setSuffix(" years")' in l:
        lines[i] = l.replace('" years"', '" months"')
    elif 'self.diabetes_duration.setRange(0, 80)' in l:
        lines[i] = l.replace('0, 80', '0, 1200')

# 3. Update the duration calculation logic
new_calc = """        today = QDate.currentDate()
        months = (today.year() - diag_date.year()) * 12 + today.month() - diag_date.month()
        if today.day() < diag_date.day():
            months -= 1
        self.diabetes_duration.setValue(max(0, months))
"""

start_calc = -1
for i, l in enumerate(lines):
    if 'def _update_duration_from_diagnosis_date(self):' in l:
        start_calc = i
        break

if start_calc != -1:
    # Find the lines to replace inside _update_duration_from_diagnosis_date
    replace_start = -1
    replace_end = -1
    for i in range(start_calc, start_calc + 20):
        if 'today = QDate.currentDate()' in lines[i]:
            replace_start = i
        if 'self.diabetes_duration.setValue(max(0, years))' in lines[i]:
            replace_end = i
            break
    
    if replace_start != -1 and replace_end != -1:
        lines = lines[:replace_start] + [new_calc] + lines[replace_end+1:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Updated screening_form.py UI fields')
