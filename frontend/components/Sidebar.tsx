"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Boxes,
  Radar,
  Camera,
  Network,
  ShieldAlert,
  ScrollText,
  Bell,
  FolderGit2,
  LogOut,
  Crosshair,
} from "lucide-react";
import { clearToken } from "@/lib/api";

const NAV = [
  { group: "Operate", items: [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/assets", label: "Asset Explorer", icon: Boxes },
    { href: "/scans", label: "Scan History", icon: ScrollText },
  ]},
  { group: "Intelligence", items: [
    { href: "/dns", label: "DNS & Ports", icon: Network },
    { href: "/screenshots", label: "Screenshots", icon: Camera },
    { href: "/takeovers", label: "Takeover Center", icon: ShieldAlert },
    { href: "/wayback", label: "Wayback & JS", icon: Radar },
  ]},
  { group: "Manage", items: [
    { href: "/projects", label: "Projects", icon: FolderGit2 },
    { href: "/notifications", label: "Notifications", icon: Bell },
  ]},
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  if (pathname === "/login") return null;

  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-edge bg-ink-900/80">
      <div className="flex items-center gap-2 px-5 py-5">
        <Crosshair className="h-5 w-5 text-scan" />
        <div className="leading-none">
          <div className="font-mono text-sm font-bold tracking-[0.3em] text-white">SUBRECO</div>
          <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">
            surface intel
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
        {NAV.map((section) => (
          <div key={section.group}>
            <div className="px-2 pb-2 eyebrow">{section.group}</div>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const active = pathname === item.href;
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={clsx(
                        "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
                        active
                          ? "bg-scan/10 text-scan shadow-glow"
                          : "text-slate-400 hover:bg-ink-700/60 hover:text-slate-100"
                      )}
                    >
                      <Icon className={clsx("h-4 w-4", active ? "text-scan" : "text-slate-500 group-hover:text-slate-300")} />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <button
        onClick={() => { clearToken(); router.push("/login"); }}
        className="m-3 flex items-center gap-3 rounded-md px-3 py-2 text-sm text-slate-400 transition hover:bg-ink-700/60 hover:text-risk"
      >
        <LogOut className="h-4 w-4" />
        Sign out
      </button>
    </aside>
  );
}
