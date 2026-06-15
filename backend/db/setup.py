"""Initialize database"""
from database import engine, Base
from models.models import User, Group, GroupMember, Expense, ExpenseSplit, ImportReport

# Create all tables
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")
