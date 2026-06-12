"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Badge, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Dns = { hostname: string; type: string; value: string; ttl: number | null };
type Port = { hostname: string; port: number; protocol: string; service: string | null; state: string | null };

export default function DnsPortsPage() {
  const authed = useAuthGuard();
  const [tab, setTab] = useState<"dns" | "ports">("dns");
  const [dns, setDns] = useState<Dns[]>([]);
  const [ports, setPorts] = useState<Port[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authed) return;
    Promise.all([
      api.dns().then(setDns).catch(() => setDns([])),
      api.ports().then(setPorts).catch(() => setPorts([])),
    ]).finally(() => setLoading(false));
  }, [authed]);
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="DNS & Ports" subtitle="Resolved records and open services across the surface.">
        <div className="flex rounded-md border border-edge bg-ink-700 p-0.5">
          {(["dns", "ports"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`rounded px-3 py-1 font-mono text-xs uppercase tracking-wide ${tab === t ? "bg-scan/15 text-scan" : "text-slate-400 hover:text-slate-200"}`}>
              {t === "dns" ? `DNS · ${dns.length}` : `Ports · ${ports.length}`}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="px-8 py-6">
        {loading ? (
          <Spinner label="loading records…" />
        ) : tab === "dns" ? (
          dns.length === 0 ? (
            <EmptyState title="No DNS records" body="DNS records are collected during the resolution stage of each scan." />
          ) : (
            <Table head={["Hostname", "Type", "Value", "TTL"]}>
              {dns.map((d, i) => (
                <tr key={i} className="border-b border-edge/50 hover:bg-ink-700/40">
                  <Td mono>{d.hostname}</Td>
                  <Td><Badge tone="scan">{d.type}</Badge></Td>
                  <Td mono className="text-slate-300">{d.value}</Td>
                  <Td mono className="text-slate-500">{d.ttl ?? "—"}</Td>
                </tr>
              ))}
            </Table>
          )
        ) : ports.length === 0 ? (
          <EmptyState title="No open ports" body="Port data is populated when naabu (or an equivalent scanner) is available during a scan." />
        ) : (
          <Table head={["Hostname", "Port", "Protocol", "Service", "State"]}>
            {ports.map((p, i) => (
              <tr key={i} className="border-b border-edge/50 hover:bg-ink-700/40">
                <Td mono>{p.hostname}</Td>
                <Td><Badge tone="warn">{p.port}</Badge></Td>
                <Td mono className="text-slate-400">{p.protocol}</Td>
                <Td className="text-slate-300">{p.service || "—"}</Td>
                <Td mono className="text-slate-500">{p.state || "—"}</Td>
              </tr>
            ))}
          </Table>
        )}
      </div>
    </div>
  );
}

function Table({ head, children }: { head: string[]; children: React.ReactNode }) {
  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-edge bg-ink-900/60">
              {head.map((h) => <th key={h} className="px-3 py-2.5 text-left eyebrow">{h}</th>)}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
    </div>
  );
}
function Td({ children, mono, className = "" }: { children: React.ReactNode; mono?: boolean; className?: string }) {
  return <td className={`px-3 py-2 ${mono ? "data text-slate-200" : ""} ${className}`}>{children}</td>;
}
