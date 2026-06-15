import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.models import User, Group, GroupMember
from schemas import UserCreate, UserResponse, GroupCreate
from utils.auth import hash_password
from datetime import datetime
import uuid


class AuthService:
    @staticmethod
    def create_user(user_data: UserCreate, db: Session) -> User:
        """Create a new user"""
        db_user = db.query(User).filter(
            or_(User.email == user_data.email, User.username == user_data.username)
        ).first()
        
        if db_user:
            raise ValueError("User with this email or username already exists")
        
        hashed_password = hash_password(user_data.password)
        db_user = User(
            id=str(uuid.uuid4()),
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def get_user_by_email(email: str, db: Session) -> User:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(username: str, db: Session) -> User:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()


class GroupService:
    @staticmethod
    def create_group(group_data: GroupCreate, creator_id: str, db: Session) -> Group:
        """Create a new group"""
        group = Group(
            id=str(uuid.uuid4()),
            name=group_data.name,
            description=group_data.description,
            created_by=creator_id
        )
        
        db.add(group)
        db.flush()
        
        # Add creator as member
        group_member = GroupMember(
            id=str(uuid.uuid4()),
            group_id=group.id,
            user_id=creator_id,
            joined_at=datetime.now()
        )
        db.add(group_member)
        
        # Add other members if provided
        if group_data.member_emails:
            for email in group_data.member_emails:
                user = db.query(User).filter(User.email == email).first()
                if user:
                    group_member = GroupMember(
                        id=str(uuid.uuid4()),
                        group_id=group.id,
                        user_id=user.id,
                        joined_at=datetime.now()
                    )
                    db.add(group_member)
        
        db.commit()
        db.refresh(group)
        
        return group
    
    @staticmethod
    def add_member_to_group(group_id: str, user_id: str, db: Session) -> GroupMember:
        """Add a user to a group"""
        # Check if already a member
        existing = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        ).first()
        
        if existing:
            if existing.left_at:
                # Reactivate
                existing.left_at = None
                existing.is_active = True
                db.commit()
                return existing
            raise ValueError("User is already a member of this group")
        
        member = GroupMember(
            id=str(uuid.uuid4()),
            group_id=group_id,
            user_id=user_id,
            joined_at=datetime.now()
        )
        
        db.add(member)
        db.commit()
        db.refresh(member)
        
        return member
    
    @staticmethod
    def remove_member_from_group(group_id: str, user_id: str, db: Session):
        """Remove a user from a group"""
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        ).first()
        
        if not member:
            raise ValueError("User is not a member of this group")
        
        member.left_at = datetime.now()
        member.is_active = False
        db.commit()
    
    @staticmethod
    def get_group_members(group_id: str, db: Session):
        """Get all active members of a group"""
        members = db.query(User).join(
            GroupMember, User.id == GroupMember.user_id
        ).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        ).all()
        
        return members
    
    @staticmethod
    def get_user_groups(user_id: str, db: Session):
        """Get all groups a user is a member of"""
        groups = db.query(Group).join(
            GroupMember, Group.id == GroupMember.group_id
        ).filter(
            GroupMember.user_id == user_id,
            GroupMember.is_active == True
        ).all()
        
        return groups
