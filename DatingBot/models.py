from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import enum

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"

class SubscriptionType(enum.Enum):
    FREE = "free"
    PREMIUM = "premium"
    OWNER = "owner"

class MatchStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"
    BLOCKED = "blocked"

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_registered = Column(Boolean, default=False)
    subscription_type = Column(Enum(SubscriptionType), default=SubscriptionType.FREE)
    premium_expires_at = Column(DateTime, nullable=True)
    gender_views_used = Column(Integer, default=0)  # Track how many times user has seen gender info
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sent_matches = relationship("Match", foreign_keys="Match.user1_id", back_populates="user1")
    received_matches = relationship("Match", foreign_keys="Match.user2_id", back_populates="user2")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    reports_made = relationship("Report", foreign_keys="Report.reporter_id", back_populates="reporter")
    reports_received = relationship("Report", foreign_keys="Report.reported_id", back_populates="reported")
    
    def __repr__(self):
        return f'<User {self.telegram_id}>'

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    looking_for = Column(Enum(Gender), nullable=False)
    bio = Column(Text, nullable=True)
    interests = Column(Text, nullable=True)  # JSON string of interests
    min_age = Column(Integer, default=18)
    max_age = Column(Integer, default=50)
    city = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f'<UserProfile {self.user_id}>'

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(MatchStatus), default=MatchStatus.PENDING)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    anonymous_id_1 = Column(String(20), nullable=False)  # Anonymous ID for user1
    anonymous_id_2 = Column(String(20), nullable=False)  # Anonymous ID for user2
    
    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="sent_matches")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="received_matches")
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Match {self.id}: {self.user1_id} -> {self.user2_id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_read = Column(Boolean, default=False)
    
    # Relationships
    match = relationship("Match", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    
    def __repr__(self):
        return f'<Message {self.id}: {self.sender_id} -> {self.receiver_id}>'

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reported_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=True)
    reason = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_resolved = Column(Boolean, default=False)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports_made")
    reported = relationship("User", foreign_keys=[reported_id], back_populates="reports_received")
    
    def __repr__(self):
        return f'<Report {self.id}: {self.reporter_id} -> {self.reported_id}>'

class BlockedUser(db.Model):
    __tablename__ = 'blocked_users'
    
    id = Column(Integer, primary_key=True)
    blocker_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    blocked_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<BlockedUser {self.blocker_id} -> {self.blocked_id}>'
