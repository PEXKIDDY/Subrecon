"""Wayback URL triage + JavaScript secret/endpoint intelligence.

`categorize_url` mirrors common `gf` patterns (admin/login/api/backup) for fast
triage. `scan_js_for_secrets` applies trufflehog-style regexes to JS bodies to
surface exposed keys for responsible disclosure / remediation.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import settings

ADMIN_RE = re.compile(r"/(admin|administrator|wp-admin|dashboard|manage|console)\b", re.I)
LOGIN_RE = re.compile(r"/(login|signin|sign-in|auth|sso|oauth)\b", re.I)
API_RE = re.compile(r"/(api|v\d+|graphql|rest|swagger|openapi)\b", re.I)
BACKUP_RE = re.compile(r"\.(bak|old|backup|sql|zip|tar|gz|rar|7z|env|config|conf|log)(\?|$)", re.I)

# trufflehog-style high-signal secret patterns
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,48}")),
    ("github_token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}")),
    ("stripe_key", re.compile(r"sk_live_[0-9A-Za-z]{24,}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("generic_api_key", re.compile(r"(?i)(?:api[_-]?key|secret|token)['\"]?\s*[:=]\s*['\"][0-9a-zA-Z\-_]{16,}['\"]")),
]

ENDPOINT_RE = re.compile(r"""["'`](/[a-zA-Z0-9_\-/{}.]+?(?:/[a-zA-Z0-9_\-/{}.]+)*)["'`]""")


def categorize_url(url: str) -> str:
    if BACKUP_RE.search(url):
        return "backup"
    if ADMIN_RE.search(url):
        return "admin"
    if LOGIN_RE.search(url):
        return "login"
    if API_RE.search(url):
        return "api"
    return "other"


def extract_params(url: str) -> list[str]:
    try:
        return sorted(parse_qs(urlparse(url).query).keys())
    except Exception:
        return []


def scan_js_for_secrets(js_url: str) -> dict:
    """Fetch a JS file and extract secrets + referenced endpoints."""
    findings = {"secrets": [], "endpoints": []}
    try:
        with httpx.Client(timeout=settings.RECON_HTTP_TIMEOUT,
                          headers={"User-Agent": "subreco/1.0"}) as c:
            r = c.get(js_url)
            if r.status_code != 200:
                return findings
            body = r.text[:500_000]  # cap to 500KB
    except Exception:
        return findings

    for name, pat in SECRET_PATTERNS:
        for m in set(pat.findall(body)):
            match = m if isinstance(m, str) else (m[0] if m else "")
            if match:
                findings["secrets"].append({"type": name, "match": match[:120]})

    for m in set(ENDPOINT_RE.findall(body)):
        if len(m) > 3 and any(seg in m.lower() for seg in ("/api", "/v1", "/v2", "/graphql", "/rest")):
            findings["endpoints"].append(m)
    return findings
