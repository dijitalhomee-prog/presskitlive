"""
PressKitLive — Transactional Email Service (email_service.py)
Abstracted Resend API integration with safe fallback when API key is missing.
"""

import os
import json
import urllib.request
import urllib.error

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = "PressKitLive <bildirim@presskitlive.com>"

def send_email(to_email, subject, html_body):
    """
    Sends transactional HTML email via Resend API.
    If RESEND_API_KEY is not configured, logs a warning and returns status='skipped'
    without interrupting or failing the calling logic.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print(f"[UYARI] RESEND_API_KEY tanımlı değil — e-posta gönderilemedi: '{subject}' -> {to_email}")
        return {"status": "skipped", "message": "RESEND_API_KEY missing"}

    payload = json.dumps({
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_body
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as res:
            res_body = json.loads(res.read().decode('utf-8'))
            print(f"✉️ E-posta başarıyla gönderildi: '{subject}' -> {to_email}")
            return {"status": "success", "response": res_body}
    except Exception as e:
        print(f"[HATA] E-posta gönderilirken hata oluştu ({to_email}): {e}")
        return {"status": "error", "message": str(e)}
