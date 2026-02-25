from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .export_service import export_bytes


def send_report_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_sender: str,
    use_tls: bool,
    recipient_email: str,
    attachment_name: str,
    attachment_rows,
):
    pdf_bytes, _, extension = export_bytes(attachment_rows, "pdf")

    msg = EmailMessage()
    msg["Subject"] = "SecurePay AI Audit Report"
    msg["From"] = smtp_sender or smtp_user
    msg["To"] = recipient_email
    msg.set_content("Attached is your requested audit report.")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=f"{attachment_name}.{extension}")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as client:
        if use_tls:
            client.starttls()
        if smtp_user:
            client.login(smtp_user, smtp_password)
        client.send_message(msg)
