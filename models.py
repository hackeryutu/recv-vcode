from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, func
from database import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    mail_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    imap_server = Column(String)
    access_token = Column(String)  # Token required to access this account via API
    default_sender_filter = Column(String, nullable=True)


class EmailCache(Base):
    __tablename__ = "email_cache"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("email_accounts.id"), unique=True, nullable=False)
    message_ids = Column(Text, nullable=True)  # JSON serialized list of ids
    payload = Column(Text, nullable=True)  # JSON serialized email summary list
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
