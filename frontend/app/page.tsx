"use client";

import { useCallback, useEffect, useState } from "react";
import { Download } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, StatTile, Spinner, useAuthGuard } from "@/components/ui";
import { ScanLauncher } from "@/components/ScanLauncher";
import { LiveVsDead, BarDist } from "@/components/Charts";

export default function DashboardPage() {
  const authed = useAuthGuard();
  const [stats, setStats] = useState<any>(null);
  const [charts, setCharts] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([api.stats(), api.charts()]);
      setStats(s);
      setCharts(c);
    } catch {
      /* surfaced via empty widgets */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (authed) load(); }, [authed, load]);
  if (!authed) return null;

  const tiles: [string, number, any][] = stats
    ? [
        ["Total assets", stats.total_assets, "scan"],
        ["Live hosts", stats.live_hosts, "live"],
        ["Dead hosts", stats.dead_hosts, "slate"],
        ["Open ports", stats.open_ports, "warn"],
        ["Technologies", stats.technologies, "scan"],
        ["Screenshots", stats.screenshots, "slate"],
        ["DNS records", stats.dns_records, "scan"],
        ["Wayback URLs", stats.wayback_urls, "slate"],
        ["API endpoints", stats.api_endpoints, "warn"],
        ["JS files", stats.js_files, "slate"],
        ["Takeover risks", stats.takeovers, "risk"],
      ]
    : [];

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Live attack-surface posture across all projects.">
        <ExportMenu />
      </PageHeader>

      <div className="space-y-6 px-8 py-6">
        <ScanLauncher onComplete={load} />

        {loading ? (
          <Spinner label="loading surface data…" />
        ) : (
          <>
            <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
              {tiles.map(([label, value, accent]) => (
                <StatTile key={label} label={label} value={value ?? 0} accent={accent} />
              ))}
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
              <LiveVsDead data={charts?.live_vs_dead ?? []} />
              <BarDist title="Technology distribution" data={charts?.technology_distribution ?? []} />
              <BarDist title="Port distribution" data={charts?.port_distribution ?? []} />
              <BarDist title="ASN distribution" data={charts?.asn_distribution ?? []} />
              <BarDist title="DNS record distribution" data={charts?.dns_distribution ?? []} />
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function ExportMenu() {
  const fmts = ["csv", "json", "xlsx", "pdf"];
  return (
    <div className="flex items-center gap-1.5">
      {fmts.map((f) => (
        <a key={f} className="btn px-2.5 py-1.5 text-xs" href={api.exportUrl(f)} target="_blank" rel="noreferrer">
          <Download className="h-3.5 w-3.5" /> {f.toUpperCase()}
        </a>
      ))}
    </div>
  );
}
