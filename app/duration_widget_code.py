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
        """Returns total duration in months."""
        return self.years.value() * 12 + self.months.value()
        
    def setValue(self, total_months: int):
        total_months = int(total_months or 0)
        y = total_months // 12
        m = total_months % 12
        self.years.setValue(y)
        self.months.setValue(m)
        
    def setRange(self, min_val, max_val):
        # We handle ranges internally, but keep this for compatibility
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
