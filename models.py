from sqlalchemy import Column, Integer, String
from database import Base

class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    mail_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    imap_server = Column(String)
    access_token = Column(String) # Token required to access this account via API
    default_sender_filter = Column(String, nullable=True)
