import imaplib
import email
import json
from email.header import decode_header
from datetime import datetime, timezone, timedelta
import logging
import socket
from sqlalchemy.orm import Session
import crud
import models
import config as app_config

logger = logging.getLogger(__name__)

GENERIC_TIMEOUT_ERROR = "邮件服务超时，请稍后再试"
GENERIC_CONNECTION_ERROR = "无法连接邮件服务器，请稍后重试"
GENERIC_FETCH_ERROR = "获取邮件失败，请稍后再试"

def fetch_recent_emails(
    config: models.EmailAccount,
    sender_filter: str = None,
    limit: int = 5,
    timeout: int = None,
    db: Session = None,
):
    # Use configured timeout if not specified
    if timeout is None:
        timeout = app_config.IMAP_TIMEOUT

    target_sender = sender_filter if sender_filter else config.default_sender_filter
    logger.info(f"[MAIL] fetch_recent_emails started - email: {config.email}, sender_filter: {target_sender}, timeout: {timeout}s")

    cache_entry = crud.get_email_cache(db, config.id) if db else None

    if not target_sender:
        logger.warning("[MAIL] No sender filter specified")
        return {"error": "No sender filter specified"}

    try:
        logger.info(f"[MAIL] Connecting to IMAP server: {config.imap_server} (timeout: {timeout}s)")
        # Create IMAP connection with timeout
        mail = imaplib.IMAP4_SSL(config.imap_server, timeout=timeout)
        logger.info("[MAIL] IMAP connection established, attempting login...")

        # Set socket timeout for all subsequent operations
        if hasattr(mail, 'sock') and mail.sock:
            mail.sock.settimeout(timeout)

        mail.login(config.email, config.password)
        logger.info("[MAIL] Login successful")
    except socket.timeout:
        logger.error(f"[MAIL] IMAP connection/login timeout after {timeout}s - Failed to connect or authenticate to {config.imap_server}")
        return {"error": GENERIC_TIMEOUT_ERROR}
    except Exception as e:
        logger.error(f"[MAIL] Connection/Login failed: {str(e)}")
        return {"error": GENERIC_CONNECTION_ERROR}

    try:
        logger.info("[MAIL] Selecting inbox...")
        try:
            mail.select("inbox")
            logger.info("[MAIL] Inbox selected")
        except socket.timeout:
            logger.error(f"[MAIL] Timeout while selecting inbox after {timeout}s")
            raise

        # Search for emails from the specific sender
        logger.info(f"[MAIL] Searching emails from: {target_sender}")
        try:
            status, messages = mail.search(None, f'(FROM "{target_sender}")')
            logger.info(f"[MAIL] Search completed - status: {status}")
        except socket.timeout:
            logger.error(f"[MAIL] Timeout while searching emails from '{target_sender}' after {timeout}s")
            raise

        if status != "OK":
            logger.warning("[MAIL] Search status not OK")
            return {"message": "No emails found"}

        email_ids = messages[0].split()
        logger.info(f"[MAIL] Found {len(email_ids)} email(s)")

        if not email_ids:
            logger.info(f"[MAIL] No emails found from {target_sender}")
            return {"message": f"No emails found from {target_sender}"}

        # Get the last N emails
        recent_email_ids = email_ids[-limit:]
        recent_email_ids.reverse() # Newest first
        logger.info(f"[MAIL] Processing {len(recent_email_ids)} recent email(s)")

        if not recent_email_ids:
            return []

        id_strings = [e_id.decode() for e_id in recent_email_ids if e_id]

        if cache_entry and cache_entry.message_ids and cache_entry.payload:
            try:
                cached_ids = json.loads(cache_entry.message_ids)
                cached_payload = json.loads(cache_entry.payload)
            except json.JSONDecodeError:
                cached_ids = cached_payload = None
            else:
                if cached_ids == id_strings:
                    logger.info(f"[MAIL] Returning cached emails (no new messages) for account: {config.email}")
                    return cached_payload

        # Fetch all headers in a single IMAP call for better performance
        message_set = ",".join(id_strings)
        logger.info(f"[MAIL] Fetching headers in batch for ids: {message_set}")

        try:
            status, msg_data = mail.fetch(message_set, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
        except socket.timeout:
            logger.error(f"[MAIL] Timeout while fetching batched headers after {timeout}s")
            raise

        if status != "OK":
            logger.warning(f"[MAIL] Failed to fetch headers batch, status: {status}")
            return {"error": GENERIC_FETCH_ERROR}

        headers_map = {}
        for response_part in msg_data:
            if not isinstance(response_part, tuple) or not response_part[1]:
                continue

            response_id = response_part[0]
            if isinstance(response_id, bytes):
                response_id = response_id.decode()
            response_id = response_id.split()[0]

            msg = email.message_from_bytes(response_part[1])
            email_content = {"subject": "Unknown", "from": "", "date": ""}

            raw_subject = msg.get("Subject")
            if raw_subject:
                subject, encoding = decode_header(raw_subject)[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                email_content["subject"] = subject

            email_content["from"] = msg.get("From", "")

            raw_date = msg.get("Date")
            formatted_date = raw_date
            try:
                if raw_date:
                    parsed_date = email.utils.parsedate_to_datetime(raw_date)
                    # Convert to GMT+8 timezone
                    gmt8_tz = timezone(timedelta(hours=8))
                    gmt8_date = parsed_date.astimezone(gmt8_tz)
                    formatted_date = gmt8_date.strftime("%Y/%m/%d %H:%M:%S")
            except:
                pass

            email_content["date"] = formatted_date or ""
            email_content["id"] = response_id
            headers_map[response_id] = email_content

        email_list = []
        for e_id in recent_email_ids:
            key = e_id.decode()
            if key in headers_map:
                email_list.append(headers_map[key])
            else:
                logger.warning(f"[MAIL] Missing header data for email id {key}")

        if db:
            try:
                crud.upsert_email_cache(
                    db,
                    config.id,
                    json.dumps(id_strings, ensure_ascii=False),
                    json.dumps(email_list, ensure_ascii=False),
                )
            except Exception as cache_error:
                logger.warning(f"[MAIL] Failed to update email cache: {cache_error}")

        logger.info(f"[MAIL] Closing connection, total emails fetched: {len(email_list)}")
        try:
            mail.close()
            mail.logout()
            logger.info("[MAIL] Connection closed successfully")
        except socket.timeout:
            logger.warning(f"[MAIL] Timeout while closing connection after {timeout}s - returning already fetched emails")
        except Exception as close_error:
            logger.warning(f"[MAIL] Error while closing connection: {close_error}")

        return email_list

    except socket.timeout:
        error_msg = f"IMAP operation timeout after {timeout}s - Check network connection and IMAP server responsiveness"
        logger.error(f"[MAIL] {error_msg}")
        try:
            mail.close()
            mail.logout()
        except:
            pass
        return {"error": GENERIC_TIMEOUT_ERROR}
    except Exception as e:
        logger.error(f"[MAIL] Error fetching mail: {str(e)}")
        try:
            mail.close()
            mail.logout()
        except:
            pass
        return {"error": GENERIC_FETCH_ERROR}
