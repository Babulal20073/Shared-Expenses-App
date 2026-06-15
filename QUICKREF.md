# Quick Reference Guide

## Running the Application

### Option 1: Automated Setup (Linux/Mac)
```bash
bash quick-start.sh
```

### Option 2: Manual Setup

#### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.index:app --reload
```

Server: http://localhost:5000
API Docs: http://localhost:5000/docs

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## Key URLs

| Component | URL | Purpose |
|-----------|-----|---------|
| Frontend | http://localhost:5173 | Main app |
| API | http://localhost:5000 | Backend server |
| API Docs | http://localhost:5000/docs | Interactive Swagger UI |
| API ReDoc | http://localhost:5000/redoc | Alternative API docs |

---

## CSV Import Format

### Required Columns
- `date` - DD-MM-YYYY format
- `description` - What was purchased
- `paid_by` - Person who paid
- `amount` - Numeric amount
- `currency` - INR, USD, EUR, etc.
- `split_type` - equal, unequal, percentage, share
- `split_with` - Names separated by ;
- `split_details` - Details for non-equal splits
- `notes` - Optional notes

### Example
```csv
date,description,paid_by,amount,currency,split_type,split_with,split_details,notes
01-02-2026,February rent,Aisha,48000,INR,equal,Aisha;Rohan;Priya;Meera,,
08-02-2026,Dinner,Dev,3200,INR,equal,Aisha;Rohan;Priya;Dev,,Dev visiting
20-02-2026,Birthday cake,Rohan,1500,INR,unequal,Rohan;Priya;Meera,Rohan 700; Priya 400; Meera 400,Aisha not charged
```

---

## Test Data

### Create Test User
- Email: `test@example.com`
- Password: `password123`

### Test Group
- Name: "Test Group"
- Members: Add other test users

### Test Expense
- Amount: 1200
- Split: Equal among 4 people = 300 each

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn src.index:app --reload --port 5001
```

### Database Connection Error
```bash
# Check PostgreSQL is running
psql

# Or update DATABASE_URL in .env to:
DATABASE_URL=sqlite:///./test.db
```

### Module Not Found
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate      # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend npm issues
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## API Examples

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Create Group
```bash
curl -X POST http://localhost:5000/api/groups \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Group","description":"Testing"}'
```

### Get Balances
```bash
curl -X GET http://localhost:5000/api/groups/{group_id}/balances \
  -H "Authorization: Bearer <token>"
```

### Import CSV
```bash
curl -X POST http://localhost:5000/api/groups/{group_id}/import-csv \
  -H "Authorization: Bearer <token>" \
  -F "file=@expenses.csv"
```

---

## Development Workflow

1. **Start both servers** (in separate terminals)
2. **Make changes** to code
3. **Auto-reload** happens automatically
4. **Test** in browser at http://localhost:5173
5. **Check API** at http://localhost:5000/docs

---

## Deployment Checklist

- [ ] Database created and running
- [ ] Environment variables set
- [ ] Dependencies installed
- [ ] Both services started
- [ ] Frontend accessible at port 5173
- [ ] Backend accessible at port 5000
- [ ] Can login/signup
- [ ] Can create groups
- [ ] Can import CSV
- [ ] Balances calculated correctly

---

## Key Files to Know

- `backend/src/index.py` - Main FastAPI app
- `backend/src/services/csv_importer.py` - CSV anomaly detection
- `backend/src/services/expense_service.py` - Balance calculations
- `frontend/src/App.tsx` - Main React component
- `frontend/src/pages/GroupPage.tsx` - Group/expense UI

---

For detailed documentation, see README.md, SCOPE.md, DECISIONS.md, and AI_USAGE.md
