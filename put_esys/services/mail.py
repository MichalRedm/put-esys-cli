import email
import email.utils
import imaplib
import os
import re
import smtplib
import time
from email import encoders
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from put_esys.models.mail import EmailDetails, EmailSummary


def decode_mime_header(raw_header: Optional[str]) -> str:
    """
    Decodes RFC 2047 MIME encoded headers into a unified string.
    Handles multi-chunk headers, default charsets, and lookup fallbacks.
    """
    if not raw_header:
        return ""

    decoded_chunks = decode_header(raw_header)
    parts = []
    for chunk, encoding in decoded_chunks:
        if isinstance(chunk, bytes):
            enc = encoding or "utf-8"
            try:
                parts.append(chunk.decode(enc))
            except (LookupError, UnicodeDecodeError):
                parts.append(chunk.decode("utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    return "".join(parts)


class MailClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.imap_server = "poczta.student.put.poznan.pl"
        self.imap_port = 993
        self.smtp_server = "poczta.student.put.poznan.pl"
        self.smtp_port = 465  # SSL

    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        return mail

    def list_folders(self) -> List[str]:
        mail = self._connect_imap()
        try:
            status, folder_list = mail.list()
            if status != "OK":
                return []

            folders = []
            for folder_bytes in folder_list:
                line = folder_bytes.decode("utf-8", errors="replace")
                match = re.search(
                    r"\((?P<flags>[^)]*)\)\s+(?P<delim>\"[^\"]+\"|[^\s]+)\s+(?P<name>.*)",
                    line,
                )
                if match:
                    name = match.group("name").strip()
                    if name.startswith('"') and name.endswith('"'):
                        name = name[1:-1]
                    folders.append(name)
                else:
                    folders.append(line)
            return folders
        finally:
            mail.logout()

    def list_emails(
        self, folder="INBOX", limit=10, search_query: Optional[str] = None
    ) -> List[EmailSummary]:
        mail = self._connect_imap()
        try:
            mail.select(folder)

            if search_query:
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
                # Optimized header-only fetch avoiding heavy full-body and attachment downloads
                status, msg_data = mail.fetch(
                    mail_id, "(BODY.PEEK[HEADER.FIELDS (Subject From To Date)])"
                )
                if status != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = decode_mime_header(msg.get("Subject", ""))
                        from_ = decode_mime_header(msg.get("From", ""))
                        to_header = msg.get("To")
                        to = decode_mime_header(to_header) if to_header else None

                        email_list.append(
                            EmailSummary(
                                id=mail_id.decode(),
                                subject=subject,
                                from_=from_,
                                to=to,
                                date=msg.get("Date"),
                            )
                        )
            return email_list
        finally:
            mail.logout()

    def get_email_details(self, mail_id, folder="INBOX") -> Optional[EmailDetails]:
        mail = self._connect_imap()
        try:
            mail.select(folder)
            status, msg_data = mail.fetch(str(mail_id), "(RFC822)")
            if status != "OK":
                return None

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_mime_header(msg.get("Subject", ""))
                    from_ = decode_mime_header(msg.get("From", ""))
                    to_header = msg.get("To")
                    to = decode_mime_header(to_header) if to_header else None

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
                                    fname = decode_mime_header(filename)
                                    attachments.append(fname)
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

                    return EmailDetails(
                        id=str(mail_id),
                        subject=subject,
                        from_=from_,
                        to=to,
                        date=msg.get("Date"),
                        body=body,
                        attachments=attachments,
                    )
            return None
        finally:
            mail.logout()

    def download_attachment(
        self, mail_id, filename, output_path, folder="INBOX", index: Optional[int] = None
    ) -> bool:
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

                    match_count = 0
                    for part in msg.walk():
                        content_disposition = str(part.get("Content-Disposition"))
                        is_attach = "attachment" in content_disposition or (
                            "inline" in content_disposition and part.get_filename()
                        )

                        if is_attach:
                            part_filename = part.get_filename()
                            if part_filename:
                                fname = decode_mime_header(part_filename)

                                if fname == filename:
                                    match_count += 1
                                    if index is not None:
                                        if match_count == index:
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                with open(output_path, "wb") as f:
                                                    f.write(payload)
                                                return True
                                    else:
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            with open(output_path, "wb") as f:
                                                f.write(payload)
                                            return True
            return False
        finally:
            mail.logout()

    def send_email(
        self, to_address, subject, body, attachment_paths: Optional[List[str]] = None
    ) -> None:
        if attachment_paths:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body, "plain", "utf-8"))
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
        else:
            msg = MIMEText(body, "plain", "utf-8")

        msg["From"] = self.username
        msg["To"] = to_address
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)

        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.username, self.password)
            server.send_message(msg)

        try:
            mail = self._connect_imap()
            try:
                internal_date = imaplib.Time2Internaldate(time.time())
                mail.append("Sent", None, internal_date, msg.as_bytes())
            finally:
                mail.logout()
        except Exception:
            pass
