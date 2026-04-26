import os

file_path = r'c:\Users\Computer\Desktop\EyeShield\EyeShield-modelTest\app\screening_form.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Replace DurationWidget class with DurationSpinBox
new_class = """
class DurationSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 1200)
        
    def textFromValue(self, value: int) -> str:
        y = value // 12
        m = value % 12
        return f"{y} years {m} months"
        
    def valueFromText(self, text: str) -> int:
        try:
            # Basic parsing support for manual typing if needed
            import re
            parts = re.findall(r'(\d+)', text)
            if len(parts) >= 2:
                return int(parts[0]) * 12 + int(parts[1])
            elif len(parts) == 1:
                return int(parts[0]) * 12
        except Exception:
            pass
        return super().valueFromText(text)

"""

start_idx = -1
end_idx = -1
for i, l in enumerate(lines):
    if 'class DurationWidget' in l:
        start_idx = i
    if start_idx != -1 and 'self.months.setStyleSheet(ss)' in l:
        end_idx = i + 1
        break

if start_idx != -1 and end_idx != -1:
    lines = lines[:start_idx] + [new_class] + lines[end_idx:]

# 2. Update instantiations
for i, l in enumerate(lines):
    if 'DurationWidget()' in l:
        lines[i] = l.replace('DurationWidget()', 'DurationSpinBox()')

# 3. Clean up comments and setRange calls
for i, l in enumerate(lines):
    if 'self.diabetes_duration.setSuffix(' in l and '# ' in l:
        lines[i] = '' # Remove the commented out suffix line
    if 'self.diabetes_duration.setRange(' in l and '# ' in l:
        lines[i] = '' # Remove the commented out range line

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Updated screening_form.py to use DurationSpinBox')
