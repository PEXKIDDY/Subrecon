"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, Badge, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Scan = {
  id: number; project_id: number; status: string; progress: number;
  current_stage: string | null; error: string | null;
  started_at: string | null; finished_at: string | null; created_at: string;
};

const statusTone: Record<string, any> = {
  completed: "live", running: "scan", queued: "neutral", failed: "risk", cancelled: "dead",
};

export default function ScansPage() {
  const authed = useAuthGuard();
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<number | null>(null);
  const [history, setHistory] = useState<Record<number, any[]>>({});

  useEffect(() => {
    if (!authed) return;
    api.scans().then(setScans).catch(() => setScans([])).finally(() => setLoading(false));
  }, [authed]);

  async function toggle(id: number) {
    if (open === id) { setOpen(null); return; }
    setOpen(id);
    if (!history[id]) {
      try { const h = await api.scanHistory(id); setHistory((p) => ({ ...p, [id]: h })); }
      catch { setHistory((p) => ({ ...p, [id]: [] })); }
    }
  }
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="Scan History" subtitle="Every reconnaissance run and its stage-by-stage timeline." />
      <div className="px-8 py-6">
        {loading ? (
          <Spinner label="loading scans…" />
        ) : scans.length === 0 ? (
          <EmptyState title="No scans run yet" body="Start your first scan from the dashboard. Each run is recorded here with full stage history and resulting stats." />
        ) : (
          <div className="panel divide-y divide-edge/60">
            {scans.map((s) => (
              <div key={s.id}>
                <button onClick={() => toggle(s.id)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-ink-700/40">
                  {open === s.id ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
                  <span className="data text-sm text-slate-500">#{s.id}</span>
                  <Badge tone={statusTone[s.status] || "neutral"}>{s.status}</Badge>
                  <span className="data flex-1 text-xs text-slate-400">
                    {s.current_stage || "—"} · {s.progress}%
                  </span>
                  <span className="data text-[11px] text-slate-600">{new Date(s.created_at).toLocaleString()}</span>
                </button>
                {open === s.id && (
                  <div className="border-t border-edge bg-ink-900/50 px-4 py-3">
                    {!history[s.id] ? (
                      <Spinner label="loading timeline…" />
                    ) : history[s.id].length === 0 ? (
                      <div className="font-mono text-[11px] text-slate-600">no stage events recorded</div>
                    ) : (
                      <ol className="space-y-1">
                        {history[s.id].map((h) => (
                          <li key={h.id} className="font-mono text-[11px] leading-relaxed">
                            <span className={h.level === "error" ? "text-risk" : "text-scan/70"}>[{h.stage}]</span>{" "}
                            <span className="text-slate-300">{h.message}</span>{" "}
                            <span className="text-slate-600">{new Date(h.created_at).toLocaleTimeString()}</span>
                          </li>
                        ))}
                      </ol>
                    )}
                    {s.error && <div className="mt-2 font-mono text-[11px] text-risk">error: {s.error}</div>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
