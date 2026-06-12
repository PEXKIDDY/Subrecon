// Minimal typed API client for the SUBRECO backend.
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost/api";
const WS = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost/ws";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("subreco_token");
}
export function setToken(t: string) { localStorage.setItem("subreco_token", t); }
export function clearToken() { localStorage.removeItem("subreco_token"); }

async function req(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as any) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    clearToken();
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.status === 204 ? null : res.json();
}

export const api = {
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error("Invalid credentials");
    return res.json();
  },
  register: (data: any) => req("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  me: () => req("/auth/me"),
  startScan: (domain: string) => req("/scan", { method: "POST", body: JSON.stringify({ domain }) }),
  scans: () => req("/scans"),
  scan: (id: number) => req(`/scans/${id}`),
  stats: (projectId?: number) => req(`/dashboard/stats${projectId ? `?project_id=${projectId}` : ""}`),
  charts: (projectId?: number) => req(`/dashboard/charts${projectId ? `?project_id=${projectId}` : ""}`),
  assets: (params: Record<string, any> = {}) => {
    const q = new URLSearchParams(params as any).toString();
    return req(`/assets?${q}`);
  },
  takeovers: (projectId?: number) => req(`/takeovers${projectId ? `?project_id=${projectId}` : ""}`),
  scanHistory: (id: number) => req(`/scans/${id}/history`),
  dns: (projectId?: number) => req(`/dns${projectId ? `?project_id=${projectId}` : ""}`),
  ports: (projectId?: number) => req(`/ports${projectId ? `?project_id=${projectId}` : ""}`),
  wayback: (category?: string) => req(`/wayback${category ? `?category=${category}` : ""}`),
  endpoints: (secretsOnly = false) => req(`/endpoints${secretsOnly ? "?secrets_only=true" : ""}`),
  certificates: (projectId?: number) => req(`/certificates${projectId ? `?project_id=${projectId}` : ""}`),
  screenshots: (projectId?: number) => req(`/screenshots${projectId ? `?project_id=${projectId}` : ""}`),
  projects: () => req("/projects"),
  exportUrl: (fmt: string, projectId?: number) =>
    `${API}/export?fmt=${fmt}${projectId ? `&project_id=${projectId}` : ""}`,
};

export function scanSocket(scanId: number, onEvent: (e: any) => void): WebSocket {
  const ws = new WebSocket(`${WS}/scans/${scanId}`);
  ws.onmessage = (m) => { try { onEvent(JSON.parse(m.data)); } catch {} };
  return ws;
}
