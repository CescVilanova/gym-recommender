#!/usr/bin/env python3
"""
ProGym Email Sender

Sends a quote email via Gmail SMTP with a PDF attachment.
Requires GMAIL_USER and GMAIL_APP_PASSWORD env vars.

Usage:
    python3 send_email.py <to_email> <subject> <body_html_path> <pdf_path>

The body argument is a PATH to an HTML or text file (avoids shell-escaping issues).
"""

import sys
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465


def send(to_email: str, subject: str, body_path: str, pdf_path: str):
    user     = os.environ.get('GMAIL_USER')
    password = os.environ.get('GMAIL_APP_PASSWORD')

    if not user or not password:
        print("ERROR: GMAIL_USER and GMAIL_APP_PASSWORD env vars are required.",
              file=sys.stderr)
        sys.exit(1)

    # Read body content
    with open(body_path, 'r', encoding='utf-8') as f:
        body = f.read()

    # Build message
    msg = MIMEMultipart()
    msg['From']    = f"ProGym <{user}>"
    msg['To']      = to_email
    msg['Subject'] = subject

    # Detect HTML vs plain text by file extension
    body_type = 'html' if body_path.lower().endswith('.html') else 'plain'
    msg.attach(MIMEText(body, body_type, 'utf-8'))

    # Attach PDF if provided and exists
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'pdf')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{os.path.basename(pdf_path)}"'
        )
        msg.attach(part)
    elif pdf_path:
        print(f"WARNING: PDF not found at {pdf_path}, sending without attachment.",
              file=sys.stderr)

    # Send
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(user, password)
        server.send_message(msg)

    print(f"✓ Email sent to {to_email}")


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 send_email.py <to_email> <subject> <body_path> <pdf_path>",
              file=sys.stderr)
        sys.exit(1)
    send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
