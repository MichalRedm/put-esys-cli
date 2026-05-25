import email
import imaplib
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional


class MailClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.imap_server = "poczta.student.put.poznan.pl"
        self.imap_port = 993
        self.smtp_server = "poczta.student.put.poznan.pl"
        self.smtp_port = 465  # SSL

    def _connect_imap(self):
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        return mail

    def list_emails(self, folder="INBOX", limit=10) -> List[Dict]:
        mail = self._connect_imap()
        try:
            mail.select(folder)
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                return []

            mail_ids = messages[0].split()
            latest_ids = mail_ids[-limit:]
            latest_ids.reverse()

            email_list = []
            for mail_id in latest_ids:
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                if status != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject_raw = decode_header(msg.get("Subject", ""))[0]
                        subject = subject_raw[0]
                        if isinstance(subject, bytes):
                            encoding = subject_raw[1] or "utf-8"
                            try:
                                subject = subject.decode(encoding)
                            except LookupError:
                                subject = subject.decode("utf-8", errors="replace")

                        from_raw = decode_header(msg.get("From", ""))[0]
                        from_ = from_raw[0]
                        if isinstance(from_, bytes):
                            encoding = from_raw[1] or "utf-8"
                            try:
                                from_ = from_.decode(encoding)
                            except LookupError:
                                from_ = from_.decode("utf-8", errors="replace")

                        email_list.append({
                            "id": mail_id.decode(),
                            "subject": str(subject),
                            "from": str(from_),
                            "date": msg.get("Date")
                        })
            return email_list
        finally:
            mail.logout()

    def get_email_details(self, mail_id, folder="INBOX") -> Optional[Dict]:
        mail = self._connect_imap()
        try:
            mail.select(folder)
            status, msg_data = mail.fetch(str(mail_id), "(RFC822)")
            if status != "OK":
                return None

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    subject_raw = decode_header(msg.get("Subject", ""))[0]
                    subject = subject_raw[0]
                    if isinstance(subject, bytes):
                        encoding = subject_raw[1] or "utf-8"
                        try:
                            subject = subject.decode(encoding)
                        except LookupError:
                            subject = subject.decode("utf-8", errors="replace")

                    from_raw = decode_header(msg.get("From", ""))[0]
                    from_ = from_raw[0]
                    if isinstance(from_, bytes):
                        encoding = from_raw[1] or "utf-8"
                        try:
                            from_ = from_.decode(encoding)
                        except LookupError:
                            from_ = from_.decode("utf-8", errors="replace")

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            is_plain = content_type == "text/plain"
                            is_attach = "attachment" in content_disposition
                            if is_plain and not is_attach:
                                try:
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or "utf-8"
                                    body = payload.decode(charset, errors="replace")
                                except Exception:
                                    body = "[Could not decode body]"
                                break
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            charset = msg.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="replace")
                        except Exception:
                            body = "[Could not decode body]"

                    return {
                        "id": str(mail_id),
                        "subject": str(subject),
                        "from": str(from_),
                        "date": msg.get("Date"),
                        "body": body
                    }
            return None
        finally:
            mail.logout()

    def send_email(self, to_address, subject, body):
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.username, self.password)
            server.send_message(msg)
