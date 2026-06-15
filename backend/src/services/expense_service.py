import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.models import Expense, ExpenseSplit, User, Group, GroupMember


class ExpenseService:
    USD_TO_INR = 84.5  # Exchange rate
    
    @staticmethod
    def calculate_group_balances(group_id: str, db: Session) -> Dict[str, Dict]:
        """Calculate net balances for all members in a group"""
        
        # Get all active members in the group at any point
        members = db.query(User).join(
            GroupMember, User.id == GroupMember.user_id
        ).filter(GroupMember.group_id == group_id).all()
        
        # Initialize balances
        balances = {member.id: {
            "user": member,
            "owes": 0.0,
            "owed": 0.0,
            "net": 0.0,
            "currency": "INR",
            "expenses": []
        } for member in members}
        
        # Get all non-deleted, non-settlement expenses for the group
        expenses = db.query(Expense).filter(
            and_(
                Expense.group_id == group_id,
                Expense.is_deleted == False,
                Expense.is_settlement == False
            )
        ).all()
        
        # Process each expense
        for expense in expenses:
            ExpenseService._process_expense(expense, balances, db)
        
        # Calculate net for each person
        for user_id in balances:
            balances[user_id]["net"] = balances[user_id]["owed"] - balances[user_id]["owes"]
        
        return balances
    
    @staticmethod
    def _process_expense(expense: Expense, balances: Dict, db: Session):
        """Process a single expense and update balances"""
        
        payer_id = expense.paid_by_user_id
        payer = db.query(User).filter(User.id == payer_id).first()
        
        # Get expense splits
        splits = db.query(ExpenseSplit).filter(
            ExpenseSplit.expense_id == expense.id
        ).all()
        
        # Calculate each person's share
        total_amount = expense.amount
        
        if expense.split_type == "equal":
            share_amount = total_amount / len(splits)
            for split in splits:
                if split.user_id != payer_id:
                    balances[split.user_id]["owes"] += share_amount
        
        elif expense.split_type == "unequal":
            # Split amounts stored in split.amount
            for split in splits:
                if split.user_id != payer_id:
                    balances[split.user_id]["owes"] += split.amount
        
        elif expense.split_type == "percentage":
            # Split percentages stored in split.percentage
            for split in splits:
                if split.user_id != payer_id:
                    share = (split.percentage / 100) * total_amount
                    balances[split.user_id]["owes"] += share
        
        elif expense.split_type == "share":
            # Split by shares
            total_shares = sum(s.shares or 1 for s in splits)
            for split in splits:
                if split.user_id != payer_id:
                    shares = split.shares or 1
                    share = (shares / total_shares) * total_amount
                    balances[split.user_id]["owes"] += share
        
        # Payer is owed by others
        balances[payer_id]["owed"] += (total_amount - balances[payer_id]["owes"])
    
    @staticmethod
    def get_settlement_summary(group_id: str, db: Session) -> List[Dict]:
        """Generate minimal settlement transactions needed to clear all debts"""
        
        balances = ExpenseService.calculate_group_balances(group_id, db)
        
        # Get debtors and creditors
        debtors = []  # People who owe money
        creditors = []  # People who are owed money
        
        for user_id, balance in balances.items():
            net = balance["net"]
            if net > 0.01:  # User owes money
                debtors.append({"user_id": user_id, "user": balance["user"], "amount": net})
            elif net < -0.01:  # User is owed money
                creditors.append({"user_id": user_id, "user": balance["user"], "amount": abs(net)})
        
        # Generate settlements
        settlements = []
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditors.sort(key=lambda x: x["amount"], reverse=True)
        
        d_idx, c_idx = 0, 0
        
        while d_idx < len(debtors) and c_idx < len(creditors):
            debtor = debtors[d_idx]
            creditor = creditors[c_idx]
            
            settle_amount = min(debtor["amount"], creditor["amount"])
            
            settlements.append({
                "from_user_id": debtor["user_id"],
                "from_user": debtor["user"].full_name or debtor["user"].username,
                "to_user_id": creditor["user_id"],
                "to_user": creditor["user"].full_name or creditor["user"].username,
                "amount": round(settle_amount, 2)
            })
            
            debtor["amount"] -= settle_amount
            creditor["amount"] -= settle_amount
            
            if debtor["amount"] < 0.01:
                d_idx += 1
            if creditor["amount"] < 0.01:
                c_idx += 1
        
        return settlements
    
    @staticmethod
    def get_user_expense_breakdown(group_id: str, user_id: str, db: Session) -> List[Dict]:
        """Get detailed breakdown of all expenses a user is involved in"""
        
        expenses = db.query(Expense).filter(
            and_(
                Expense.group_id == group_id,
                Expense.is_deleted == False
            )
        ).all()
        
        breakdown = []
        
        for expense in expenses:
            splits = db.query(ExpenseSplit).filter(
                ExpenseSplit.expense_id == expense.id
            ).all()
            
            # Check if user is involved
            involved = any(s.user_id == user_id for s in splits) or expense.paid_by_user_id == user_id
            
            if involved:
                payer = db.query(User).filter(User.id == expense.paid_by_user_id).first()
                
                # Calculate user's share
                user_share = 0.0
                if expense.split_type == "equal":
                    user_share = expense.amount / len(splits)
                else:
                    user_split = next((s for s in splits if s.user_id == user_id), None)
                    if user_split:
                        if expense.split_type == "unequal":
                            user_share = user_split.amount
                        elif expense.split_type == "percentage":
                            user_share = (user_split.percentage / 100) * expense.amount
                        elif expense.split_type == "share":
                            total_shares = sum(s.shares or 1 for s in splits)
                            user_share = ((user_split.shares or 1) / total_shares) * expense.amount
                
                breakdown.append({
                    "expense_id": expense.id,
                    "description": expense.description,
                    "amount": expense.amount,
                    "currency": expense.currency,
                    "paid_by": payer.full_name or payer.username,
                    "date": expense.expense_date,
                    "your_share": round(user_share, 2),
                    "you_paid": expense.paid_by_user_id == user_id,
                    "notes": expense.notes
                })
        
        return breakdown
