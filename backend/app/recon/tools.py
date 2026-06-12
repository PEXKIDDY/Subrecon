"""Thin wrappers over the ProjectDiscovery + classic recon toolchain.

Each function returns parsed results and silently yields nothing when its
binary is missing (see runner.tool_available). Output formats target the
JSON-line (`-json`) modes where available for robust parsing.
"""
from __future__ import annotations

import json

from app.config import settings
from app.recon.runner import lines, run_tool, tool_available


# ---------------- Subdomain enumeration ----------------
def subfinder(domain: str) -> set[str]:
    res = run_tool("subfinder", ["-silent", "-d", domain])
    return set(lines(res.stdout)) if res.ok else set()


def assetfinder(domain: str) -> set[str]:
    res = run_tool("assetfinder", ["--subs-only", domain])
    return {h for h in lines(res.stdout) if h.endswith(domain)} if res.ok else set()


def amass(domain: str) -> set[str]:
    # passive mode keeps it fast and non-intrusive
    res = run_tool("amass", ["enum", "-passive", "-d", domain, "-silent"], timeout=settings.RECON_TOOL_TIMEOUT)
    return {h for h in lines(res.stdout) if h.endswith(domain)} if res.ok else set()


def chaos(domain: str) -> set[str]:
    if not settings.CHAOS_API_KEY:
        return set()
    res = run_tool("chaos", ["-d", domain, "-silent", "-key", settings.CHAOS_API_KEY])
    return set(lines(res.stdout)) if res.ok else set()


# ---------------- DNS resolution ----------------
def dnsx_resolve(hosts: list[str]) -> dict[str, dict]:
    """Resolve hosts with dnsx, returning {host: {a:[...], cname:..}}."""
    if not hosts or not tool_available("dnsx"):
        return {}
    res = run_tool("dnsx", ["-silent", "-json", "-a", "-cname", "-resp"], stdin_data="\n".join(hosts))
    out: dict[str, dict] = {}
    if not res.ok:
        return out
    for line in lines(res.stdout):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        host = obj.get("host")
        if not host:
            continue
        out[host] = {
            "a": obj.get("a", []),
            "cname": (obj.get("cname") or [None])[0] if obj.get("cname") else None,
        }
    return out


# ---------------- Live host probing ----------------
def httpx_probe(hosts: list[str]) -> dict[str, dict]:
    """Probe hosts with httpx; return rich HTTP metadata keyed by input host."""
    if not hosts or not tool_available("httpx"):
        return {}
    args = [
        "-silent", "-json", "-status-code", "-title", "-tech-detect",
        "-server", "-ip", "-cdn", "-asn", "-follow-redirects",
        "-rate-limit", str(settings.RECON_MAX_CONCURRENCY),
    ]
    res = run_tool("httpx", args, stdin_data="\n".join(hosts))
    out: dict[str, dict] = {}
    if not res.ok:
        return out
    for line in lines(res.stdout):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        host = obj.get("input") or obj.get("host")
        if not host:
            continue
        out[host] = {
            "status_code": obj.get("status_code"),
            "title": obj.get("title"),
            "server": obj.get("webserver"),
            "scheme": obj.get("scheme"),
            "ip": (obj.get("a") or [None])[0] if obj.get("a") else obj.get("host"),
            "cdn": obj.get("cdn_name"),
            "asn": (obj.get("asn") or {}).get("as_number") if isinstance(obj.get("asn"), dict) else None,
            "asn_org": (obj.get("asn") or {}).get("as_name") if isinstance(obj.get("asn"), dict) else None,
            "technologies": obj.get("tech", []),
            "content_length": obj.get("content_length"),
            "url": obj.get("url"),
        }
    return out


# ---------------- Port scanning ----------------
def naabu_scan(host: str, top_ports: str = "100") -> list[int]:
    if not tool_available("naabu"):
        return []
    res = run_tool("naabu", ["-host", host, "-top-ports", top_ports, "-silent"])
    ports: list[int] = []
    for line in lines(res.stdout):
        if ":" in line:
            try:
                ports.append(int(line.split(":")[-1]))
            except ValueError:
                continue
    return ports


# ---------------- Crawling ----------------
def katana_crawl(url: str, depth: int = 2) -> list[dict]:
    if not tool_available("katana"):
        return []
    res = run_tool("katana", ["-u", url, "-d", str(depth), "-jc", "-silent", "-json"])
    out: list[dict] = []
    for line in lines(res.stdout):
        try:
            obj = json.loads(line)
            endpoint = obj.get("request", {}).get("endpoint") or obj.get("endpoint")
            if endpoint:
                out.append({"url": endpoint, "is_js": endpoint.lower().endswith(".js")})
        except json.JSONDecodeError:
            continue
    return out


# ---------------- Historical URLs ----------------
def waybackurls(domain: str) -> set[str]:
    res = run_tool("waybackurls", [domain], stdin_data=domain)
    return set(lines(res.stdout)) if res.ok else set()


def gau(domain: str) -> set[str]:
    res = run_tool("gau", ["--threads", "5", domain])
    return set(lines(res.stdout)) if res.ok else set()


# ---------------- Screenshots ----------------
def gowitness(urls: list[str], out_dir: str) -> bool:
    """Capture screenshots with gowitness. Returns True if it ran."""
    if not urls or not tool_available("gowitness"):
        return False
    import os
    os.makedirs(out_dir, exist_ok=True)
    list_file = os.path.join(out_dir, "_targets.txt")
    with open(list_file, "w") as fh:
        fh.write("\n".join(urls))
    res = run_tool("gowitness", ["file", "-f", list_file, "--screenshot-path", out_dir, "-q"])
    return res.ok
