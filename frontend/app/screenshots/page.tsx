"use client";

import { useEffect, useState } from "react";
import { Camera } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Shot = { hostname: string; path: string; url: string | null };

// Screenshots are written to a shared volume and served by nginx at /screenshots/.
function shotSrc(path: string): string {
  const file = path.split("/").pop();
  return `/screenshots/${file}`;
}

export default function ScreenshotsPage() {
  const authed = useAuthGuard();
  const [shots, setShots] = useState<Shot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authed) return;
    api.screenshots().then(setShots).catch(() => setShots([])).finally(() => setLoading(false));
  }, [authed]);
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="Screenshots" subtitle="Visual capture of live hosts for fast triage." />
      <div className="px-8 py-6">
        {loading ? (
          <Spinner label="loading captures…" />
        ) : shots.length === 0 ? (
          <EmptyState title="No screenshots captured" body="Screenshots are produced by the capture stage when gowitness (or Chromium headless) is available. Live hosts are rendered and stored to the screenshots volume." />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {shots.map((s, i) => (
              <a key={i} href={s.url || `http://${s.hostname}`} target="_blank" rel="noreferrer"
                 className="panel group overflow-hidden transition hover:border-scan/50">
                <div className="aspect-video overflow-hidden border-b border-edge bg-ink-900">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={shotSrc(s.path)} alt={s.hostname}
                       className="h-full w-full object-cover object-top opacity-90 transition group-hover:opacity-100"
                       onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                </div>
                <div className="flex items-center gap-2 px-3 py-2">
                  <Camera className="h-3.5 w-3.5 text-scan" />
                  <span className="data truncate text-xs text-slate-300">{s.hostname}</span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
