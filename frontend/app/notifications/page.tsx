"use client";

import { Bell, MessageSquare, Send, Slack, Mail } from "lucide-react";
import { PageHeader, Badge, useAuthGuard } from "@/components/ui";

const CHANNELS = [
  { icon: MessageSquare, name: "Discord", env: "DISCORD_WEBHOOK_URL", desc: "Posts a summary to a channel webhook when a scan finishes." },
  { icon: Send, name: "Telegram", env: "TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID", desc: "Sends a message via your bot to the configured chat." },
  { icon: Slack, name: "Slack", env: "SLACK_WEBHOOK_URL", desc: "Delivers scan results to an incoming webhook." },
  { icon: Mail, name: "Email", env: "SMTP_HOST / SMTP_USER / SMTP_PASS", desc: "Emails a completion notice over SMTP." },
];

export default function NotificationsPage() {
  const authed = useAuthGuard();
  if (!authed) return null;

  return (
    <div>
      <PageHeader title="Notifications" subtitle="Outbound alerts fire automatically when a scan completes or fails." />
      <div className="px-8 py-6">
        <div className="panel mb-5 flex items-start gap-3 p-4">
          <Bell className="mt-0.5 h-4 w-4 text-scan" />
          <p className="text-xs leading-relaxed text-slate-400">
            Channels are configured by environment variables on the worker. Any channel with credentials
            present is active; the rest are skipped silently. Set the variables in your <span className="data text-slate-300">.env</span> and restart the worker to enable a channel.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {CHANNELS.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.name} className="panel p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-slate-300" />
                    <span className="text-sm font-medium text-slate-100">{c.name}</span>
                  </div>
                  <Badge>configurable</Badge>
                </div>
                <p className="mt-2 text-xs text-slate-400">{c.desc}</p>
                <div className="mt-3 rounded border border-edge bg-ink-900/70 px-2 py-1 font-mono text-[11px] text-scan/70">{c.env}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
