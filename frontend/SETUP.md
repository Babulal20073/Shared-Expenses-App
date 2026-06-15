# Shared Expenses App - Frontend Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Environment Setup
Create `.env.local`:
```
VITE_API_URL=http://localhost:5000
```

### 3. Run Dev Server
```bash
npm run dev
```

Frontend will be at: http://localhost:5173

### 4. Build for Production
```bash
npm run build
```

Output will be in `dist/` folder

## Environment Variables

- `VITE_API_URL` - Backend API URL

## Project Structure

```
frontend/src/
├── App.tsx              # Main component
├── main.tsx             # Entry point
├── pages/               # Page components
├── services/            # API client
└── styles/              # CSS files
```

## Pages

1. **LoginPage** - User login
2. **SignupPage** - User registration
3. **DashboardPage** - List user's groups
4. **GroupPage** - Group details, expenses, balances, CSV import

## Features

- User authentication with JWT
- Create and manage expense groups
- Track shared expenses with multiple split types
- Import expenses from CSV with anomaly detection
- Real-time balance calculations
- Settlement planning

## Development

Watch mode with hot reload:
```bash
npm run dev
```

## Deployment

Build and deploy to:
- Vercel (recommended for Vite apps)
- Netlify
- Any static hosting service

Just deploy the `dist/` folder after building.
