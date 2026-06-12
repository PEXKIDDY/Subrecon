"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, Badge, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Way = { url: string; params: string | null; category: string | null; source: string | null };
type Endpoint = { url?: string; path?: string; secret_type?: string | null; secret_match?: string | null; source?: string | null };

const CATS = ["", "admin", "login", "api", "backup"];
const catTone: Record<string, any> = { admin: "risk", login: "warn", api: "scan", backup: "warn" };

export default function WaybackPage() {
  const authed = useAuthGuard();
  const [tab, setTab] = useState<"urls" | "secrets">("urls");
  const [cat, setCat] = useState("");
  const [urls, setUrls] = useState<Way[]>([]);
  const [eps, setEps] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);

  const loadUrls = useCallback(async () => {
    setLoading(true);
    try { setUrls(await api.wayback(cat || undefined)); } catch { setUrls([]); } finally { setLoading(false); }
  }, [cat]);

  useEffect(() => {
    if (!authed) return;
    api.endpoints(true).then(setEps).catch(() => setEps([]));
  }, [authed]);
  useEffect(() => { if (authed && tab === "urls") loadUrls(); }, [authed, tab, loadUrls]);
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="Wayback & JS" subtitle="Historical URLs and secrets surfaced from crawled JavaScript.">
        <div className="flex rounded-md border border-edge bg-ink-700 p-0.5">
          {(["urls", "secrets"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`rounded px-3 py-1 font-mono text-xs uppercase tracking-wide ${tab === t ? "bg-scan/15 text-scan" : "text-slate-400 hover:text-slate-200"}`}>
              {t === "urls" ? "Wayback URLs" : `Secrets · ${eps.length}`}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="px-8 py-6">
        {tab === "urls" ? (
          <>
            <div className="mb-4 flex flex-wrap gap-1.5">
              {CATS.map((c) => (
                <button key={c || "all"} onClick={() => setCat(c)}
                  className={`btn px-3 py-1 text-xs ${cat === c ? "btn-scan" : ""}`}>
                  {c || "all"}
                </button>
              ))}
            </div>
            {loading ? (
              <Spinner label="loading archived urls…" />
            ) : urls.length === 0 ? (
              <EmptyState title="No archived URLs" body="Wayback and gau collect historical URLs during the wayback stage, then categorize them (admin, login, api, backup) with gf-style patterns." />
            ) : (
              <div className="panel divide-y divide-edge/50">
                {urls.map((u, i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2">
                    {u.category && <Badge tone={catTone[u.category] || "neutral"}>{u.category}</Badge>}
                    <a href={u.url} target="_blank" rel="noreferrer" className="data truncate text-xs text-slate-300 hover:text-scan">{u.url}</a>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : eps.length === 0 ? (
          <EmptyState title="No secrets detected" body="During JS intelligence, crawled scripts are scanned with trufflehog-style patterns (AWS, Google, Slack, GitHub, Stripe, private keys, JWTs). Findings appear here." />
        ) : (
          <div className="space-y-2">
            {eps.map((e, i) => (
              <div key={i} className="panel flex items-start gap-3 p-3">
                <KeyRound className="mt-0.5 h-4 w-4 text-risk" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Badge tone="risk">{e.secret_type || "secret"}</Badge>
                    <span className="data truncate text-xs text-slate-400">{e.url || e.path}</span>
                  </div>
                  {e.secret_match && (
                    <div className="mt-1 truncate rounded bg-ink-900/70 px-2 py-1 font-mono text-[11px] text-warn">{e.secret_match}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
