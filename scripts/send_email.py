#!/usr/bin/env python3
"""
ProGym Email Sender

Sends a quote email with a PDF attachment.
Prefers Resend API (RESEND_API_KEY + RESEND_FROM) over Gmail SMTP
(GMAIL_USER + GMAIL_APP_PASSWORD) — Resend works over HTTPS and requires
no outbound SMTP ports.

Usage:
    python3 send_email.py <to_email> <subject> <body_html_path> <pdf_path>
"""

import sys
import os
import base64
import json
import smtplib
import ssl
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def _send_resend(to_email, subject, body_path, pdf_path):
    api_key   = os.environ['RESEND_API_KEY']
    from_addr = os.environ['RESEND_FROM']

    with open(body_path, 'r', encoding='utf-8') as f:
        body = f.read()

    body_key = 'html' if body_path.lower().endswith('.html') else 'text'

    payload = {
        'from':    from_addr,
        'to':      [to_email],
        'subject': subject,
        body_key:  body,
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

    data = json.dumps(payload).encode('utf-8')
    req  = urllib.request.Request(
        'https://api.resend.com/emails',
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
            'User-Agent':    'progym-recommender/1.0',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode())
            print(f"✓ Email sent via Resend to {to_email} (id: {result.get('id', '?')})")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"ERROR: Resend API returned {e.code}: {err}", file=sys.stderr)
        sys.exit(1)


def _send_smtp(to_email, subject, body_path, pdf_path):
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

    print(f"✓ Email sent via Gmail SMTP to {to_email}")


def send(to_email, subject, body_path, pdf_path):
    if os.environ.get('RESEND_API_KEY') and os.environ.get('RESEND_FROM'):
        _send_resend(to_email, subject, body_path, pdf_path)
    else:
        _send_smtp(to_email, subject, body_path, pdf_path)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 send_email.py <to_email> <subject> <body_path> <pdf_path>",
              file=sys.stderr)
        sys.exit(1)
    send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
