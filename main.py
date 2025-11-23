from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
import secrets
import logging
import re
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import List, Optional

import models, schemas, crud, database, mail_service, config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

security = HTTPBasic()
templates = Jinja2Templates(directory="templates")

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, config.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, config.ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse("admin/index.html", {"request": request, "username": username})

@app.get("/admin/db", response_class=HTMLResponse)
def admin_db_page(request: Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse("admin/db_view.html", {"request": request, "username": username})

def get_table_list():
    inspector = inspect(database.engine)
    return inspector.get_table_names()

def validate_table_name(table_name: str):
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    available_tables = get_table_list()
    if table_name not in available_tables:
        raise HTTPException(status_code=404, detail="Table not found")
    return table_name

@app.get("/admin/api/db/tables")
def list_db_tables(username: str = Depends(get_current_username)):
    return {"tables": get_table_list()}

@app.get("/admin/api/db/table/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    username: str = Depends(get_current_username),
):
    validated_name = validate_table_name(table_name)
    with database.engine.connect() as conn:
        result = conn.execute(
            text(f'SELECT * FROM "{validated_name}" LIMIT :limit OFFSET :offset'),
            {"limit": limit, "offset": offset},
        )
        rows = [dict(row._mapping) for row in result]

        total_result = conn.execute(text(f'SELECT COUNT(*) FROM "{validated_name}"'))
        total = total_result.scalar() or 0

    return {"table": validated_name, "columns": list(rows[0].keys()) if rows else [], "rows": rows, "total": total}

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/admin/accounts", response_model=schemas.EmailAccountResponse)
def create_account(account: schemas.EmailAccountCreate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    # Check if email already exists
    db_account = crud.get_email_account_by_email(db, email=account.email)
    if db_account:
        raise HTTPException(status_code=400, detail="邮箱地址已存在")
    return crud.create_email_account(db=db, account=account)

@app.get("/admin/accounts", response_model=List[schemas.EmailAccountResponse])
def read_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    accounts = crud.get_email_accounts(db, skip=skip, limit=limit)
    return accounts

@app.put("/admin/accounts/{account_id}", response_model=schemas.EmailAccountResponse)
def update_account(account_id: int, account: schemas.EmailAccountUpdate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    # Check if the account exists
    current_account = db.query(models.EmailAccount).filter(models.EmailAccount.id == account_id).first()
    if not current_account:
        raise HTTPException(status_code=404, detail="Account not found")

    # If email is being updated, check if it's already used by another account
    if account.email and account.email != current_account.email:
        existing_account = crud.get_email_account_by_email(db, email=account.email)
        if existing_account:
            raise HTTPException(status_code=400, detail="邮箱地址已存在")

    db_account = crud.update_email_account(db, account_id=account_id, account_update=account)
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    return db_account

@app.delete("/admin/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    success = crud.delete_email_account(db, account_id=account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deleted successfully"}

@app.get("/mail", response_class=HTMLResponse)
def read_mail(
    request: Request,
    mail_id: str, 
    token: str, 
    sender: Optional[str] = None,
    db: Session = Depends(get_db)
):
    account = crud.get_email_account(db, mail_id=mail_id)
    if not account:
        raise HTTPException(status_code=404, detail="Mail ID not found")
    
    if account.access_token != token:
        raise HTTPException(status_code=404, detail="Mail ID not found")
    
    # Just serve the page with context, don't fetch emails yet
    return templates.TemplateResponse("app/mail_view.html", {
        "request": request,
        "email": account.email,
        "mail_id": mail_id,
        "token": token,
        "sender": sender
    })

@app.get("/api/mail/messages")
def get_mail_messages(
    mail_id: str,
    token: str,
    sender: Optional[str] = None,
    db: Session = Depends(get_db)
):
    logger.info(f"[API] /api/mail/messages called - mail_id: {mail_id}, sender: {sender}")

    account = crud.get_email_account(db, mail_id=mail_id)
    if not account:
        logger.warning(f"[API] Mail ID not found: {mail_id}")
        raise HTTPException(status_code=404, detail="Mail ID not found")

    if account.access_token != token:
        logger.warning(f"[API] Invalid token for mail_id: {mail_id}")
        raise HTTPException(status_code=403, detail="Invalid token")

    logger.info(f"[API] Fetching emails for: {account.email}, imap_server: {account.imap_server}")
    emails = mail_service.fetch_recent_emails(account, sender_filter=sender, db=db)

    if isinstance(emails, list):
        logger.info(f"[API] Fetch success - account: {account.email}, sender: {sender or account.default_sender_filter}, fetched: {len(emails)}")
    elif isinstance(emails, dict) and "error" in emails:
        logger.error(f"[API] Fetch failed - account: {account.email}, sender: {sender or account.default_sender_filter}, reason: {emails.get('error')}")
    elif isinstance(emails, dict):
        logger.info(f"[API] Fetch result - account: {account.email}, sender: {sender or account.default_sender_filter}, message: {emails}")
    else:
        logger.warning(f"[API] Fetch returned unexpected result type={type(emails).__name__} for account: {account.email}")

    return emails
