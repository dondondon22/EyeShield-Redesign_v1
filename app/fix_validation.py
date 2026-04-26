import os

file_path = r'c:\Users\Computer\Desktop\EyeShield\EyeShield-modelTest\app\screening_form.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_validate_method = '''
    def _validate_all_fields_for_queue(self) -> bool:
        missing = []
        
        full_name = self.p_name.text().strip()
        if len([p for p in full_name.split() if p.strip()]) < 2:
            missing.append("First and Last Name")
            
        if not self._get_dob_date().isValid():
            missing.append("Date of Birth")
            
        if not self.p_sex.currentText().strip():
            missing.append("Sex")
            
        phone = self.p_phone.text().strip() if hasattr(self, "p_phone") else ""
        contact = self.p_contact.text().strip()
        if not (phone or contact):
            missing.append("Phone/Contact Number")
            
        if hasattr(self, "p_address") and not self.p_address.text().strip():
            missing.append("Address")
            
        if hasattr(self, "diabetes_type") and self.diabetes_type.currentText().strip() in ("", "Select"):
            missing.append("Diabetes Type")
            
        # Clinical variables
        if hasattr(self, "diabetes_diagnosis_date") and self.diabetes_diagnosis_date.isEnabled():
            if not self.diabetes_diagnosis_date.text().strip() and self.diabetes_type.currentText().strip() not in ("", "Select", "None", "No Diabetes"):
                missing.append("Diabetes Diagnosis Date")
                
        if hasattr(self, "va_left") and not self.va_left.text().strip():
            missing.append("Visual Acuity (Left Eye)")
        if hasattr(self, "va_right") and not self.va_right.text().strip():
            missing.append("Visual Acuity (Right Eye)")
            
        if hasattr(self, "bp_systolic") and self.bp_systolic.value() <= 0:
            missing.append("Blood Pressure (Systolic)")
        if hasattr(self, "bp_diastolic") and self.bp_diastolic.value() <= 0:
            missing.append("Blood Pressure (Diastolic)")
        if hasattr(self, "fbs") and self.fbs.value() <= 0:
            missing.append("Fasting Blood Sugar (FBS)")
        if hasattr(self, "rbs") and self.rbs.value() <= 0:
            missing.append("Random Blood Sugar (RBS)")
            
        if hasattr(self, "height") and self.height.value() <= 0:
            missing.append("Height (cm)")
        if hasattr(self, "weight") and self.weight.value() <= 0:
            missing.append("Weight (kg)")
            
        if hasattr(self, "treatment_regimen") and self.treatment_regimen.currentText().strip() in ("", "Select"):
            missing.append("Treatment Regimen")
            
        if hasattr(self, "prev_dr_stage") and self.prev_dr_stage.currentText().strip() in ("", "Select"):
            missing.append("Previous DR Stage")
            
        if missing:
            QMessageBox.warning(
                self,
                "Missing Required Fields",
                "Please fill in all required fields before saving.\\n\\nMissing:\\n- " + "\\n- ".join(missing)
            )
            return False
            
        return True
'''

start_idx = -1
for i, l in enumerate(lines):
    if 'def _save_and_queue_patient(self) -> None:' in l:
        start_idx = i
        break

if start_idx != -1:
    lines.insert(start_idx, new_validate_method)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully added _validate_all_fields_for_queue")
else:
    print("Could not find _save_and_queue_patient")
