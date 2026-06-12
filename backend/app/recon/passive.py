"""Passive subdomain enumeration via public HTTP APIs.

These sources require **no external binaries** — only outbound HTTPS — so the
platform always produces real results even in a minimal install. Optional API
keys (SecurityTrails, Chaos, OTX) unlock additional sources when present.
"""
from __future__ import annotations

import json
import re

import httpx

from app.config import settings

_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?\.)+[a-zA-Z]{2,}$")


def _clean(host: str, root: str) -> str | None:
    host = host.strip().lower().lstrip("*.")
    if not host or host == root:
        return host if host == root else None
    if not host.endswith("." + root):
        return None
    if not _DOMAIN_RE.match(host):
        return None
    return host


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=settings.RECON_HTTP_TIMEOUT,
        headers={"User-Agent": "subreco/1.0 (+asm)"},
        follow_redirects=True,
    )


def from_crtsh(domain: str) -> set[str]:
    out: set[str] = set()
    try:
        with _client() as c:
            r = c.get("https://crt.sh/", params={"q": f"%.{domain}", "output": "json"})
            if r.status_code == 200 and r.text.strip():
                for row in r.json():
                    for name in str(row.get("name_value", "")).splitlines():
                        if (h := _clean(name, domain)):
                            out.add(h)
    except Exception:
        pass
    return out


def from_otx(domain: str) -> set[str]:
    out: set[str] = set()
    url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
    headers = {"X-OTX-API-KEY": settings.OTX_API_KEY} if settings.OTX_API_KEY else {}
    try:
        with _client() as c:
            r = c.get(url, headers=headers)
            if r.status_code == 200:
                for rec in r.json().get("passive_dns", []):
                    if (h := _clean(rec.get("hostname", ""), domain)):
                        out.add(h)
    except Exception:
        pass
    return out


def from_rapiddns(domain: str) -> set[str]:
    out: set[str] = set()
    try:
        with _client() as c:
            r = c.get(f"https://rapiddns.io/subdomain/{domain}", params={"full": "1"})
            if r.status_code == 200:
                for m in re.findall(r"<td>([\w.-]+\." + re.escape(domain) + r")</td>", r.text):
                    if (h := _clean(m, domain)):
                        out.add(h)
    except Exception:
        pass
    return out


def from_bufferover(domain: str) -> set[str]:
    out: set[str] = set()
    try:
        with _client() as c:
            r = c.get(f"https://dns.bufferover.run/dns?q=.{domain}")
            if r.status_code == 200:
                data = r.json()
                for key in ("FDNS_A", "RDNS"):
                    for entry in data.get(key) or []:
                        host = entry.split(",")[-1] if "," in entry else entry
                        if (h := _clean(host, domain)):
                            out.add(h)
    except Exception:
        pass
    return out


def from_securitytrails(domain: str) -> set[str]:
    out: set[str] = set()
    if not settings.SECURITYTRAILS_API_KEY:
        return out
    try:
        with _client() as c:
            r = c.get(
                f"https://api.securitytrails.com/v1/domain/{domain}/subdomains",
                headers={"APIKEY": settings.SECURITYTRAILS_API_KEY},
                params={"children_only": "false"},
            )
            if r.status_code == 200:
                for sub in r.json().get("subdomains", []):
                    if (h := _clean(f"{sub}.{domain}", domain)):
                        out.add(h)
    except Exception:
        pass
    return out


PASSIVE_SOURCES = {
    "crtsh": from_crtsh,
    "otx": from_otx,
    "rapiddns": from_rapiddns,
    "bufferover": from_bufferover,
    "securitytrails": from_securitytrails,
}


def collect_passive(domain: str) -> dict[str, set[str]]:
    """Run every passive source; return {source_name: {hosts}}."""
    results: dict[str, set[str]] = {}
    for name, fn in PASSIVE_SOURCES.items():
        try:
            results[name] = fn(domain)
        except Exception:
            results[name] = set()
    return results
