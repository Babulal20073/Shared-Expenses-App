import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from config import get_settings

# Import routes
from routes import auth, groups, expenses, balances

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Shared Expenses API",
    description="API for managing shared expenses among flatmates",
    version="1.0.0"
)

settings = get_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(balances.router)


@app.get("/")
async def root():
    return {
        "message": "Shared Expenses API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "index:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.ENVIRONMENT == "development"
    )
