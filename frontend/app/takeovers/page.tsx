"use client";

import { useEffect, useState } from "react";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, Badge, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Takeover = {
  hostname: string; service: string; cname: string | null;
  confidence: string; risk_level: string; evidence: string | null;
};

const riskTone: Record<string, any> = { high: "risk", medium: "warn", low: "scan" };

export default function TakeoverPage() {
  const authed = useAuthGuard();
  const [rows, setRows] = useState<Takeover[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authed) return;
    api.takeovers().then(setRows).catch(() => setRows([])).finally(() => setLoading(false));
  }, [authed]);
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="Takeover Center" subtitle="Dangling DNS that may be claimable by an attacker. Detection only — verify before reporting." />
      <div className="px-8 py-6">
        {loading ? (
          <Spinner label="evaluating fingerprints…" />
        ) : rows.length === 0 ? (
          <div className="space-y-4">
            <div className="panel flex items-center gap-3 p-5">
              <ShieldCheck className="h-6 w-6 text-live" />
              <div>
                <div className="font-mono text-sm text-slate-200">No takeover candidates flagged</div>
                <div className="text-xs text-slate-500">
                  CNAMEs are checked against known fingerprints (S3, GitHub Pages, Heroku, Shopify, Azure, Zendesk, Fastly, CloudFront) during each scan.
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {rows.map((t, i) => (
              <div key={i} className="panel p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-risk" />
                    <span className="data text-slate-100">{t.hostname}</span>
                  </div>
                  <Badge tone={riskTone[t.risk_level] || "warn"}>{t.risk_level} risk</Badge>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <Meta label="Service" value={t.service} />
                  <Meta label="Confidence" value={t.confidence} />
                  <Meta label="CNAME" value={t.cname || "—"} mono />
                </div>
                {t.evidence && (
                  <div className="mt-3 rounded border border-edge bg-ink-900/70 p-2 font-mono text-[11px] text-slate-400">
                    {t.evidence}
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

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className={`mt-0.5 ${mono ? "data" : ""} truncate text-slate-300`}>{value}</div>
    </div>
  );
}
