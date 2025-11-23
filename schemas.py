from pydantic import BaseModel
from typing import Optional

class EmailAccountBase(BaseModel):
    mail_id: str
    email: str
    password: str
    imap_server: str
    access_token: str
    default_sender_filter: Optional[str] = None

class EmailAccountCreate(EmailAccountBase):
    mail_id: Optional[str] = None
    access_token: Optional[str] = None

class EmailAccountUpdate(BaseModel):
    mail_id: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    imap_server: Optional[str] = None
    access_token: Optional[str] = None
    default_sender_filter: Optional[str] = None

class EmailAccountResponse(EmailAccountBase):
    id: int

    class Config:
        orm_mode = True
