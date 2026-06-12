"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  useReactTable, getCoreRowModel, flexRender, createColumnHelper,
} from "@tanstack/react-table";
import { Search, ChevronLeft, ChevronRight, Download, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, Badge, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Asset = {
  id: number; hostname: string; ip: string | null; asn_org: string | null;
  cdn: string | null; is_live: boolean; status_code: number | null;
  title: string | null; server: string | null; level: number; source: string | null;
  last_seen: string;
  ports: { port: number }[];
  technologies: { name: string }[];
};

const col = createColumnHelper<Asset>();

export default function AssetsPage() {
  const authed = useAuthGuard();
  const [rows, setRows] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [search, setSearch] = useState("");
  const [liveOnly, setLiveOnly] = useState<"" | "true" | "false">("");
  const [sortBy, setSortBy] = useState("last_seen");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize, sort_by: sortBy, order };
      if (search) params.search = search;
      if (liveOnly) params.is_live = liveOnly;
      const data = await api.assets(params);
      setRows(data.items);
      setTotal(data.total);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, sortBy, order, search, liveOnly]);

  useEffect(() => { if (authed) load(); }, [authed, load]);

  function toggleSort(field: string) {
    if (sortBy === field) setOrder(order === "asc" ? "desc" : "asc");
    else { setSortBy(field); setOrder("desc"); }
    setPage(1);
  }

  const columns = useMemo(() => [
    col.accessor("hostname", {
      header: "Hostname",
      cell: (c) => {
        const a = c.row.original;
        const url = `http${a.status_code && a.status_code < 400 ? "s" : ""}://${a.hostname}`;
        return (
          <div className="flex items-center gap-2">
            <span className="data text-slate-100">{a.hostname}</span>
            {a.level > 2 && <Badge>L{a.level}</Badge>}
            {a.is_live && (
              <a href={url} target="_blank" rel="noreferrer" className="text-slate-600 hover:text-scan">
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        );
      },
    }),
    col.accessor("ip", { header: "IP", cell: (c) => <span className="data text-slate-400">{c.getValue() || "—"}</span> }),
    col.accessor("status_code", {
      header: "Status",
      cell: (c) => {
        const a = c.row.original;
        if (!a.is_live) return <Badge tone="dead">dead</Badge>;
        const s = c.getValue();
        const tone = !s ? "live" : s < 300 ? "live" : s < 400 ? "scan" : s < 500 ? "warn" : "risk";
        return <Badge tone={tone as any}>{s ?? "live"}</Badge>;
      },
    }),
    col.accessor("ports", { header: "Ports", cell: (c) => {
      const ps = c.getValue();
      return ps?.length ? <span className="data text-slate-300">{ps.map((p) => p.port).slice(0, 6).join(" ")}</span> : <span className="text-slate-600">—</span>;
    }}),
    col.accessor("title", { header: "Title", cell: (c) => <span className="max-w-[220px] truncate text-slate-300">{c.getValue() || "—"}</span> }),
    col.accessor("server", { header: "Server", cell: (c) => <span className="data text-slate-400">{c.getValue() || "—"}</span> }),
    col.accessor("technologies", { header: "Tech", cell: (c) => {
      const t = c.getValue();
      return t?.length ? (
        <div className="flex flex-wrap gap-1">
          {t.slice(0, 3).map((x, i) => <Badge key={i} tone="scan">{x.name}</Badge>)}
          {t.length > 3 && <span className="text-[11px] text-slate-500">+{t.length - 3}</span>}
        </div>
      ) : <span className="text-slate-600">—</span>;
    }}),
    col.accessor("cdn", { header: "CDN", cell: (c) => c.getValue() ? <Badge>{c.getValue()}</Badge> : <span className="text-slate-600">—</span> }),
  ], []);

  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() });
  const pages = Math.max(1, Math.ceil(total / pageSize));

  if (!authed) return null;

  const SORTABLE: Record<string, string> = { Hostname: "hostname", IP: "ip", Status: "status_code", Title: "title", Server: "server" };

  return (
    <div>
      <PageHeader title="Asset Explorer" subtitle={`${total.toLocaleString()} discovered hosts`}>
        <a className="btn px-2.5 py-1.5 text-xs" href={api.exportUrl("csv")} target="_blank" rel="noreferrer"><Download className="h-3.5 w-3.5" /> CSV</a>
        <a className="btn px-2.5 py-1.5 text-xs" href={api.exportUrl("json")} target="_blank" rel="noreferrer"><Download className="h-3.5 w-3.5" /> JSON</a>
        <a className="btn px-2.5 py-1.5 text-xs" href={api.exportUrl("xlsx")} target="_blank" rel="noreferrer"><Download className="h-3.5 w-3.5" /> XLSX</a>
      </PageHeader>

      <div className="px-8 py-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              className="input pl-9 data"
              placeholder="search hostname, ip, title, server…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <select className="input w-auto data" value={liveOnly} onChange={(e) => { setLiveOnly(e.target.value as any); setPage(1); }}>
            <option value="">all hosts</option>
            <option value="true">live only</option>
            <option value="false">dead only</option>
          </select>
        </div>

        {loading ? (
          <Spinner label="querying assets…" />
        ) : rows.length === 0 ? (
          <EmptyState title="No assets yet" body="Launch a scan from the dashboard to populate the attack surface. Discovered hosts will appear here with ports, technologies, and status." />
        ) : (
          <div className="panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-edge bg-ink-900/60">
                    {table.getHeaderGroups()[0].headers.map((h) => {
                      const label = String(h.column.columnDef.header);
                      const sortable = SORTABLE[label];
                      return (
                        <th key={h.id} className="px-3 py-2.5 text-left">
                          <button
                            className={`eyebrow ${sortable ? "hover:text-scan" : "cursor-default"}`}
                            onClick={() => sortable && toggleSort(sortable)}
                          >
                            {label}{sortable && sortBy === sortable ? (order === "asc" ? " ↑" : " ↓") : ""}
                          </button>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((r) => (
                    <tr key={r.id} className="border-b border-edge/50 transition hover:bg-ink-700/40">
                      {r.getVisibleCells().map((c) => (
                        <td key={c.id} className="px-3 py-2.5 align-middle">
                          {flexRender(c.column.columnDef.cell, c.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-edge px-3 py-2">
              <span className="data text-[11px] text-slate-500">page {page} / {pages}</span>
              <div className="flex gap-1">
                <button className="btn px-2 py-1" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft className="h-4 w-4" /></button>
                <button className="btn px-2 py-1" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}><ChevronRight className="h-4 w-4" /></button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
