#!/usr/bin/env python3
"""
ProGym Email Sender

Sends a quote email with an optional PDF attachment.
Prefers Resend API (RESEND_API_KEY + RESEND_FROM) when available;
falls back to Gmail SMTP (GMAIL_USER + GMAIL_APP_PASSWORD).

Usage:
    python3 send_email.py <to_email> <subject> <body_html_path> <pdf_path>

Pass an empty string for pdf_path to send without attachment.
"""

import sys
import os
import json
import base64
import subprocess
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def _send_resend(to_email: str, subject: str, body_path: str, pdf_path: str):
    api_key  = os.environ['RESEND_API_KEY']
    from_addr = os.environ.get('RESEND_FROM', 'ProGym <hola@gymreco.agentstudio.io>')

    with open(body_path, 'r', encoding='utf-8') as f:
        body_html = f.read()

    payload = {
        'from':    from_addr,
        'to':      [to_email],
        'subject': subject,
        'html':    body_html,
    }

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            pdf_b64 = base64.b64encode(f.read()).decode()
        payload['attachments'] = [{
            'filename': os.path.basename(pdf_path),
            'content':  pdf_b64,
        }]
    elif pdf_path:
        print(f"WARNING: PDF not found at {pdf_path}, sending without attachment.",
              file=sys.stderr)

    # Write payload to a temp file — avoids shell-escaping and Cloudflare UA issues
    payload_path = '/tmp/_resend_payload.json'
    with open(payload_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f)

    result = subprocess.run(
        [
            'curl', '-s', '-w', '\n%{http_code}',
            '-X', 'POST', 'https://api.resend.com/emails',
            '-H', f'Authorization: Bearer {api_key}',
            '-H', 'Content-Type: application/json',
            '-d', f'@{payload_path}',
        ],
        capture_output=True, text=True,
    )

    lines = result.stdout.strip().rsplit('\n', 1)
    body_out = lines[0] if len(lines) == 2 else ''
    status   = int(lines[-1]) if lines[-1].isdigit() else 0

    if status in (200, 201):
        print(f"✓ Email sent to {to_email} via Resend")
    else:
        print(f"ERROR: Resend returned {status}: {body_out}", file=sys.stderr)
        sys.exit(1)


def _send_smtp(to_email: str, subject: str, body_path: str, pdf_path: str):
    user     = os.environ.get('GMAIL_USER')
    password = os.environ.get('GMAIL_APP_PASSWORD')

    if not user or not password:
        print("ERROR: GMAIL_USER and GMAIL_APP_PASSWORD env vars are required.",
              file=sys.stderr)
        sys.exit(1)

    with open(body_path, 'r', encoding='utf-8') as f:
        body = f.read()

    msg = MIMEMultipart()
    msg['From']    = f"ProGym <{user}>"
    msg['To']      = to_email
    msg['Subject'] = subject

    body_type = 'html' if body_path.lower().endswith('.html') else 'plain'
    msg.attach(MIMEText(body, body_type, 'utf-8'))

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

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(user, password)
        server.send_message(msg)

    print(f"✓ Email sent to {to_email} via Gmail SMTP")


def send(to_email: str, subject: str, body_path: str, pdf_path: str):
    if os.environ.get('RESEND_API_KEY'):
        _send_resend(to_email, subject, body_path, pdf_path)
    else:
        _send_smtp(to_email, subject, body_path, pdf_path)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 send_email.py <to_email> <subject> <body_path> <pdf_path>",
              file=sys.stderr)
        sys.exit(1)
    send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
