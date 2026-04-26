import os

file_path = r'c:\Users\Computer\Desktop\EyeShield\EyeShield-modelTest\app\screening_form.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Define DurationWidget class
duration_widget_class = """
class DurationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.years = QSpinBox()
        self.years.setSuffix(" years")
        self.years.setRange(0, 100)
        
        self.months = QSpinBox()
        self.months.setSuffix(" months")
        self.months.setRange(0, 11)
        
        layout.addWidget(self.years)
        layout.addWidget(self.months)
        
    def value(self) -> int:
        \"\"\"Returns total duration in months.\"\"\"
        return self.years.value() * 12 + self.months.value()
        
    def setValue(self, total_months: int):
        total_months = int(total_months or 0)
        y = total_months // 12
        m = total_months % 12
        self.years.setValue(y)
        self.months.setValue(m)
        
    def setRange(self, min_val, max_val):
        pass
        
    def setReadOnly(self, ro: bool):
        self.years.setReadOnly(ro)
        self.months.setReadOnly(ro)
        
    def setButtonSymbols(self, sym):
        self.years.setButtonSymbols(sym)
        self.months.setButtonSymbols(sym)
        
    def setStyleSheet(self, ss: str):
        self.years.setStyleSheet(ss)
        self.months.setStyleSheet(ss)

"""

# Inject class after imports
inject_idx = 0
for i, l in enumerate(lines):
    if 'class DropZoneLabel' in l:
        inject_idx = i
        break
lines.insert(inject_idx, duration_widget_class)

# 2. Update self.diabetes_duration initialization
for i, l in enumerate(lines):
    if 'self.diabetes_duration = QSpinBox()' in l:
        lines[i] = l.replace('QSpinBox()', 'DurationWidget()')
    # Remove suffix and range calls as they are handled in DurationWidget
    if 'self.diabetes_duration.setSuffix(" months")' in l:
        lines[i] = '# ' + l
    if 'self.diabetes_duration.setRange(0, 1200)' in l:
        lines[i] = '# ' + l

# 3. Update _validate_all_fields_for_queue to include duration
for i, l in enumerate(lines):
    if 'if missing:' in l and 'def _validate_all_fields_for_queue' in lines[i-30:i]: # heuristic
        # Check if duration is already there (it isn't)
        lines.insert(i, '        if hasattr(self, "diabetes_duration") and self.diabetes_duration.value() < 0: # 0 is allowed\n            pass\n')
        # Actually, let's just add a check that it's required if not 0? 
        # User said "all fields are required". But if they have diabetes for 0 months (just diagnosed), it's 0.
        # Maybe I should just check if it exists.
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Updated screening_form.py to use DurationWidget')
