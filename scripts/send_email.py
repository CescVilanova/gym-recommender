#!/usr/bin/env python3
"""
ProGym Email Sender

Sends a quote email via Resend HTTP API with a PDF attachment.
Requires RESEND_API_KEY and RESEND_FROM env vars.

Usage:
    python3 send_email.py <to_email> <subject> <body_html_path> <pdf_path>

pdf_path may be an empty string to send without attachment.
"""

import sys
import os
import json
import base64
import urllib.request
import urllib.error


RESEND_API_URL = 'https://api.resend.com/emails'


def send(to_email: str, subject: str, body_path: str, pdf_path: str):
    api_key  = os.environ.get('RESEND_API_KEY')
    from_addr = os.environ.get('RESEND_FROM', 'ProGym <noreply@progym.es>')

    if not api_key:
        print("ERROR: RESEND_API_KEY env var is required.", file=sys.stderr)
        sys.exit(1)

    with open(body_path, 'r', encoding='utf-8') as f:
        body = f.read()

    payload = {
        'from':    from_addr,
        'to':      [to_email],
        'subject': subject,
        'html':    body,
    }

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('ascii')
        payload['attachments'] = [{
            'filename': os.path.basename(pdf_path),
            'content':  encoded,
        }]
    elif pdf_path:
        print(f"WARNING: PDF not found at {pdf_path}, sending without attachment.",
              file=sys.stderr)

    data = json.dumps(payload).encode('utf-8')
    req  = urllib.request.Request(
        RESEND_API_URL,
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        print(f"✓ Email sent to {to_email} (id: {result.get('id', '?')})")
    except urllib.error.HTTPError as e:
        body_err = e.read().decode('utf-8', errors='replace')
        print(f"ERROR {e.code}: {body_err}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 send_email.py <to_email> <subject> <body_path> <pdf_path>",
              file=sys.stderr)
        sys.exit(1)
    send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
