# SCOPE.md - Anomaly Log and Database Schema

## Anomalies Detected and Handled

### 1. **Settlement/Payment Entries (Row 25)**
- **Issue**: "Rohan paid Aisha back" is a settlement, not an expense
- **Detection**: Single recipient in split_with + keywords like "settlement", "paid back"
- **Action**: Skip from expense tracking; log for informational purposes
- **Severity**: INFO

### 2. **Invalid/Missing Dates**
- **Issue**: Date format inconsistencies ("Mar-14" vs "DD-MM-YYYY")
- **Detection**: Try multiple date formats before failing
- **Action**: Skip row if no format matches
- **Severity**: ERROR

Example: Row 14 "Mar-14" handled with format "%b-%d"

### 3. **Missing Descriptions**
- **Issue**: Empty description field
- **Detection**: Check if description is empty after trimming
- **Action**: Skip row
- **Severity**: ERROR

### 4. **Invalid Amount Format**
- **Issue**: Amount with commas ("1,200") or invalid characters
- **Detection**: Try parsing after removing commas
- **Action**: Skip row if still unparseable
- **Severity**: ERROR

Example: Row 10 "1,200" → parsed as 1200.0

### 5. **Negative Amounts (Refunds)**
- **Issue**: Negative amounts indicate refunds/adjustments
- **Detection**: Check if amount < 0
- **Action**: Treat as refund; log warning; use absolute value
- **Severity**: WARNING

Example: Row 12 "-30" USD for parasailing refund

### 6. **Missing or Invalid Currency**
- **Issue**: Currency field empty or unknown value
- **Detection**: Check if currency is missing or not in [INR, USD, EUR]
- **Action**: Default to INR; log warning
- **Severity**: WARNING

Example: Row 15 missing currency → defaults to INR

### 7. **Missing Payer Name**
- **Issue**: "paid_by" field is empty
- **Detection**: Check if paid_by is empty after trimming
- **Action**: Skip row
- **Severity**: ERROR

### 8. **Invalid Split Type**
- **Issue**: Unknown split type or missing
- **Detection**: Check if split_type in ["equal", "unequal", "percentage", "share"]
- **Action**: Default to "equal"; log warning
- **Severity**: WARNING

### 9. **Missing Participants**
- **Issue**: split_with is empty or no valid participants
- **Detection**: Check if split_with produces empty list
- **Action**: Skip row
- **Severity**: ERROR

### 10. **Payer Not in Split**
- **Issue**: Payer doesn't appear in split_with list
- **Detection**: Check if paid_by in split_with
- **Action**: Add payer to split list; log warning
- **Severity**: WARNING

Example: Row 20 payer "Rohan" added to split list

### 11. **Duplicate Expenses**
- **Issue**: Same expense logged twice with different amounts
- **Detection**: Track (date, description, payer, amount) tuples
- **Action**: Keep first, flag second for review
- **Severity**: WARNING

Example: Row 8 & 9 both "dinner - marina bites" on 08-02-2026

### 12. **Member Joined/Left Dates**
- **Issue**: Expense assigned to person after they moved out
- **Detection**: Check expense date vs member join/leave dates
- **Action**: Flag for approval; optionally exclude
- **Severity**: WARNING

Example: Meera appears in April rent but left at end of March

## Database Schema

### `users`
```
id: VARCHAR(36) PRIMARY KEY
username: VARCHAR(50) UNIQUE NOT NULL
email: VARCHAR(100) UNIQUE NOT NULL
hashed_password: VARCHAR(255) NOT NULL
full_name: VARCHAR(100)
created_at: TIMESTAMP DEFAULT NOW()
```

### `groups`
```
id: VARCHAR(36) PRIMARY KEY
name: VARCHAR(100) NOT NULL
description: TEXT
created_by: VARCHAR(36) FK → users.id
created_at: TIMESTAMP DEFAULT NOW()
is_active: BOOLEAN DEFAULT TRUE
```

### `group_members`
```
id: VARCHAR(36) PRIMARY KEY
group_id: VARCHAR(36) FK → groups.id NOT NULL
user_id: VARCHAR(36) FK → users.id NOT NULL
joined_at: TIMESTAMP DEFAULT NOW()
left_at: TIMESTAMP NULL
is_active: BOOLEAN DEFAULT TRUE
```

### `expenses`
```
id: VARCHAR(36) PRIMARY KEY
group_id: VARCHAR(36) FK → groups.id NOT NULL
description: VARCHAR(255) NOT NULL
amount: FLOAT NOT NULL
currency: VARCHAR(3) DEFAULT 'INR'
paid_by_user_id: VARCHAR(36) FK → users.id NOT NULL
split_type: VARCHAR(20) NOT NULL
expense_date: TIMESTAMP NOT NULL
created_at: TIMESTAMP DEFAULT NOW()
notes: TEXT
is_deleted: BOOLEAN DEFAULT FALSE
is_settlement: BOOLEAN DEFAULT FALSE
csv_row_number: INTEGER
```

### `expense_splits`
```
id: VARCHAR(36) PRIMARY KEY
expense_id: VARCHAR(36) FK → expenses.id NOT NULL
user_id: VARCHAR(36) FK → users.id NOT NULL
amount: FLOAT (for unequal splits)
percentage: FLOAT (for percentage splits)
shares: INTEGER (for share-based splits)
```

### `import_reports`
```
id: VARCHAR(36) PRIMARY KEY
group_id: VARCHAR(36) FK → groups.id NOT NULL
import_date: TIMESTAMP DEFAULT NOW()
total_rows: INTEGER NOT NULL
successful_imports: INTEGER NOT NULL
anomalies_detected: JSON NOT NULL
created_by: VARCHAR(36) FK → users.id NOT NULL
```

## Key Decisions in Schema

1. **Soft Deletes**: Expenses have `is_deleted` flag instead of hard deletes (audit trail)
2. **CSV Row Tracking**: `csv_row_number` stored for traceability
3. **Member Timeline**: `group_members` tracks join/leave with timestamps
4. **Flexible Splits**: Single table with amount/percentage/shares fields
5. **Import History**: Full anomaly JSON preserved in reports

---

For detailed decision rationale, see `DECISIONS.md`
