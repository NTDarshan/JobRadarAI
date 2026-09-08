from __future__ import annotations

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils.logging import get_logger

logger = get_logger(__name__)


def send_job_digest_email(
    html_body: str,
    host: str,
    port: int,
    username: str,
    password: str,
    from_address: str,
    to_address: str,
    send_date: date | None = None,
) -> None:
    """Send the job digest over SMTP with STARTTLS. Raises on failure so the caller can exit non-zero."""
    subject = f"JobRadar AI — Daily Job Matches — {(send_date or date.today()).isoformat()}"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(from_address, [to_address], message.as_string())
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send job digest email: %s", exc)
        raise
