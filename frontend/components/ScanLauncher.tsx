"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Square, Radar } from "lucide-react";
import { api, scanSocket } from "@/lib/api";

type Event = { stage: string; message: string; progress: number; scan_id?: number };

export function ScanLauncher({ onComplete }: { onComplete?: () => void }) {
  const [domain, setDomain] = useState("");
  const [scanId, setScanId] = useState<number | null>(null);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string>("");
  const [log, setLog] = useState<Event[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sockRef = useRef<WebSocket | null>(null);
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => () => sockRef.current?.close(), []);
  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [log]);

  async function launch() {
    setError(null);
    const d = domain.trim().toLowerCase();
    if (!/^([a-z0-9-]+\.)+[a-z]{2,}$/.test(d)) {
      setError("Enter a valid root domain, e.g. example.com");
      return;
    }
    setRunning(true);
    setProgress(0);
    setLog([]);
    setStage("queued");
    try {
      const scan = await api.startScan(d);
      setScanId(scan.id);
      const sock = scanSocket(scan.id, (e: Event) => {
        setProgress(e.progress ?? 0);
        setStage(e.stage);
        setLog((prev) => [...prev, e].slice(-200));
        if (e.stage === "completed" || e.stage === "failed") {
          setRunning(false);
          sock.close();
          if (e.stage === "completed") onComplete?.();
          if (e.stage === "failed") setError(e.message);
        }
      });
      sockRef.current = sock;
    } catch (e: any) {
      setError(e.message || "Failed to start scan");
      setRunning(false);
    }
  }

  function stop() {
    sockRef.current?.close();
    setRunning(false);
    setStage("detached");
  }

  return (
    <div className="scanline panel p-5" style={{ ["--scan-h" as any]: "200px" }}>
      <div className="flex items-center justify-between">
        <div className="eyebrow flex items-center gap-2"><Radar className="h-3.5 w-3.5" /> New reconnaissance</div>
        {scanId && <span className="data text-[11px] text-slate-500">scan #{scanId}</span>}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          className="input data"
          placeholder="example.com"
          value={domain}
          disabled={running}
          onChange={(e) => setDomain(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !running && launch()}
        />
        {running ? (
          <button className="btn" onClick={stop}><Square className="h-4 w-4" /> Detach</button>
        ) : (
          <button className="btn btn-scan whitespace-nowrap" onClick={launch} disabled={!domain}>
            <Play className="h-4 w-4" /> Launch scan
          </button>
        )}
      </div>

      {error && <div className="mt-2 font-mono text-xs text-risk">{error}</div>}

      {(running || progress > 0) && (
        <div className="mt-4">
          <div className="flex items-center justify-between font-mono text-[11px]">
            <span className="text-scan">{stage}</span>
            <span className="text-slate-400">{progress}%</span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-900">
            <div className="h-full rounded-full bg-scan transition-all duration-500" style={{ width: `${progress}%` }} />
          </div>

          <div ref={logRef} className="mt-3 max-h-36 overflow-y-auto rounded border border-edge bg-ink-900/70 p-2">
            {log.length === 0 ? (
              <div className="font-mono text-[11px] text-slate-600">waiting for worker…</div>
            ) : (
              log.map((e, i) => (
                <div key={i} className="font-mono text-[11px] leading-relaxed">
                  <span className="text-scan/70">{String(e.progress).padStart(3, " ")}%</span>{" "}
                  <span className="text-slate-500">[{e.stage}]</span>{" "}
                  <span className="text-slate-300">{e.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
