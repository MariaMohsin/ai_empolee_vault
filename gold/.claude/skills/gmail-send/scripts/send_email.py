#!/usr/bin/env python3
"""
Gmail SMTP Email Sender - Production Implementation
Sends real emails using Gmail SMTP server
"""

import smtplib
import argparse
import os
import sys
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Auto-load .env from project root
def _load_env():
    for candidate in [
        Path(__file__).parent.parent.parent.parent.parent / ".env",  # silver/.env
        Path(__file__).parent / ".env",
    ]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
            break

_load_env()


def send_email(to, subject, body, cc=None, bcc=None):
    """
    Send email via Gmail SMTP

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        cc: CC recipients (comma-separated string)
        bcc: BCC recipients (comma-separated string)

    Returns:
        dict: {"success": bool, "message": str}
    """
    # Get credentials from environment
    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")

    if not email_address or not email_password:
        return {
            "success": False,
            "message": "Missing EMAIL_ADDRESS or EMAIL_PASSWORD environment variables"
        }

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = email_address
        msg["To"] = to
        msg["Subject"] = subject

        # Add CC/BCC if provided
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        # Attach body
        msg.attach(MIMEText(body, "plain"))

        # Build recipient list
        recipients = [to]
        if cc:
            recipients.extend([addr.strip() for addr in cc.split(",")])
        if bcc:
            recipients.extend([addr.strip() for addr in bcc.split(",")])

        # Connect to Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg, from_addr=email_address, to_addrs=recipients)

        return {
            "success": True,
            "message": f"Email sent successfully to {to}"
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Authentication failed. Check EMAIL_ADDRESS and EMAIL_PASSWORD. Use App Password for Gmail."
        }

    except smtplib.SMTPException as e:
        return {
            "success": False,
            "message": f"SMTP error: {str(e)}"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }


def main():
    parser = argparse.ArgumentParser(description="Send email via Gmail SMTP")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body text")
    parser.add_argument("--cc", help="CC recipients (comma-separated)")
    parser.add_argument("--bcc", help="BCC recipients (comma-separated)")

    args = parser.parse_args()

    # Send email
    result = send_email(
        to=args.to,
        subject=args.subject,
        body=args.body,
        cc=args.cc,
        bcc=args.bcc
    )

    # Print result
    print(result["message"])

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
