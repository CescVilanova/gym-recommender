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
import subprocess
import tempfile


RESEND_API_URL = 'https://api.resend.com/emails'


def send(to_email: str, subject: str, body_path: str, pdf_path: str):
    api_key   = os.environ.get('RESEND_API_KEY')
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

    # Write payload to a temp file so the API key never appears in the process list
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                'curl', '--silent', '--show-error', '--fail-with-body',
                '-X', 'POST', RESEND_API_URL,
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', f'@{tmp_path}',
            ],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(tmp_path)

    if result.returncode != 0:
        print(f"ERROR: {result.stdout or result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    print(f"✓ Email sent to {to_email} (id: {data.get('id', '?')})")


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 send_email.py <to_email> <subject> <body_path> <pdf_path>",
              file=sys.stderr)
        sys.exit(1)
    send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
