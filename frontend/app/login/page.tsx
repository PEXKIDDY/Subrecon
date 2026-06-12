"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Crosshair } from "lucide-react";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      if (mode === "register") {
        await api.register({ username, email, password });
      }
      const tok = await api.login(username, password);
      setToken(tok.access_token);
      router.push("/");
    } catch (e: any) {
      setError(e.message || "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen w-full items-center justify-center px-4">
      <div className="scanline panel w-full max-w-sm p-7" style={{ ["--scan-h" as any]: "360px" }}>
        <div className="flex items-center gap-2">
          <Crosshair className="h-5 w-5 text-scan" />
          <span className="font-mono text-sm font-bold tracking-[0.3em] text-white">SUBRECO</span>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          {mode === "login" ? "Authenticate to access the console." : "Create the operator account."}
        </p>

        <div className="mt-6 space-y-3">
          <div>
            <label className="eyebrow">Username</label>
            <input className="input mt-1" value={username} autoFocus
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()} />
          </div>
          {mode === "register" && (
            <div>
              <label className="eyebrow">Email</label>
              <input className="input mt-1" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} />
            </div>
          )}
          <div>
            <label className="eyebrow">Password</label>
            <input className="input mt-1" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()} />
          </div>
        </div>

        {error && <div className="mt-3 font-mono text-xs text-risk">{error}</div>}

        <button className="btn btn-scan mt-5 w-full" disabled={busy || !username || !password} onClick={submit}>
          {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account & sign in"}
        </button>

        <button
          className="mt-4 w-full text-center font-mono text-[11px] text-slate-500 hover:text-scan"
          onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}
        >
          {mode === "login" ? "First run? Create the operator account →" : "← Back to sign in"}
        </button>

        <p className="mt-6 text-center text-[10px] leading-relaxed text-slate-600">
          Authorized reconnaissance only. Scan domains you own or have explicit permission to test.
        </p>
      </div>
    </div>
  );
}
