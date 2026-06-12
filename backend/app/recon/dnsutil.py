"""Pure-Python DNS resolution using dnspython.

Acts as a dependency-free fallback for resolution and record enumeration when
the `dnsx` binary is not installed, so DNS data is always populated.
"""
from __future__ import annotations

import dns.resolver

RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "NS", "TXT"]

_resolver = dns.resolver.Resolver()
_resolver.timeout = 4.0
_resolver.lifetime = 6.0


def resolve_host(host: str) -> dict:
    """Return {a, aaaa, cname, records:[(type,value,ttl)], live:bool}."""
    result = {"a": [], "aaaa": [], "cname": None, "records": []}
    for rtype in RECORD_TYPES:
        try:
            answers = _resolver.resolve(host, rtype)
            ttl = answers.rrset.ttl if answers.rrset else None
            for rdata in answers:
                value = rdata.to_text().rstrip(".")
                result["records"].append((rtype, value, ttl))
                if rtype == "A":
                    result["a"].append(value)
                elif rtype == "AAAA":
                    result["aaaa"].append(value)
                elif rtype == "CNAME":
                    result["cname"] = value
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers, dns.exception.Timeout):
            continue
        except Exception:
            continue
    result["resolvable"] = bool(result["a"] or result["aaaa"] or result["cname"])
    return result


def subdomain_level(host: str, root: str) -> int:
    """Depth of a subdomain relative to the root (example.com -> 2)."""
    return host.count(".") + 1
