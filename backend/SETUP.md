# Shared Expenses App - Backend Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set up Database
Make sure PostgreSQL is running, then:
```bash
# Create database
createdb shared_expenses

# Run migrations
python -m src.database
```

### 3. Run Server
```bash
uvicorn src.index:app --reload --port 5000
```

Server will be at: http://localhost:5000
API docs: http://localhost:5000/docs

## Environment Variables

See `.env.example` for configuration. Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - For JWT token signing
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time

## Project Structure

```
backend/src/
├── index.py              # FastAPI app entry point
├── config.py             # Settings management
├── database.py           # Database connection
├── schemas.py            # Pydantic models
├── routes/              # API endpoints
├── models/              # SQLAlchemy models
├── services/            # Business logic
├── middleware/          # Auth middleware
└── utils/               # Helper functions
```

## API Endpoints

- `POST /api/auth/signup` - Register user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Current user info
- `GET /api/groups` - List user's groups
- `POST /api/groups` - Create group
- `GET /api/groups/{id}` - Get group details
- `GET /api/groups/{id}/expenses` - List expenses
- `POST /api/groups/{id}/import-csv` - Import CSV
- `GET /api/groups/{id}/balances` - Get balances
- `GET /api/groups/{id}/balances/settlement` - Settlement plan

Full documentation at `/docs` endpoint
