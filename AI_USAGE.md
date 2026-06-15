# AI_USAGE.md - AI Assistance and Course Corrections

## AI Tools Used

1. **GitHub Copilot** - Code generation and completion
2. **Claude AI** - Architecture design and troubleshooting
3. **ChatGPT** - Testing strategy and edge case analysis

---

## Key Prompts

### Prompt 1: CSV Anomaly Detection Design
**Prompt**: "Design a CSV importer for financial data that detects 12 different anomalies without silently guessing. Each anomaly should be logged with row number, field, issue, and action taken."

**Result**: Structured `Anomaly` class with severity levels and comprehensive detection logic for:
- Date format variations
- Currency mismatches
- Duplicate entries
- Settlement vs expense distinction
- Member timeline violations

### Prompt 2: Balance Calculation Algorithm
**Prompt**: "Implement a settlement algorithm that calculates the minimum number of transactions needed to settle all debts, where some people owe multiple others."

**Result**: Greedy matching algorithm that:
- Sorts debtors/creditors by amount
- Matches largest debtor with largest creditor
- Handles partial settlements
- Minimizes total transactions

### Prompt 3: FastAPI + SQLAlchemy Setup
**Prompt**: "Structure a FastAPI application with SQLAlchemy ORM, authentication, and complex relationship queries across multiple tables."

**Result**: Proper separation of concerns with:
- Models layer (SQLAlchemy)
- Schemas layer (Pydantic)
- Services layer (business logic)
- Routes layer (endpoints)
- Middleware (authentication)

---

## AI Mistakes Caught and Fixed

### Mistake 1: Incorrect Import Relationships

**AI Generated**:
```python
# Wrong: Circular import
from routes import auth, groups, expenses  # In models.py
```

**Issue**: Models imported routes, causing circular dependency.

**What I Changed**:
```python
# Correct: Only import models in routes
from models.models import Expense  # In routes
```

**How I Caught It**: Ran the app and got `ImportError: circular import`

**Fix Applied**: Restructured import order - models first, then routes/services that depend on models.

---

### Mistake 2: Incorrect Foreign Key Reference

**AI Generated**:
```python
# Wrong: Incorrect relationship setup
class Expense(Base):
    user_id = Column(String(36), ForeignKey("users.id"))  # Missing paid_by
    user = relationship("User")  # Ambiguous
```

**Issue**: Relationship names conflicted; unclear which user field for what.

**What I Changed**:
```python
# Correct: Explicit naming
class Expense(Base):
    paid_by_user_id = Column(String(36), ForeignKey("users.id"))
    paid_by_user = relationship("User", back_populates="expenses_paid")
```

**How I Caught It**: Code review - realized "user" was ambiguous; could be payer or splitter.

**Fix Applied**: Renamed to `paid_by_user_id` for clarity; updated all references.

---

### Mistake 3: Balance Calculation Logic Error

**AI Generated**:
```python
# Wrong: Payer's own balance calculated incorrectly
if expense.split_type == "equal":
    share = total_amount / len(splits)
    for split in splits:
        balances[split.user_id]["owes"] += share
    # Payer's balance not handled separately
```

**Issue**: Payer's `owes` amount was being added even though they paid. Leads to incorrect net balance.

**What I Changed**:
```python
# Correct: Exclude payer from debts
if expense.split_type == "equal":
    share = total_amount / len(splits)
    for split in splits:
        if split.user_id != payer_id:  # ← Added this check
            balances[split.user_id]["owes"] += share

# Payer gets credit
balances[payer_id]["owed"] += (total_amount - balances[payer_id]["owes"])
```

**How I Caught It**: Manual calculation walkthrough
```
Test Case: Aisha pays ₹1200 for rent (equal split 4 ways)
Each person owes: ₹300
Aisha paid: ₹1200
Aisha's net should be: ₹900 (paid ₹1200, owes ₹300)

With bug: Aisha owed=1200, owes=300, net=900 ✓ (accidentally correct)
But logic was wrong for unequal splits.
```

**Fix Applied**: Added explicit check `if split.user_id != payer_id` to exclude payer from owing themselves.

---

### Mistake 4: CSV Date Parsing Incomplete

**AI Generated**:
```python
# Incomplete: Missing format
formats = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
]
# Missing: Mar-14 format from CSV row 14
```

**Issue**: "Mar-14" in the CSV wasn't being parsed.

**What I Changed**:
```python
formats = [
    "%d-%m-%Y",
    "%d-%m-%y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y-%m-%d",
    "%b-%d",  # ← Added this
    "%m-%d-%Y",
]
```

**How I Caught It**: Ran import on actual CSV, got "Row 14: invalid date" error.

**Fix Applied**: Added `"%b-%d"` format to handle abbreviated month names.

---

### Mistake 5: Settlement Detection Logic Too Simple

**AI Generated**:
```python
# Wrong: Only checks split count
def is_settlement(self, row):
    split_count = len(row.get("split_with", "").split(";"))
    return split_count == 1
```

**Issue**: Legitimate single-recipient expenses (gift to one person) flagged as settlements.

**What I Changed**:
```python
# Correct: Multiple signals + keyword detection
def is_settlement(self, row):
    split_with = row.get("split_with", "").strip()
    notes = row.get("notes", "").lower()
    
    # Check keywords first
    if any(keyword in notes for keyword in ["settlement", "paid back", "repaid", "loan"]):
        return True
    
    # Then check count (secondary signal)
    split_count = len([s for s in split_with.split(";") if s.strip()])
    return split_count == 1
```

**How I Caught It**: Reviewed CSV - row 25 has "this is a settlement not an expense??" in notes. Original logic would miss context.

**Fix Applied**: Added keyword detection in notes field as primary signal.

---

### Mistake 6: Pydantic Model Validation Too Strict

**AI Generated**:
```python
# Wrong: Required fields without defaults
class UserCreate(BaseModel):
    username: str  # No length constraints
    email: EmailStr
    password: str  # No minimum length
```

**Issue**: Could create user with 1-character username or password.

**What I Changed**:
```python
# Correct: Add field constraints
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
```

**How I Caught It**: Security review - realized no input validation.

**Fix Applied**: Added Pydantic `Field` constraints for all user inputs.

---

### Mistake 7: Missing Error Handling in Services

**AI Generated**:
```python
# Wrong: No error handling
def get_group_members(group_id, db):
    return db.query(User).filter(...).all()  # Raises if invalid group_id
```

**Issue**: Endpoint passes through database errors directly to user.

**What I Changed**:
```python
# Correct: Validate first
@router.get("/groups/{group_id}/members")
async def get_members(group_id, current_user, db):
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(404, "Group not found")  # ← Explicit check
    
    members = GroupService.get_group_members(group_id, db)
    return [UserResponse.model_validate(m) for m in members]
```

**How I Caught It**: Thought about edge cases - "what if group doesn't exist?"

**Fix Applied**: Added explicit group existence check before calling service.

---

### Mistake 8: Import Report JSON Serialization Issue

**AI Generated**:
```python
# Wrong: Direct list assignment
import_report = ImportReport(
    anomalies_detected=[a.to_dict() for a in anomalies]  # Can't store list
)
```

**Issue**: PostgreSQL JSON field requires string, not list.

**What I Changed**:
```python
# Correct: Serialize to JSON string
import_report = ImportReport(
    anomalies_detected=json.dumps([a.to_dict() for a in anomalies])
)

# And deserialize on read
anomalies_data = json.loads(report.anomalies_detected)
anomalies = [AnomalyReport(**a) for a in anomalies_data]
```

**How I Caught It**: Tried to save import report, got `TypeError: Object of type list is not JSON serializable`.

**Fix Applied**: Added `json.dumps()` on write, `json.loads()` on read.

---

## Edge Cases Tested

### Test 1: All Users in Different Currencies
```
Input: Aisha pays ₹1000, Dev pays $100 USD in same group
Expected: Balances shown in original currencies, settlement mentions both
Status: ✅ Handled by storing original currency + amount
```

### Test 2: Duplicate Entries with Different Amounts
```
Input: Row 8 & 9 both "dinner - marina bites" but different amounts
Expected: First kept, second flagged as potential duplicate (not strict match)
Status: ✅ Handled by tracking (date, description, payer, amount) tuple
```

### Test 3: Member Leaves Then Appears Again
```
Input: Meera leaves March 28, but April 2 has "Groceries BigBasket" with Meera
Expected: Flag warning, let user approve
Status: ✅ Handled by group_members timeline + warning in import report
```

### Test 4: Circular Settlements
```
Input: Aisha owes Rohan ₹100, Rohan owes Priya ₹100, Priya owes Aisha ₹100
Expected: Settlement plan shows who pays whom
Status: ✅ Greedy algorithm handles chains correctly
```

### Test 5: Percentage Splits Not Adding to 100%
```
Input: "Aisha 30%; Rohan 30%; Priya 30%; Meera 20%" (adds to 100% but example says might be off)
Expected: Log warning about percentages, normalize on display
Status: ✅ Detected with message "Percentages add up to X%, not 100%"
```

---

## Summary

| Mistake Type | Count | Severity | Root Cause |
|---|---|---|---|
| Logic errors | 3 | High | Incomplete handling of edge cases |
| Import issues | 2 | High | Missing patterns or data format variants |
| Type errors | 2 | Medium | Incorrect field types for storage |
| Validation gaps | 1 | Medium | Missing input constraints |

**Key Lesson**: Even well-generated code needs manual review for:
1. Financial calculations (no rounding errors)
2. Edge cases in data validation
3. Error handling and user feedback
4. Data serialization for storage

---

**Conclusion**: Copilot/Claude were excellent for scaffolding and pattern generation, but domain-specific logic (financial calculations, anomaly detection) required manual verification and refinement.
