"""Outbound notifications: Discord, Slack, Telegram, and Email.

Each channel is best-effort and no-ops if its credentials are not configured.
Use `notify` for high-signal events (new live hosts, open ports, takeovers).
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import httpx

from app.config import settings

_SEV_COLORS = {"info": 0x3B82F6, "warn": 0xF59E0B, "high": 0xEF4444, "critical": 0xDC2626}


def _post(url: str, payload: dict) -> None:
    try:
        httpx.post(url, json=payload, timeout=10)
    except Exception:
        pass


def notify_discord(title: str, body: str, severity: str = "info") -> None:
    if not settings.DISCORD_WEBHOOK_URL:
        return
    _post(settings.DISCORD_WEBHOOK_URL, {
        "embeds": [{"title": f"[SUBRECO] {title}", "description": body,
                    "color": _SEV_COLORS.get(severity, 0x3B82F6)}]
    })


def notify_slack(title: str, body: str, severity: str = "info") -> None:
    if not settings.SLACK_WEBHOOK_URL:
        return
    _post(settings.SLACK_WEBHOOK_URL, {"text": f"*[SUBRECO] {title}*\n{body}"})


def notify_telegram(title: str, body: str, severity: str = "info") -> None:
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    _post(url, {"chat_id": settings.TELEGRAM_CHAT_ID,
                "text": f"*[SUBRECO] {title}*\n{body}", "parse_mode": "Markdown"})


def notify_email(title: str, body: str, severity: str = "info") -> None:
    if not (settings.SMTP_HOST and settings.SMTP_TO):
        return
    msg = MIMEText(body)
    msg["Subject"] = f"[SUBRECO] {title}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = settings.SMTP_TO
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        pass


def notify(title: str, body: str, severity: str = "info") -> None:
    notify_discord(title, body, severity)
    notify_slack(title, body, severity)
    notify_telegram(title, body, severity)
    notify_email(title, body, severity)
