"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FolderGit2, RotateCw } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, useAuthGuard } from "@/components/ui";

type Project = { id: number; name: string; root_domain: string; description: string | null; created_at: string };

export default function ProjectsPage() {
  const authed = useAuthGuard();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    if (!authed) return;
    api.projects().then(setProjects).catch(() => setProjects([])).finally(() => setLoading(false));
  }, [authed]);

  async function rescan(p: Project) {
    setBusy(p.id);
    try { await api.startScan(p.root_domain); router.push("/scans"); }
    catch { setBusy(null); }
  }
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="Projects" subtitle="Each root domain you scan becomes a project that aggregates its assets over time." />
      <div className="px-8 py-6">
        {loading ? (
          <Spinner label="loading projects…" />
        ) : projects.length === 0 ? (
          <EmptyState title="No projects yet" body="Projects are created automatically the first time you scan a root domain. Launch a scan from the dashboard to begin." />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <div key={p.id} className="panel p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FolderGit2 className="h-4 w-4 text-scan" />
                    <span className="data text-sm text-slate-100">{p.root_domain}</span>
                  </div>
                  <span className="data text-[11px] text-slate-600">#{p.id}</span>
                </div>
                {p.description && <p className="mt-2 text-xs text-slate-400">{p.description}</p>}
                <div className="mt-3 flex items-center justify-between">
                  <span className="data text-[11px] text-slate-600">{new Date(p.created_at).toLocaleDateString()}</span>
                  <button className="btn px-2.5 py-1 text-xs" disabled={busy === p.id} onClick={() => rescan(p)}>
                    <RotateCw className={`h-3.5 w-3.5 ${busy === p.id ? "animate-spin" : ""}`} /> Rescan
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
