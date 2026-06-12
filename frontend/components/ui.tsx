"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { getToken } from "@/lib/api";

/** Redirect to /login if there is no token. Returns false until verified. */
export function useAuthGuard(): boolean {
  const router = useRouter();
  const [ok, setOk] = useState(false);
  useEffect(() => {
    if (!getToken()) router.replace("/login");
    else setOk(true);
  }, [router]);
  return ok;
}

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-edge px-8 py-6">
      <div>
        <h1 className="font-mono text-xl font-bold tracking-wide text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </header>
  );
}

export function StatTile({
  label,
  value,
  accent = "scan",
  hint,
}: {
  label: string;
  value: number | string;
  accent?: "scan" | "live" | "risk" | "warn" | "slate";
  hint?: string;
}) {
  const color = {
    scan: "text-scan",
    live: "text-live",
    risk: "text-risk",
    warn: "text-warn",
    slate: "text-slate-200",
  }[accent];
  return (
    <div className="panel p-4">
      <div className="eyebrow">{label}</div>
      <div className={clsx("mt-2 data text-3xl font-bold", color)}>{value}</div>
      {hint && <div className="mt-1 text-[11px] text-slate-500">{hint}</div>}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "live" | "dead" | "risk" | "warn" | "scan";
}) {
  const tones = {
    neutral: "border-edge text-slate-300",
    live: "border-live/40 bg-live/10 text-live",
    dead: "border-dead/40 bg-dead/10 text-dead",
    risk: "border-risk/40 bg-risk/10 text-risk",
    warn: "border-warn/40 bg-warn/10 text-warn",
    scan: "border-scan/40 bg-scan/10 text-scan",
  }[tone];
  return (
    <span className={clsx("inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px]", tones)}>
      {children}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-slate-400">
      <span className="h-3 w-3 animate-ping rounded-full bg-scan" />
      <span className="font-mono text-xs">{label ?? "loading…"}</span>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="panel flex flex-col items-center justify-center gap-2 px-6 py-16 text-center">
      <div className="font-mono text-sm text-slate-300">{title}</div>
      <div className="max-w-md text-xs text-slate-500">{body}</div>
    </div>
  );
}
