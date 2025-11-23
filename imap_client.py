import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import getpass
import socket
import config

def clean_text(text):
    return "".join(text.split())

def get_email_content(username, password, imap_server, sender_email, timeout=None):
    # Use configured timeout if not specified
    if timeout is None:
        timeout = config.IMAP_TIMEOUT

    # Connect to the server
    try:
        print(f"Connecting to {imap_server} (timeout: {timeout}s)...")
        mail = imaplib.IMAP4_SSL(imap_server, timeout=timeout)

        # Set socket timeout for all subsequent operations
        if hasattr(mail, 'sock') and mail.sock:
            mail.sock.settimeout(timeout)

        mail.login(username, password)
        print("Login successful")
    except socket.timeout:
        print(f"IMAP connection/login timeout after {timeout}s - Failed to connect or authenticate to {imap_server}")
        return
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        mail.select("inbox")

        # Search for emails from the specific sender
        # IMAP search criteria: FROM "sender@example.com"
        status, messages = mail.search(None, f'(FROM "{sender_email}")')

        if status != "OK":
            print("No emails found.")
            return

        email_ids = messages[0].split()

        if not email_ids:
            print(f"No emails found from {sender_email}")
            return

        # Get the latest email
        latest_email_id = email_ids[-1]

        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Decode subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")

                print(f"Subject: {subject}")
                print(f"From: {msg.get('From')}")
                print("-" * 50)

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
                            # Prefer HTML if available, or append it
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

                print("Body Content:")
                print(body.strip())

        mail.close()
        mail.logout()
    except socket.timeout:
        print(f"IMAP operation timeout after {timeout}s - Timeout occurred while selecting inbox, searching or fetching emails")
        try:
            mail.close()
            mail.logout()
        except:
            pass
    except Exception as e:
        print(f"Error fetching emails: {e}")
        try:
            mail.close()
            mail.logout()
        except:
            pass

def get_imap_server(email_address):
    domain = email_address.split("@")[-1].lower()
    if domain == "gmail.com":
        return "imap.gmail.com"
    elif domain in ["outlook.com", "hotmail.com", "live.com"]:
        return "outlook.office365.com"
    return None

if __name__ == "__main__":
    print("IMAP Email Fetcher")
    print("------------------")
    
    user = input("Email Address: ").strip()
    
    # Auto-detect server
    detected_server = get_imap_server(user)
    default_server = detected_server if detected_server else "outlook.office365.com"
    
    server = input(f"IMAP Server [{default_server}]: ").strip() or default_server
    
    pwd = getpass.getpass("Password: ").strip()
    sender = input("Target Sender Email: ").strip()
    
    if user and pwd and sender:
        get_email_content(user, pwd, server, sender)
    else:
        print("Missing required information.")
