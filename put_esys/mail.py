import email
import imaplib
import os
import smtplib
from email import encoders
from email.header import decode_header
from email.mime.base import MIMEBase
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

    def list_emails(
        self, folder="INBOX", limit=10, search_query: Optional[str] = None
    ) -> List[Dict]:
        mail = self._connect_imap()
        try:
            mail.select(folder)

            if search_query:
                # IMAP expects literal string for search
                status, messages = mail.search(None, "TEXT", f'"{search_query}"')
            else:
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

                        email_list.append(
                            {
                                "id": mail_id.decode(),
                                "subject": str(subject),
                                "from": str(from_),
                                "date": msg.get("Date"),
                            }
                        )
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
                    attachments = []
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            is_attach = "attachment" in content_disposition or (
                                "inline" in content_disposition and part.get_filename()
                            )

                            if is_attach:
                                filename = part.get_filename()
                                if filename:
                                    decoded_filename = decode_header(filename)[0]
                                    fname = decoded_filename[0]
                                    if isinstance(fname, bytes):
                                        encoding = decoded_filename[1] or "utf-8"
                                        try:
                                            fname = fname.decode(encoding, errors="replace")
                                        except LookupError:
                                            fname = fname.decode("utf-8", errors="replace")
                                    attachments.append(str(fname))
                                continue

                            is_plain = content_type == "text/plain"
                            if is_plain and not body:
                                try:
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or "utf-8"
                                    body = payload.decode(charset, errors="replace")
                                except Exception:
                                    body = "[Could not decode body]"
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
                        "body": body,
                        "attachments": attachments,
                    }
            return None
        finally:
            mail.logout()

    def download_attachment(self, mail_id, filename, output_path, folder="INBOX") -> bool:
        mail = self._connect_imap()
        try:
            mail.select(folder)
            status, msg_data = mail.fetch(str(mail_id), "(RFC822)")
            if status != "OK":
                return False

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    if not msg.is_multipart():
                        return False

                    for part in msg.walk():
                        content_disposition = str(part.get("Content-Disposition"))
                        is_attach = "attachment" in content_disposition or (
                            "inline" in content_disposition and part.get_filename()
                        )

                        if is_attach:
                            part_filename = part.get_filename()
                            if part_filename:
                                decoded_filename = decode_header(part_filename)[0]
                                fname = decoded_filename[0]
                                if isinstance(fname, bytes):
                                    encoding = decoded_filename[1] or "utf-8"
                                    try:
                                        fname = fname.decode(encoding, errors="replace")
                                    except LookupError:
                                        fname = fname.decode("utf-8", errors="replace")

                                if str(fname) == filename:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        with open(output_path, "wb") as f:
                                            f.write(payload)
                                        return True
            return False
        finally:
            mail.logout()

    def send_email(self, to_address, subject, body, attachment_paths: Optional[List[str]] = None):
        msg = MIMEMultipart()
        msg["From"] = self.username
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if attachment_paths:
            for filepath in attachment_paths:
                if not os.path.isfile(filepath):
                    continue
                filename = os.path.basename(filepath)
                with open(filepath, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
                msg.attach(part)

        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.username, self.password)
            server.send_message(msg)
