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
    EUR_TO_INR = 91.0  # Exchange rate
    
    @staticmethod
    def get_inr_amount(amount: float, currency: str) -> float:
        curr = (currency or "INR").upper().strip()
        if curr == "USD":
            return amount * ExpenseService.USD_TO_INR
        elif curr == "EUR":
            return amount * ExpenseService.EUR_TO_INR
        return amount

    @staticmethod
    def calculate_group_balances(group_id: str, db: Session) -> Dict[str, Dict]:
        """Calculate net balances for all members in a group"""
        
        # Get all members in the group (active or inactive, since we need past history)
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
        } for member in members}
        
        # Get all non-deleted expenses for the group (including settlements!)
        expenses = db.query(Expense).filter(
            and_(
                Expense.group_id == group_id,
                Expense.is_deleted == False
            )
        ).all()
        
        # Process each expense
        for expense in expenses:
            ExpenseService._process_expense(expense, balances, db)
        
        # Calculate net for each person: owes - owed (Positive: owes, Negative: is owed)
        for user_id in balances:
            balances[user_id]["net"] = balances[user_id]["owes"] - balances[user_id]["owed"]
        
        return balances
    
    @staticmethod
    def _process_expense(expense: Expense, balances: Dict, db: Session):
        """Process a single expense/settlement and update balances"""
        
        payer_id = expense.paid_by_user_id
        
        # Get expense splits
        splits = db.query(ExpenseSplit).filter(
            ExpenseSplit.expense_id == expense.id
        ).all()
        
        # Convert total amount to INR
        currency = expense.currency or "INR"
        total_amount_inr = ExpenseService.get_inr_amount(expense.amount, currency)
        
        # 1. Payer gets credit for paying
        if payer_id in balances:
            balances[payer_id]["owed"] += total_amount_inr
            
        # 2. Add each person's share to their 'owes'
        if expense.split_type == "equal":
            if len(splits) > 0:
                share_amount_inr = total_amount_inr / len(splits)
                for split in splits:
                    if split.user_id in balances:
                        balances[split.user_id]["owes"] += share_amount_inr
        
        elif expense.split_type == "unequal":
            for split in splits:
                if split.user_id in balances:
                    split_amount_inr = ExpenseService.get_inr_amount(split.amount or 0.0, currency)
                    balances[split.user_id]["owes"] += split_amount_inr
        
        elif expense.split_type == "percentage":
            for split in splits:
                if split.user_id in balances:
                    percentage = split.percentage or 0.0
                    share_amount_inr = (percentage / 100.0) * total_amount_inr
                    balances[split.user_id]["owes"] += share_amount_inr
        
        elif expense.split_type == "share":
            total_shares = sum(s.shares or 0 for s in splits)
            if total_shares > 0:
                for split in splits:
                    if split.user_id in balances:
                        shares = split.shares or 0
                        share_amount_inr = (shares / total_shares) * total_amount_inr
                        balances[split.user_id]["owes"] += share_amount_inr
    
    @staticmethod
    def get_settlement_summary(group_id: str, db: Session) -> List[Dict]:
        """Generate minimal settlement transactions needed to clear all debts"""
        
        balances = ExpenseService.calculate_group_balances(group_id, db)
        
        # Get debtors and creditors
        debtors = []  # People who owe money (net > 0)
        creditors = []  # People who are owed money (net < 0)
        
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
        """Get detailed breakdown of all expenses/settlements a user is involved in"""
        
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
                
                # Calculate user's share in original currency and INR
                user_share = 0.0
                currency = expense.currency or "INR"
                
                if expense.split_type == "equal":
                    if len(splits) > 0:
                        user_share = expense.amount / len(splits)
                else:
                    user_split = next((s for s in splits if s.user_id == user_id), None)
                    if user_split:
                        if expense.split_type == "unequal":
                            user_share = user_split.amount or 0.0
                        elif expense.split_type == "percentage":
                            user_share = ((user_split.percentage or 0.0) / 100.0) * expense.amount
                        elif expense.split_type == "share":
                            total_shares = sum(s.shares or 0 for s in splits)
                            if total_shares > 0:
                                user_share = (((user_split.shares or 0) / total_shares) * expense.amount)
                
                user_share_inr = ExpenseService.get_inr_amount(user_share, currency)
                amount_inr = ExpenseService.get_inr_amount(expense.amount, currency)
                
                breakdown.append({
                    "expense_id": expense.id,
                    "description": expense.description,
                    "amount": expense.amount,
                    "currency": expense.currency,
                    "amount_inr": round(amount_inr, 2),
                    "paid_by": payer.full_name or payer.username,
                    "date": expense.expense_date,
                    "your_share": round(user_share, 2),
                    "your_share_inr": round(user_share_inr, 2),
                    "you_paid": expense.paid_by_user_id == user_id,
                    "is_settlement": expense.is_settlement,
                    "notes": expense.notes
                })
        
        return breakdown

