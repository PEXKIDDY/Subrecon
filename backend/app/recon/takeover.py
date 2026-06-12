"""Subdomain takeover detection.

Flags *potential* dangling-CNAME takeovers by matching the CNAME target and
HTTP body fingerprint against known service signatures. This is detection only
— it never attempts to claim or exploit a resource. Useful for both bug-bounty
triage and defensive remediation of your own dangling records.
"""
from __future__ import annotations

import httpx

from app.config import settings

# (service, [cname substrings], [body fingerprint strings], default risk)
FINGERPRINTS: list[tuple[str, list[str], list[str], str]] = [
    ("AWS S3", ["s3.amazonaws.com", "s3-website", ".s3."],
     ["NoSuchBucket", "The specified bucket does not exist"], "high"),
    ("GitHub Pages", ["github.io", "github.map.fastly.net"],
     ["There isn't a GitHub Pages site here", "404"], "medium"),
    ("Heroku", ["herokuapp.com", "herokussl.com"],
     ["No such app", "herokucdn.com/error-pages/no-such-app.html"], "high"),
    ("Shopify", ["myshopify.com"],
     ["Sorry, this shop is currently unavailable"], "medium"),
    ("Azure", ["azurewebsites.net", "cloudapp.net", "trafficmanager.net", "blob.core.windows.net"],
     ["404 Web Site not found", "The resource you are looking for has been removed"], "high"),
    ("Zendesk", ["zendesk.com"],
     ["Help Center Closed", "this help center no longer exists"], "medium"),
    ("Fastly", ["fastly.net"],
     ["Fastly error: unknown domain"], "medium"),
    ("CloudFront", ["cloudfront.net"],
     ["Bad request", "ERROR: The request could not be satisfied"], "medium"),
]


def detect_takeover(host: str, cname: str | None) -> dict | None:
    """Return takeover finding dict or None."""
    if not cname:
        return None
    cname_l = cname.lower()
    for service, cname_subs, body_sigs, risk in FINGERPRINTS:
        if not any(sub in cname_l for sub in cname_subs):
            continue
        # CNAME match alone = low confidence; fetch body to confirm fingerprint.
        confidence = "low"
        evidence = f"CNAME points to {service} ({cname})"
        try:
            with httpx.Client(timeout=settings.RECON_HTTP_TIMEOUT, follow_redirects=True,
                              headers={"User-Agent": "subreco/1.0"}) as c:
                for scheme in ("https", "http"):
                    try:
                        r = c.get(f"{scheme}://{host}")
                        body = r.text[:8000]
                        if any(sig.lower() in body.lower() for sig in body_sigs):
                            confidence = "high"
                            evidence = f"{service} fingerprint matched in HTTP body"
                            break
                    except Exception:
                        continue
        except Exception:
            pass
        return {
            "service": service,
            "cname": cname,
            "confidence": confidence,
            "risk_level": risk,
            "evidence": evidence,
        }
    return None
