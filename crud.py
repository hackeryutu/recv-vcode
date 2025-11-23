from sqlalchemy.orm import Session
import models, schemas

import uuid
import secrets
import shortuuid

def get_email_account(db: Session, mail_id: str):
    return db.query(models.EmailAccount).filter(models.EmailAccount.mail_id == mail_id).first()

def get_email_account_by_email(db: Session, email: str):
    return db.query(models.EmailAccount).filter(models.EmailAccount.email == email).first()

def get_email_accounts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.EmailAccount).offset(skip).limit(limit).all()

def create_email_account(db: Session, account: schemas.EmailAccountCreate):
    account_data = account.dict()
    if not account_data.get("mail_id"):
        account_data["mail_id"] = shortuuid.uuid()
    if not account_data.get("access_token"):
        account_data["access_token"] = secrets.token_urlsafe(16)
    
    db_account = models.EmailAccount(**account_data)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

def update_email_account(db: Session, account_id: int, account_update: schemas.EmailAccountUpdate):
    db_account = db.query(models.EmailAccount).filter(models.EmailAccount.id == account_id).first()
    if not db_account:
        return None
    
    update_data = account_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_account, key, value)
    
    db.commit()
    db.refresh(db_account)
    return db_account

def delete_email_account(db: Session, account_id: int):
    db_account = db.query(models.EmailAccount).filter(models.EmailAccount.id == account_id).first()
    if db_account:
        db.delete(db_account)
        db.commit()
        return True
    return False
