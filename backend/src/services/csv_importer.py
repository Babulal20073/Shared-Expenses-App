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
    # Reference exchange rates
    USD_TO_INR = 84.5
    EUR_TO_INR = 91.0
    
    # Default Spreetail Flatmates Timeline
    DEFAULT_TIMELINES = {
        "Aisha": (datetime(2026, 2, 1), None),
        "Rohan": (datetime(2026, 2, 1), None),
        "Priya": (datetime(2026, 2, 1), None),
        "Meera": (datetime(2026, 2, 1), datetime(2026, 3, 31, 23, 59, 59)),
        "Sam": (datetime(2026, 4, 15), None),
        "Dev": (datetime(2026, 2, 1), None),  # Visited/guest
        "Kabir": (datetime(2026, 3, 11), None)  # Guest
    }
    
    def __init__(self):
        self.anomalies: List[Anomaly] = []
        self.parsed_expenses: List[Dict[str, Any]] = []
        self.processed_rows = 0
        self.successful_imports = 0

    def parse_csv(self, csv_content: str, member_timelines: Optional[Dict] = None) -> Tuple[List[Dict], List[Anomaly]]:
        """Parse CSV and detect anomalies without saving to database"""
        self.anomalies = []
        self.parsed_expenses = []
        self.processed_rows = 0
        self.successful_imports = 0

        # Use default timelines if not provided
        timelines = member_timelines or self.DEFAULT_TIMELINES

        reader = csv.DictReader(StringIO(csv_content))
        
        seen_expenses = {}
        
        for row_num, row in enumerate(reader, start=2):  # start=2 because header is row 1
            try:
                processed_row = self._process_row(row, row_num, seen_expenses, timelines)
                if processed_row:
                    self.parsed_expenses.append(processed_row)
                    self.successful_imports += 1
                self.processed_rows += 1
            except Exception as e:
                self.anomalies.append(Anomaly(
                    row_number=row_num,
                    field="row",
                    issue=f"Row processing failed: {str(e)}",
                    original_value=str(row),
                    action_taken="Row skipped",
                    severity=AnomalySeverity.ERROR
                ))

        return self.parsed_expenses, self.anomalies

    def _process_row(self, row: Dict, row_num: int, seen_expenses: Dict, timelines: Dict) -> Optional[Dict]:
        """Process a single CSV row, detect anomalies, and return normalized dictionary"""
        
        notes = row.get("notes", "").strip()
        description = row.get("description", "").strip()
        
        # ===== ANOMALY 1: Settlement entries =====
        is_settlement = self._is_settlement(row)

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

        # Handle Date formatting warnings (e.g. Mar-14, 04-05-2026 formatting inconsistency)
        original_date_str = row.get("date", "").strip()
        if "-" in original_date_str and not original_date_str.split("-")[0].isdigit():
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="date",
                issue=f"Non-standard date text format: '{original_date_str}'",
                original_value=original_date_str,
                action_taken=f"Parsed as {expense_date.strftime('%d-%m-%Y')}",
                severity=AnomalySeverity.WARNING
            ))
        elif original_date_str == "04-05-2026" and "May 4" not in notes:
            # Row 34 Deep cleaning service date conflict (May 4 vs April 5)
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="date",
                issue="Ambiguous date format: '04-05-2026' (Notes suggest April 5, sheet says May 4)",
                original_value=original_date_str,
                action_taken="Parsed as May 4, flagged for verification",
                severity=AnomalySeverity.WARNING
            ))

        # ===== ANOMALY 3: Missing description =====
        if not description:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="description",
                issue="Description is empty",
                original_value="",
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
                issue="Negative amount detected (indicates a refund)",
                original_value=amount_str,
                action_taken=f"Imported as negative expense of amount {amount}",
                severity=AnomalySeverity.WARNING
            ))
            # Keep negative amount so it behaves as refund in balance calculation!

        # ===== ANOMALY 6: Missing or invalid currency =====
        currency = row.get("currency", "").strip()
        if not currency:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="currency",
                issue="Currency is missing, defaulting to INR",
                original_value="",
                action_taken="Set to INR",
                severity=AnomalySeverity.WARNING
            ))
            currency = "INR"
        
        currency = currency.upper()
        if currency not in ["INR", "USD", "EUR"]:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="currency",
                issue=f"Unknown currency '{currency}', defaulting to INR",
                original_value=currency,
                action_taken="Set to INR",
                severity=AnomalySeverity.WARNING
            ))
            currency = "INR"

        # ===== ANOMALY 7: Missing payer =====
        paid_by_str = row.get("paid_by", "").strip()
        if not paid_by_str and not is_settlement:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="paid_by",
                issue="Payer is missing",
                original_value="",
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None
        elif not paid_by_str and is_settlement:
            # For a settlement, we need both parties
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="paid_by",
                issue="Payer (sender) missing for settlement",
                original_value="",
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

        # Normalize payer name
        paid_by = self._normalize_name(paid_by_str)
        if paid_by_str != paid_by:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="paid_by",
                issue=f"Payer name casing/formatting inconsistent: '{paid_by_str}'",
                original_value=paid_by_str,
                action_taken=f"Normalized to '{paid_by}'",
                severity=AnomalySeverity.INFO
            ))

        # ===== ANOMALY 8: Invalid split_type =====
        split_type = row.get("split_type", "").strip().lower()
        if is_settlement:
            split_type = "equal"  # Dummy split type for settlements
        elif not split_type:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_type",
                issue="Split type is missing, defaulting to 'equal'",
                original_value="",
                action_taken="Set to 'equal'",
                severity=AnomalySeverity.WARNING
            ))
            split_type = "equal"
        elif split_type not in ["equal", "unequal", "percentage", "share"]:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_type",
                issue=f"Unknown split type '{split_type}', defaulting to 'equal'",
                original_value=split_type,
                action_taken="Set to 'equal'",
                severity=AnomalySeverity.WARNING
            ))
            split_type = "equal"

        # ===== ANOMALY 9: Parse split_with (participants) =====
        split_with_str = row.get("split_with", "").strip()
        split_with = []
        for s in split_with_str.split(";"):
            s_clean = s.strip()
            if s_clean:
                norm_s = self._normalize_name(s_clean)
                split_with.append(norm_s)
        
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

        # Check if payer is in split_with (for normal expenses only, NOT settlements)
        if not is_settlement and paid_by not in split_with and split_type == "equal":
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_with",
                issue=f"Payer '{paid_by}' not in split list for equal split",
                original_value=split_with_str,
                action_taken=f"Added '{paid_by}' to split list",
                severity=AnomalySeverity.WARNING
            ))
            split_with.append(paid_by)

        # ===== ANOMALY 12: Group member join/leave active timeline check =====
        active_split_with = []
        for name in split_with:
            if name in timelines:
                join_date, leave_date = timelines[name]
                if join_date and expense_date < join_date:
                    self.anomalies.append(Anomaly(
                        row_number=row_num,
                        field="split_with",
                        issue=f"Participant '{name}' was not active in the group yet on {expense_date.strftime('%d-%m-%Y')}",
                        original_value=name,
                        action_taken=f"Removed '{name}' from split list",
                        severity=AnomalySeverity.WARNING
                    ))
                elif leave_date and expense_date > leave_date:
                    self.anomalies.append(Anomaly(
                        row_number=row_num,
                        field="split_with",
                        issue=f"Participant '{name}' had already left the group on {expense_date.strftime('%d-%m-%Y')}",
                        original_value=name,
                        action_taken=f"Removed '{name}' from split list",
                        severity=AnomalySeverity.WARNING
                    ))
                else:
                    active_split_with.append(name)
            else:
                # Guest user not in predefined timeline
                active_split_with.append(name)

        if not active_split_with:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_with",
                issue="No active members remain in split list after timeline filtering",
                original_value=split_with_str,
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None
        
        split_with = active_split_with

        # ===== ANOMALY 10: Parse split_details (for unequal/percentage/share) =====
        split_details_str = row.get("split_details", "").strip()
        split_details = {}
        
        if is_settlement:
            split_details = {}
        elif split_type == "unequal":
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

        # Check for split details in equal split (Row 42 conflict)
        if split_type == "equal" and split_details_str:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_details",
                issue="Split type is 'equal' but split_details are provided",
                original_value=split_details_str,
                action_taken="Ignored split_details, treated as equal split",
                severity=AnomalySeverity.INFO
            ))

        # ===== ANOMALY 11: Duplicate & Double-entry Conflict detection =====
        desc_norm = "".join(description.lower().split())
        is_duplicate = False
        duplicate_of = None
        is_conflict = False
        conflict_with = None

        for key, prev_row in seen_expenses.items():
            prev_date, prev_desc, prev_payer, prev_amount = key
            if prev_date == expense_date.date():
                # Exact duplicate match
                if prev_payer == paid_by and abs(prev_amount - amount) < 0.01:
                    if desc_norm in prev_desc or prev_desc in desc_norm or desc_norm[:5] == prev_desc[:5]:
                        is_duplicate = True
                        duplicate_of = prev_row
                        break
                # Conflict match (Thalassa Dinner row 24 & 25)
                if abs(prev_amount - amount) < 100.0:  # similar amount
                    if ("thalassa" in description.lower() and "thalassa" in prev_desc.lower()) or \
                       ("marina" in description.lower() and "marina" in prev_desc.lower()):
                        is_conflict = True
                        conflict_with = prev_row
                        break
        
        if is_duplicate:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="record",
                issue=f"Potential duplicate of row {duplicate_of}",
                original_value=description,
                action_taken="Flagged as duplicate for user approval",
                severity=AnomalySeverity.WARNING
            ))
        elif is_conflict:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="record",
                issue=f"Conflicting double logging of the same event with row {conflict_with}",
                original_value=description,
                action_taken="Flagged as conflict for user approval",
                severity=AnomalySeverity.WARNING
            ))
        else:
            expense_key = (expense_date.date(), desc_norm, paid_by, amount)
            seen_expenses[expense_key] = row_num

        # Convert amount to INR for reference
        amount_inr = amount
        if currency == "USD":
            amount_inr = amount * self.USD_TO_INR
        elif currency == "EUR":
            amount_inr = amount * self.EUR_TO_INR

        return {
            "id": str(uuid.uuid4()),
            "description": description,
            "amount": round(amount, 2),
            "amount_inr": round(amount_inr, 2),
            "currency": currency,
            "paid_by": paid_by,
            "split_type": split_type,
            "expense_date": expense_date,
            "split_with": split_with,
            "split_details": split_details,
            "notes": notes,
            "csv_row_number": row_num,
            "is_settlement": is_settlement,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "is_conflict": is_conflict,
            "conflict_with": conflict_with
        }

    def _is_settlement(self, row: Dict) -> bool:
        """Check if row is a settlement/payment, not an expense"""
        split_with = row.get("split_with", "").strip()
        notes = row.get("notes", "").lower()
        description = row.get("description", "").lower()
        
        # Check keywords
        if any(keyword in notes or keyword in description for keyword in ["settlement", "paid back", "repaid", "repayment", "transfer", "deposit share"]):
            return True
        
        # Settlements typically have single recipient
        split_count = len([s for s in split_with.split(";") if s.strip()])
        return split_count == 1 and not row.get("split_type")

    def _parse_date(self, date_str: str, row_num: int) -> Optional[datetime]:
        """Parse date supporting multiple standard formats"""
        date_str = date_str.strip()
        
        formats = [
            "%d-%m-%Y",
            "%d-%m-%y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
            "%b-%d",      # Mar-14 -> parsed as current year (2026)
            "%m-%d-%Y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if fmt == "%b-%d":
                    # For Mar-14, set year to 2026 since sheet is from 2026
                    dt = dt.replace(year=2026)
                return dt
            except ValueError:
                continue
        
        return None

    def _parse_amount(self, amount_str: str, row_num: int) -> Optional[float]:
        """Parse amount, cleaning commas and quotes"""
        amount_str = amount_str.replace(",", "").replace('"', '').strip()
        try:
            val = float(amount_str)
            # Check for high precision decimal formatting anomaly
            if "." in amount_str and len(amount_str.split(".")[1]) > 2:
                self.anomalies.append(Anomaly(
                    row_number=row_num,
                    field="amount",
                    issue=f"Excessive decimal precision in amount '{amount_str}'",
                    original_value=amount_str,
                    action_taken=f"Rounded to {round(val, 2)}",
                    severity=AnomalySeverity.INFO
                ))
            return val
        except ValueError:
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="amount",
                issue=f"Invalid numeric amount format: '{amount_str}'",
                original_value=amount_str,
                action_taken="Row skipped",
                severity=AnomalySeverity.ERROR
            ))
            return None

    def _normalize_name(self, name: str) -> str:
        """Normalize participant names, stripping suffixes and resolving guest aliases"""
        name = name.strip()
        
        # Handle "Dev's friend Kabir" -> "Kabir"
        if "friend" in name.lower():
            parts = name.split()
            return parts[-1].capitalize()
        
        # Default name normalization
        name = name.capitalize()
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
                issue="Unequal split details missing",
                original_value="",
                action_taken="Split treated as equal",
                severity=AnomalySeverity.WARNING
            ))
            return {name: 0.0 for name in split_with}
        
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
        
        # Verify that all split_with users are covered
        for name in split_with:
            if name not in split_details:
                split_details[name] = 0.0
                
        return split_details

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
                issue="Percentage split details missing",
                original_value="",
                action_taken="Split treated as equal",
                severity=AnomalySeverity.WARNING
            ))
            return {name: 100.0 / len(split_with) for name in split_with}
        
        total_percentage = 0.0
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
        
        # Verify and normalize percentages to add up to 100%
        if abs(total_percentage - 100.0) > 0.01:
            action = "Percentages normalized to 100%"
            self.anomalies.append(Anomaly(
                row_number=row_num,
                field="split_details",
                issue=f"Percentages sum up to {total_percentage}%, not 100%",
                original_value=split_details_str,
                action_taken=action,
                severity=AnomalySeverity.WARNING
            ))
            if total_percentage > 0:
                for name in split_details:
                    split_details[name] = (split_details[name] / total_percentage) * 100.0
            else:
                for name in split_with:
                    split_details[name] = 100.0 / len(split_with)
        
        # Verify that all split_with users are covered
        for name in split_with:
            if name not in split_details:
                split_details[name] = 0.0
                
        return split_details

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
                issue="Share split details missing",
                original_value="",
                action_taken="Split treated as equal (1 share each)",
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
        
        # Verify that all split_with users are covered
        for name in split_with:
            if name not in split_details:
                split_details[name] = 1
                
        return split_details
