import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import logging
import socket
import models
import config as app_config

logger = logging.getLogger(__name__)

def fetch_recent_emails(config: models.EmailAccount, sender_filter: str = None, limit: int = 5, timeout: int = None):
    # Use configured timeout if not specified
    if timeout is None:
        timeout = app_config.IMAP_TIMEOUT

    target_sender = sender_filter if sender_filter else config.default_sender_filter
    logger.info(f"[MAIL] fetch_recent_emails started - email: {config.email}, sender_filter: {target_sender}, timeout: {timeout}s")

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
        return {"error": f"IMAP connection/login timeout after {timeout}s"}
    except Exception as e:
        logger.error(f"[MAIL] Connection/Login failed: {str(e)}")
        return {"error": f"Connection failed: {str(e)}"}

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

        email_list = []

        for idx, e_id in enumerate(recent_email_ids):
            logger.info(f"[MAIL] Fetching email {idx + 1}/{len(recent_email_ids)} (id: {e_id})")
            try:
                status, msg_data = mail.fetch(e_id, "(RFC822)")
            except socket.timeout:
                logger.error(f"[MAIL] Timeout while fetching email {idx + 1}/{len(recent_email_ids)} (id: {e_id}) after {timeout}s")
                raise
            
            email_content = {"subject": "Unknown", "body": "", "from": "", "date": ""}

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    email_content["subject"] = subject
                    email_content["from"] = msg.get("From")
                    
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

                    email_content["date"] = formatted_date

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    decoded_payload = payload.decode()
                                else:
                                    continue
                            except:
                                continue

                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body += decoded_payload
                            elif content_type == "text/html" and "attachment" not in content_disposition:
                                soup = BeautifulSoup(decoded_payload, "html.parser")
                                body += soup.get_text()
                    else:
                        content_type = msg.get_content_type()
                        payload = msg.get_payload(decode=True)
                        if payload:
                            decoded_payload = payload.decode()
                            if content_type == "text/html":
                                soup = BeautifulSoup(decoded_payload, "html.parser")
                                body = soup.get_text()
                            else:
                                body = decoded_payload
                    
                    email_content["body"] = body.strip()
            
            email_list.append(email_content)

        logger.info(f"[MAIL] Closing connection, total emails fetched: {len(email_list)}")
        mail.close()
        mail.logout()
        logger.info("[MAIL] Connection closed successfully")
        return email_list

    except socket.timeout:
        error_msg = f"IMAP operation timeout after {timeout}s - Check network connection and IMAP server responsiveness"
        logger.error(f"[MAIL] {error_msg}")
        try:
            mail.close()
            mail.logout()
        except:
            pass
        return {"error": error_msg}
    except Exception as e:
        logger.error(f"[MAIL] Error fetching mail: {str(e)}")
        try:
            mail.close()
            mail.logout()
        except:
            pass
        return {"error": f"Error fetching mail: {str(e)}"}
