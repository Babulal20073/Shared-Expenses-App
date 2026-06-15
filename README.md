# Shared Expenses App

A web application for managing shared expenses among flatmates with support for multiple split types, CSV import with anomaly detection, and automatic balance calculations.

## Features

- **User Authentication**: Signup and login with JWT tokens
- **Group Management**: Create groups and manage members who join/leave
- **Expense Tracking**: Record shared expenses with multiple split types:
  - Equal split
  - Unequal split (custom amounts)
  - Percentage-based split
  - Share-based split
- **CSV Import**: Bulk import expenses with automatic anomaly detection
- **Balance Calculation**: Get real-time balance summaries for all members
- **Settlement Plan**: Minimal transactions needed to settle all debts

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Relational database
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation

### Frontend
- **React** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Axios** - HTTP client

## Project Structure

```
backend/
  src/
    config.py           # Configuration and settings
    database.py         # Database connection
    index.py            # Main FastAPI app
    schemas.py          # Pydantic models
    middleware/
      auth.py          # Authentication middleware
    models/
      models.py        # SQLAlchemy models
    routes/
      auth.py          # Auth endpoints
      groups.py        # Group management endpoints
      expenses.py      # Expense and import endpoints
      balances.py      # Balance calculation endpoints
    services/
      auth_service.py       # Auth business logic
      expense_service.py    # Expense calculations
      csv_importer.py       # CSV parsing and anomaly detection
    utils/
      auth.py          # Password hashing and JWT tokens
  requirements.txt
  .env.example

frontend/
  src/
    App.tsx            # Main app component
    pages/             # Page components
    services/          # API service
    styles/            # CSS styles
  index.html
  vite.config.ts
  package.json
```

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL 12+

### Backend Setup

1. Create virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your database credentials and secret key
```

4. Initialize database:
```bash
python -m src.database
```

5. Run the server:
```bash
uvicorn src.index:app --reload
```

Server will be available at `http://localhost:5000`

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env.local`:
```
VITE_API_URL=http://localhost:5000
```

3. Run dev server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## API Documentation

Once the backend is running, visit `http://localhost:5000/docs` for interactive API documentation.

## CSV Import Format

The app expects a CSV file with the following columns:
- `date` - Expense date (DD-MM-YYYY)
- `description` - What was bought
- `paid_by` - Name of person who paid
- `amount` - Amount spent
- `currency` - Currency (INR, USD, EUR)
- `split_type` - How to split (equal, unequal, percentage, share)
- `split_with` - Names of people involved (semicolon-separated)
- `split_details` - Details for unequal/percentage/share splits
- `notes` - Additional notes

## Supported Split Types

1. **Equal**: Expense divided equally among all participants
2. **Unequal**: Custom amounts for each person (e.g., "Aisha 500; Rohan 300")
3. **Percentage**: Percentage distribution (e.g., "Aisha 50%; Rohan 50%")
4. **Share**: Proportional to shares (e.g., "Aisha 2; Rohan 1" = 2:1 ratio)

## Anomaly Detection

The CSV importer detects and handles:
- Missing or invalid dates
- Invalid amounts
- Missing currencies (defaults to INR)
- Duplicate entries
- Settlement entries (not expenses)
- Missing participant information
- Inconsistent split details
- Member joined/left after relevant dates

Each anomaly is logged with:
- Row number
- Field name
- Issue description
- Action taken
- Severity level (error, warning, info)

## Database Schema

See `SCOPE.md` for detailed database schema documentation.

## Decision Log

See `DECISIONS.md` for significant architectural and business logic decisions.

## AI Usage

See `AI_USAGE.md` for documentation on AI assistance used in development.

---

**Author**: Developed for Spreetail TC Assessment
**Deadline**: June 15, 2026
