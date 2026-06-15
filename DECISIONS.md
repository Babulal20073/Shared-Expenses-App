# DECISIONS.md - Engineering and Product Decisions

## 1. Technology Stack: FastAPI + PostgreSQL + React

### Options Considered
- Django + PostgreSQL + React
- Flask + PostgreSQL + React
- FastAPI + PostgreSQL + React ✅ CHOSEN
- Node.js/Express + MongoDB + React

### Decision Rationale
- **FastAPI**: 
  - Built-in data validation with Pydantic (ideal for anomaly detection)
  - Automatic API documentation (Swagger UI)
  - Excellent for CSV processing and financial calculations
  - Simple to explain in live technical session
  - Fast development for 2-day deadline

- **PostgreSQL**: 
  - Required by assignment (relational DB only)
  - ACID compliance for financial data
  - Strong referential integrity for complex relationships

- **React**: 
  - Modern, component-based UI
  - Good state management
  - Deployable on free tiers (Vercel, Netlify)

---

## 2. Settlement/Payment Handling

### Options Considered
- Treat settlements as regular expenses
- Skip settlements entirely
- Create separate settlement table ✅ CHOSEN
- Allow settlements with special flag

### Decision Rationale
- **Current Approach**: Settlements marked with `is_settlement=True` flag
  - Prevents double-counting in balance calculations
  - Preserved in import report for audit trail
  - User can approve/reject before processing
  - Rohan→Aisha payment (Row 25) won't distort calculations

**Example**: "Rohan paid Aisha back ₹5000" detected as settlement and excluded from "who owes whom" calculations.

---

## 3. Currency Handling

### Options Considered
- Convert all to INR at import time
- Store in original currency + conversion rate
- Store in original currency; convert on display ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Store original currency, convert on display
  - Preserves original data integrity
  - Avoids rounding errors from premature conversion
  - Exchange rates can vary by day; audit trail important
  - Display can handle both currencies

**Exchange Rate Used**: 1 USD = ₹84.5 (as of June 2026)
**Why**: Prevents hidden assumptions; auditable

---

## 4. Duplicate Detection Strategy

### Options Considered
- Reject all duplicates
- Keep all duplicates
- Auto-merge with heuristics
- Keep first, flag second ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Keep first occurrence, flag second as warning
  - User reviews flagged duplicates
  - "dinner - marina bites" (Row 8 & 9) both ₹3200 → flag as duplicate
  - Different amounts treated as distinct (not duplicates)
  - No silent data loss

---

## 5. Member Joined/Left Dates

### Options Considered
- Ignore membership timeline entirely
- Auto-exclude post-departure expenses
- Flag for manual review ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Flag warnings; let user decide
  - Meera left end of March but appears in April rent
  - System logs: "Meera appears after leaving group"
  - User can manually correct/approve
  - Respects Meera's concern: "Why would March electricity affect my balance?"

**Implementation**:
```python
# Check expense_date against group_members.left_at
if expense_date > member.left_at:
    flag_warning("Member expense after departure")
```

---

## 6. Negative Amounts (Refunds)

### Options Considered
- Reject negative amounts as errors
- Treat as credit/reversal automatically
- Log as warning, use absolute value ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Log as warning, treat as refund
  - Row 12: "-30 USD" parasailing cancellation
  - System logs: "Negative amount detected (likely refund)"
  - Uses `abs(amount)` for calculations
  - User sees it was a refund in import report

---

## 7. Missing Currency Default

### Options Considered
- Reject rows with missing currency
- Try to infer from context (hard; expensive)
- Default to INR ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Default to INR with warning
  - Row 15: Missing currency → default INR
  - User sees warning in import report: "Currency defaulted to INR"
  - Majority of expenses are INR (more likely)
  - User can correct after import if needed

---

## 8. Balance Calculation Algorithm

### Options Considered
- Simple pairwise debts (complex)
- Greedy settlement algorithm
- Minimum transaction algorithm ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Greedy algorithm for minimal transactions
  - Sort debtors/creditors by amount
  - Match largest debtor with largest creditor
  - Reduces settlement steps (Aisha's requirement: "Who pays whom, done")

**Example**:
```
Aisha owes ₹1500, Rohan owes ₹1000
Priya owed ₹1500, Meera owed ₹1000

Settlement Plan:
1. Aisha → Priya: ₹1500
2. Rohan → Meera: ₹1000
```

---

## 9. Split Type Defaults

### Options Considered
- Reject ambiguous splits
- Default to equal
- Try to infer ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Default to equal when ambiguous
  - Missing split_type → default "equal"
  - Invalid split_type → default "equal", log warning
  - User sees warning in import report

**Example**: Row with no split_type logs warning, assumes equal split.

---

## 10. Import Report Structure

### Options Considered
- Simple CSV with pass/fail
- Verbose log file
- Structured JSON with severity levels ✅ CHOSEN

### Decision Rationale
- **Current Approach**: JSON array with fields
  ```json
  {
    "row_number": 8,
    "field": "record",
    "issue": "Potential duplicate: Similar expense on row 9",
    "original_value": "Row 8",
    "action_taken": "First occurrence kept, duplicate flagged",
    "severity": "warning"
  }
  ```
  - Structured → programmable
  - Severity levels → actionable
  - Row numbers → traceable
  - Original values → auditable

---

## 11. Soft Deletes vs Hard Deletes

### Options Considered
- Hard delete expenses
- Soft delete with flag ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Soft deletes with `is_deleted` flag
  - Preserves audit trail
  - Allows "undo" if needed
  - Respects Meera's requirement: "I want to approve anything the app deletes"

---

## 12. API Authentication

### Options Considered
- No authentication (not production-ready)
- Basic auth
- JWT tokens ✅ CHOSEN

### Decision Rationale
- **Current Approach**: JWT tokens with HTTPBearer
  - Stateless (scalable)
  - Industry standard
  - Supports mobile apps later
  - Tokens expire (configurable)

---

## 13. Row-by-Row vs Atomic Import

### Options Considered
- Atomically import all or nothing
- Import valid rows, skip invalid
- Partial import with rollback option ✅ CHOSEN

### Decision Rationale
- **Current Approach**: Import all valid rows; report anomalies
  - User sees import report with anomalies
  - Valid expenses are imported
  - Anomalies listed for manual review
  - User can decide: accept import or re-run with corrections

---

## Future Enhancements (Out of Scope)

1. **PDF receipts**: Attach original documents
2. **Multi-currency**: Display balances in user's preferred currency
3. **Group messaging**: Discuss expenses in-app
4. **Split editing**: Edit splits after creation
5. **Recurring expenses**: Monthly subscriptions
6. **Export**: Download balance reports as PDF

---

**Summary**: Every decision prioritizes **explainability** and **user control** over fully automated processing.
