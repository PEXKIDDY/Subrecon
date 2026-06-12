"""The scan pipeline orchestrator.

Executes the documented workflow end-to-end, persisting results stage-by-stage
and emitting progress via a callback (used to update the DB + WebSocket). Each
stage is fault-isolated so a single failing tool never aborts the whole scan.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ApiEndpoint,
    Asset,
    CrawlResult,
    DnsRecord,
    Port,
    Takeover,
    Technology,
    WaybackUrl,
)
from app.recon import dnsutil, js_intel, passive, takeover, tools
from app.recon.runner import tool_available

ProgressCB = Callable[[str, str, int], None]  # (stage, message, progress_pct)


# Pipeline stages with their progress weight (cumulative target %).
STAGES = [
    ("passive_sources", 8),
    ("subfinder", 14),
    ("assetfinder", 18),
    ("amass", 24),
    ("chaos", 27),
    ("merge_dedupe", 30),
    ("dns_resolution", 45),
    ("live_hosts", 62),
    ("port_scan", 72),
    ("screenshots", 78),
    ("technologies", 82),
    ("wayback", 88),
    ("crawl", 92),
    ("js_intel", 96),
    ("takeover", 99),
    ("store", 100),
]


class ReconOrchestrator:
    def __init__(self, db: Session, project_id: int, scan_id: int, domain: str, progress: ProgressCB):
        self.db = db
        self.project_id = project_id
        self.scan_id = scan_id
        self.domain = domain.strip().lower().lstrip("*.")
        self.progress = progress
        self.hosts: set[str] = set()
        self.sources: dict[str, set[str]] = {}
        self.assets: dict[str, Asset] = {}
        self.stats: dict[str, int] = {}

    # ----- helpers -----
    def _pct(self, stage_name: str) -> int:
        for name, pct in STAGES:
            if name == stage_name:
                return pct
        return 0

    def _emit(self, stage: str, message: str):
        self.progress(stage, message, self._pct(stage))

    # ----- stages -----
    def stage_passive(self):
        self._emit("passive_sources", "Querying passive sources (crt.sh, OTX, RapidDNS...)")
        self.sources = passive.collect_passive(self.domain)
        for src, hosts in self.sources.items():
            self.hosts |= hosts
        self.hosts.add(self.domain)
        self._emit("passive_sources", f"Passive sources returned {len(self.hosts)} hosts")

    def stage_active_enum(self):
        for stage, fn in (
            ("subfinder", tools.subfinder),
            ("assetfinder", tools.assetfinder),
            ("amass", tools.amass),
            ("chaos", tools.chaos),
        ):
            if tool_available(stage) or stage == "chaos":
                self._emit(stage, f"Running {stage}")
                found = fn(self.domain)
                self.hosts |= found
                self.sources[stage] = found
                self._emit(stage, f"{stage}: +{len(found)} hosts (total {len(self.hosts)})")
            else:
                self._emit(stage, f"{stage} not installed — skipping")

    def stage_merge(self):
        self._emit("merge_dedupe", "Merging and de-duplicating")
        self.hosts = {h for h in self.hosts if h and h.endswith(self.domain)}
        self.stats["total_assets"] = len(self.hosts)
        self._emit("merge_dedupe", f"{len(self.hosts)} unique hosts")

    def stage_dns(self):
        self._emit("dns_resolution", "Resolving DNS records")
        host_list = sorted(self.hosts)
        dnsx_data = tools.dnsx_resolve(host_list) if tool_available("dnsx") else {}

        for host in host_list:
            asset = self._get_or_create_asset(host)
            asset.level = dnsutil.subdomain_level(host, self.domain)
            asset.source = ",".join(s for s, hs in self.sources.items() if host in hs)[:255] or None

            if host in dnsx_data:
                d = dnsx_data[host]
                asset.ip = (d.get("a") or [None])[0]
                asset.cname = d.get("cname")
            else:
                resolved = dnsutil.resolve_host(host)
                asset.ip = (resolved["a"] or [None])[0]
                asset.cname = resolved["cname"]
                for rtype, value, ttl in resolved["records"][:25]:
                    self.db.add(DnsRecord(asset=asset, record_type=rtype, value=value[:1024], ttl=ttl))
        self.db.flush()
        self._emit("dns_resolution", "DNS resolution complete")

    def stage_live(self):
        self._emit("live_hosts", "Probing live hosts (httpx)")
        host_list = sorted(self.hosts)
        probe = tools.httpx_probe(host_list)
        live = 0
        for host, asset in self.assets.items():
            data = probe.get(host)
            if data:
                asset.is_live = True
                asset.status_code = data.get("status_code")
                asset.title = (data.get("title") or "")[:512] or None
                asset.server = (data.get("server") or "")[:255] or None
                asset.scheme = data.get("scheme")
                asset.ip = data.get("ip") or asset.ip
                asset.cdn = data.get("cdn")
                asset.asn = str(data.get("asn")) if data.get("asn") else asset.asn
                asset.asn_org = data.get("asn_org")
                asset.content_length = data.get("content_length")
                for tech in data.get("technologies", []) or []:
                    self.db.add(Technology(asset=asset, name=str(tech)[:128]))
                live += 1
            else:
                # If httpx unavailable, treat resolvable hosts as tentatively live.
                if not tool_available("httpx") and asset.ip:
                    asset.is_live = True
                    live += 1
        self.db.flush()
        self.stats["live_hosts"] = live
        self.stats["dead_hosts"] = len(self.hosts) - live
        self._emit("live_hosts", f"{live} live hosts")

    def stage_ports(self):
        if not tool_available("naabu"):
            self._emit("port_scan", "naabu not installed — skipping port scan")
            return
        self._emit("port_scan", "Scanning ports on live hosts (naabu)")
        total = 0
        for host, asset in self.assets.items():
            if not asset.is_live:
                continue
            for p in tools.naabu_scan(host):
                self.db.add(Port(asset=asset, port=p, protocol="tcp", state="open"))
                total += 1
        self.db.flush()
        self.stats["open_ports"] = total
        self._emit("port_scan", f"{total} open ports found")

    def stage_screenshots(self):
        live_urls = [
            f"{a.scheme or 'https'}://{h}" for h, a in self.assets.items() if a.is_live
        ]
        if not tool_available("gowitness") or not live_urls:
            self._emit("screenshots", "gowitness not installed or no live hosts — skipping")
            return
        self._emit("screenshots", f"Capturing {len(live_urls)} screenshots")
        out_dir = os.path.join(settings.SCREENSHOT_DIR, str(self.scan_id))
        tools.gowitness(live_urls, out_dir)
        # Screenshot rows are linked opportunistically; gowitness writes <host>.png
        from app.models import Screenshot
        count = 0
        for host, asset in self.assets.items():
            if not asset.is_live:
                continue
            candidate = os.path.join(out_dir, f"{host}.png")
            if os.path.exists(candidate):
                self.db.add(Screenshot(asset=asset, path=candidate, url=f"https://{host}"))
                count += 1
        self.db.flush()
        self.stats["screenshots"] = count
        self._emit("screenshots", f"{count} screenshots captured")

    def stage_wayback(self):
        self._emit("wayback", "Collecting historical URLs (wayback/gau)")
        urls: set[str] = set()
        urls |= tools.waybackurls(self.domain)
        urls |= tools.gau(self.domain)
        stored = 0
        for url in list(urls)[:5000]:
            self.db.add(WaybackUrl(
                project_id=self.project_id,
                url=url[:2000],
                params=js_intel.extract_params(url),
                category=js_intel.categorize_url(url),
                source="wayback",
            ))
            stored += 1
        self.db.flush()
        self.stats["wayback_urls"] = stored
        self._emit("wayback", f"{stored} historical URLs stored")

    def stage_crawl(self):
        if not tool_available("katana"):
            self._emit("crawl", "katana not installed — skipping crawl")
            return
        self._emit("crawl", "Crawling live hosts (katana)")
        js_count = 0
        seen: set[str] = set()
        for host, asset in self.assets.items():
            if not asset.is_live:
                continue
            for entry in tools.katana_crawl(f"{asset.scheme or 'https'}://{host}"):
                if entry["url"] in seen:
                    continue
                seen.add(entry["url"])
                self.db.add(CrawlResult(
                    project_id=self.project_id, url=entry["url"][:2000],
                    is_js=entry["is_js"], source="katana",
                ))
                if entry["is_js"]:
                    js_count += 1
        self.db.flush()
        self.stats["js_files"] = js_count
        self._emit("crawl", f"Crawl complete ({js_count} JS files)")

    def stage_js_intel(self):
        self._emit("js_intel", "Analysing JavaScript for secrets & endpoints")
        js_urls = [r.url for r in self.db.query(CrawlResult).filter(
            CrawlResult.project_id == self.project_id, CrawlResult.is_js.is_(True)).limit(50)]
        endpoints = 0
        for js_url in js_urls:
            findings = js_intel.scan_js_for_secrets(js_url)
            for ep in findings["endpoints"]:
                self.db.add(ApiEndpoint(project_id=self.project_id, url=ep[:2000], source_js=js_url[:2000]))
                endpoints += 1
            for sec in findings["secrets"]:
                self.db.add(ApiEndpoint(
                    project_id=self.project_id, url=js_url[:2000], source_js=js_url[:2000],
                    secret_type=sec["type"], secret_match=sec["match"],
                ))
        self.db.flush()
        self.stats["api_endpoints"] = endpoints
        self._emit("js_intel", f"{endpoints} API endpoints extracted")

    def stage_takeover(self):
        self._emit("takeover", "Checking for subdomain takeovers")
        found = 0
        for host, asset in self.assets.items():
            if not asset.cname:
                continue
            result = takeover.detect_takeover(host, asset.cname)
            if result:
                self.db.add(Takeover(asset=asset, **result))
                found += 1
        self.db.flush()
        self.stats["takeovers"] = found
        self._emit("takeover", f"{found} potential takeovers flagged")

    # ----- internals -----
    def _get_or_create_asset(self, host: str) -> Asset:
        if host in self.assets:
            return self.assets[host]
        existing = self.db.query(Asset).filter(
            Asset.project_id == self.project_id, Asset.hostname == host).first()
        if existing:
            existing.scan_id = self.scan_id
            self.assets[host] = existing
            return existing
        asset = Asset(project_id=self.project_id, scan_id=self.scan_id, hostname=host)
        self.db.add(asset)
        self.assets[host] = asset
        return asset

    def run(self) -> dict:
        self.stage_passive()
        self.stage_active_enum()
        self.stage_merge()
        self.stage_dns()
        self.stage_live()
        self.stage_ports()
        self.stage_screenshots()
        self.stage_wayback()
        self.stage_crawl()
        self.stage_js_intel()
        self.stage_takeover()
        self._emit("store", "Finalising results")
        self.db.commit()
        return self.stats
