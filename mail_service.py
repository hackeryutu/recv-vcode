import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import models

def fetch_recent_emails(config: models.EmailAccount, sender_filter: str = None, limit: int = 5):
    target_sender = sender_filter if sender_filter else config.default_sender_filter
    
    if not target_sender:
        return {"error": "No sender filter specified"}

    try:
        mail = imaplib.IMAP4_SSL(config.imap_server)
        mail.login(config.email, config.password)
    except Exception as e:
        return {"error": f"Connection failed: {str(e)}"}

    try:
        mail.select("inbox")
        
        # Search for emails from the specific sender
        status, messages = mail.search(None, f'(FROM "{target_sender}")')
        
        if status != "OK":
            return {"message": "No emails found"}

        email_ids = messages[0].split()
        
        if not email_ids:
            return {"message": f"No emails found from {target_sender}"}

        # Get the last N emails
        recent_email_ids = email_ids[-limit:]
        recent_email_ids.reverse() # Newest first
        
        email_list = []

        for e_id in recent_email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            
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
                            formatted_date = parsed_date.strftime("%Y/%m/%d %H:%M:%S")
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

        mail.close()
        mail.logout()
        return email_list

    except Exception as e:
        return {"error": f"Error fetching mail: {str(e)}"}

    except Exception as e:
        return {"error": f"Error fetching mail: {str(e)}"}
