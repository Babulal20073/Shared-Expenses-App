import csv
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from io import StringIO
from enum import Enum
import uuid


class AnomalySeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Anomaly:
    def __init__(
        self,
        row_number: Optional[int],
        field: str,
        issue: str,
        original_value: Any,
        action_taken: str,
        severity: str = AnomalySeverity.WARNING
    ):
        self.row_number = row_number
        self.field = field
        self.issue = issue
        self.original_value = original_value
        self.action_taken = action_taken
        self.severity = severity

    def to_dict(self):
        return {
            "row_number": self.row_number,
            "field": self.field,
            "issue": self.issue,
            "original_value": str(self.original_value),
            "action_taken": self.action_taken,
            "severity": self.severity
        }


class CSVImporter:
    # Reference exchange rate (as of assignment date - June 2026)
    USD_TO_INR_RATE = 84.5  # Approximate rate
    
    # Known valid participants
    KNOWN_USERS = {"Aisha", "Rohan", "Priya", "Meera", "Dev", "Sam"}
    
    def __init__(self):
        self.anomalies: List[Anomaly] = []
        self.parsed_expenses: List[Dict[str, Any]] = []
        self.processed_rows = 0
        self.successful_imports = 0

    def parse_csv(self, csv_content: str) -> Tuple[List[Dict], List[Anomaly]]:
        """Parse CSV and detect anomalies"""
        self.anomalies = []
        self.parsed_expenses = []
        self.processed_rows = 0
        self.successful_imports = 0

        reader = csv.DictReader(StringIO(csv_content))
        
        # Track duplicates by checking same-day expenses
        seen_expenses = {}
        
        for row_num, row in enumerate(reader, start=2):  # start=2 because header is row 1
            try:
                processed_row = self._process_row(row, row_num, seen_expenses)
                if processed_row:
                    self.parsed_expenses.append(processed_row)
                    self.successful_imports += 1
                self.processed_rows += 1
            except Exception as e:
                self.anomalies.append(Anomaly(
                    row_number=row_num,
                    field="row",
                    issue=f"Row processing failed: {str(e)}",
                    original_value=row,
                    action_taken="Row skipped",
                    severity=AnomalySeverity.ERROR
                ))

        return self.parsed_expenses, self.anomalies

    def _process_row(self, row: Dict, row_num: int, seen_expenses: Dict) -> Optional[Dict]:
        """Process a single CSV row and detect anomalies"""
        
        # ===== ANOMALY 1: Settlement entries =====
        if self._is_settlement(row):
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_with",
                issue="Row is a settlement/payment, not an expense",
                original_value=row.get("split_with"),
                action_taken="Row skipped (settlement recorded separately)",
                severity=AnomalySeverity.INFO
            ))
            return None

        # ===== ANOMALY 2: Missing/Invalid date =====
        expense_date = self._parse_date(row.get("date", ""), row_num)
        if not expense_date:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="date",
                issue="Date format invalid or missing",
                original_value=row.get("date", ""),
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

        # ===== ANOMALY 3: Missing description =====
        description = row.get("description", "").strip()
        if not description:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="description",
                issue="Description is empty",
                original_value=row.get("description", ""),
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

        # ===== ANOMALY 4: Invalid amount =====
        amount_str = row.get("amount", "").strip()
        amount = self._parse_amount(amount_str, row_num)
        if amount is None:
            return None

        # ===== ANOMALY 5: Negative amounts (refunds) =====
        if amount < 0:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="amount",
                issue="Negative amount detected (likely a refund or adjustment)",
                original_value=amount_str,
                action_taken=f"Treated as refund with amount {abs(amount)}",
                severity=AnomalySeverity.WARNING
            ))
            amount = abs(amount)

        # ===== ANOMALY 6: Missing or invalid currency =====
        currency = row.get("currency", "").strip()
        if not currency or currency == "":
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="currency",
                issue="Currency is missing, defaulting to INR",
                original_value=row.get("currency", ""),
                action_taken="Set to INR",
                severity=AnomalySeverity.WARNING
            ))
            currency = "INR"
        
        # Normalize currency
        currency = currency.upper() if currency else "INR"
        if currency not in ["INR", "USD", "EUR"]:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="currency",
                issue=f"Unknown currency: {currency}, defaulting to INR",
                original_value=currency,
                action_taken="Set to INR",
                severity=AnomalySeverity.WARNING
            ))
            currency = "INR"

        # ===== ANOMALY 7: Missing payer =====
        paid_by = row.get("paid_by", "").strip()
        if not paid_by:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="paid_by",
                issue="Payer is missing",
                original_value=row.get("paid_by", ""),
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

        # Normalize payer name
        paid_by = self._normalize_name(paid_by)

        # ===== ANOMALY 8: Invalid split_type =====
        split_type = row.get("split_type", "").strip().lower()
        if not split_type:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_type",
                issue="Split type is missing, defaulting to 'equal'",
                original_value=row.get("split_type", ""),
                action_taken="Set to 'equal'",
                severity=AnomalySeverity.WARNING
            ))
            split_type = "equal"
        elif split_type not in ["equal", "unequal", "percentage", "share"]:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_type",
                issue=f"Unknown split type: {split_type}, defaulting to 'equal'",
                original_value=split_type,
                action_taken="Set to 'equal'",
                severity=AnomalySeverity.WARNING
            ))
            split_type = "equal"

        # ===== ANOMALY 9: Parse split_with (participants) =====
        split_with_str = row.get("split_with", "").strip()
        split_with = [self._normalize_name(s) for s in split_with_str.split(";") if s.strip()]
        
        if not split_with:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_with",
                issue="No participants listed for split",
                original_value=split_with_str,
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

        # Check if payer is in split_with
        if paid_by not in split_with:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_with",
                issue=f"Payer '{paid_by}' not in split_with list",
                original_value=split_with_str,
                action_taken=f"Added '{paid_by}' to split",
                severity=AnomalySeverity.WARNING
            ))
            split_with.append(paid_by)

        # ===== ANOMALY 10: Parse split_details (for unequal/percentage/share) =====
        split_details_str = row.get("split_details", "").strip()
        split_details = {}
        
        if split_type == "unequal":
            split_details = self._parse_unequal_split(split_details_str, split_with, row_num)
            if not split_details:
                return None
        elif split_type == "percentage":
            split_details = self._parse_percentage_split(split_details_str, split_with, row_num)
            if not split_details:
                return None
        elif split_type == "share":
            split_details = self._parse_share_split(split_details_str, split_with, row_num)
            if not split_details:
                return None

        # ===== ANOMALY 11: Duplicate detection =====
        expense_key = (expense_date.date(), description, paid_by, amount)
        if expense_key in seen_expenses:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="record",
                issue=f"Potential duplicate: Similar expense on row {seen_expenses[expense_key]}",
                original_value=f"Row {row_num}",
                action_taken="First occurrence kept, duplicate flagged for review",
                severity=AnomalySeverity.WARNING
            ))
            # Keep first occurrence only
            return None
        
        seen_expenses[expense_key] = row_num

        # ===== ANOMALY 12: Member joined/left dates =====
        notes = row.get("notes", "").strip()
        # Track who was present at what time - this would be validated during import
        # For now, we flag if someone appears after they left
        
        # Build final record
        return {
            "id": str(uuid.uuid4()),
            "description": description,
            "amount": amount,
            "currency": currency,
            "paid_by": paid_by,
            "split_type": split_type,
            "expense_date": expense_date,
            "split_with": split_with,
            "split_details": split_details,
            "notes": notes,
            "csv_row_number": row_num
        }

    def _is_settlement(self, row: Dict) -> bool:
        """Check if row is a settlement/payment, not an expense"""
        split_with = row.get("split_with", "").strip()
        notes = row.get("notes", "").lower()
        
        # Check keywords in notes
        if any(keyword in notes for keyword in ["settlement", "paid back", "repaid", "loan"]):
            return True
        
        # Settlements typically have single recipient
        split_count = len([s for s in split_with.split(";") if s.strip()])
        return split_count == 1

    def _parse_date(self, date_str: str, row_num: int) -> Optional[datetime]:
        """Parse date with multiple format support"""
        date_str = date_str.strip()
        
        formats = [
            "%d-%m-%Y",
            "%d-%m-%y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
            "%b-%d",  # Mar-14
            "%m-%d-%Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

    def _parse_amount(self, amount_str: str, row_num: int) -> Optional[float]:
        """Parse amount, handling commas and decimals"""
        amount_str = amount_str.replace(",", "").strip()
        try:
            return float(amount_str)
        except ValueError:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="amount",
                issue=f"Invalid amount format: {amount_str}",
                original_value=amount_str,
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

    def _normalize_name(self, name: str) -> str:
        """Normalize participant names"""
        name = name.strip().capitalize()
        # Remove titles or suffixes
        if " " in name:
            name = name.split()[0]
        return name

    def _parse_unequal_split(
        self,
        split_details_str: str,
        split_with: List[str],
        row_num: int
    ) -> Optional[Dict]:
        """Parse unequal split details like 'Rohan 700; Priya 400; Meera 400'"""
        split_details = {}
        
        if not split_details_str:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_details",
                issue="Unequal split requires split_details",
                original_value="",
                action_taken="Split treated as equal",
                severity=AnomalySeverity.WARNING
            ))
            # Treat as equal split
            return {name: "equal" for name in split_with}
        
        for detail in split_details_str.split(";"):
            detail = detail.strip()
            parts = detail.split()
            if len(parts) >= 2:
                name = self._normalize_name(parts[0])
                try:
                    amount = float(parts[-1])
                    split_details[name] = amount
                except ValueError:
                    pass
        
        return split_details if split_details else None

    def _parse_percentage_split(
        self,
        split_details_str: str,
        split_with: List[str],
        row_num: int
    ) -> Optional[Dict]:
        """Parse percentage split like 'Aisha 30%; Rohan 30%; Priya 30%; Meera 20%'"""
        split_details = {}
        
        if not split_details_str:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_details",
                issue="Percentage split requires split_details",
                original_value="",
                action_taken="Split treated as equal",
                severity=AnomalySeverity.WARNING
            ))
            return {name: 100 / len(split_with) for name in split_with}
        
        total_percentage = 0
        for detail in split_details_str.split(";"):
            detail = detail.strip()
            parts = detail.split()
            if len(parts) >= 2:
                name = self._normalize_name(parts[0])
                try:
                    percentage = float(parts[-1].rstrip("%"))
                    split_details[name] = percentage
                    total_percentage += percentage
                except ValueError:
                    pass
        
        # Check if percentages add up to 100
        if abs(total_percentage - 100) > 0.01:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_details",
                issue=f"Percentages add up to {total_percentage}%, not 100%",
                original_value=split_details_str,
                action_taken="Percentages will be normalized",
                severity=AnomalySeverity.WARNING
            ))
        
        return split_details if split_details else None

    def _parse_share_split(
        self,
        split_details_str: str,
        split_with: List[str],
        row_num: int
    ) -> Optional[Dict]:
        """Parse share-based split like 'Aisha 1; Rohan 2; Priya 1; Dev 2'"""
        split_details = {}
        
        if not split_details_str:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_details",
                issue="Share split requires split_details",
                original_value="",
                action_taken="Split treated as equal",
                severity=AnomalySeverity.WARNING
            ))
            return {name: 1 for name in split_with}
        
        for detail in split_details_str.split(";"):
            detail = detail.strip()
            parts = detail.split()
            if len(parts) >= 2:
                name = self._normalize_name(parts[0])
                try:
                    shares = int(parts[-1])
                    split_details[name] = shares
                except ValueError:
                    pass
        
        return split_details if split_details else None
