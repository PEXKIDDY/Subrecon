"use client";

import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell as BarCell,
} from "recharts";

type Datum = { name: string; value: number };

const SCAN = "#35e0d4";
const LIVE = "#3ddc84";
const DEAD = "#5b6b86";
const BARS = ["#35e0d4", "#3ddc84", "#f5a623", "#7aa2f7", "#bb9af7", "#5b6b86"];

const tooltipStyle = {
  background: "#0c1120",
  border: "1px solid #1e2a44",
  borderRadius: 8,
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  color: "#c7d2e4",
};

function ChartCard({ title, children, empty }: { title: string; children: React.ReactNode; empty: boolean }) {
  return (
    <div className="panel p-4">
      <div className="eyebrow mb-3">{title}</div>
      {empty ? (
        <div className="flex h-44 items-center justify-center font-mono text-xs text-slate-600">
          no data yet
        </div>
      ) : (
        <div className="h-44">{children}</div>
      )}
    </div>
  );
}

export function LiveVsDead({ data }: { data: Datum[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <ChartCard title="Live vs Dead hosts" empty={total === 0}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={42} outerRadius={66} paddingAngle={3} stroke="none">
            {data.map((d, i) => <Cell key={i} fill={d.name === "Live" ? LIVE : DEAD} />)}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function BarDist({ title, data }: { title: string; data: Datum[] }) {
  return (
    <ChartCard title={title} empty={!data || data.length === 0}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={90} tick={{ fill: "#7c8aa5", fontSize: 11, fontFamily: "var(--font-mono)" }} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(53,224,212,0.06)" }} />
          <Bar dataKey="value" radius={[0, 3, 3, 0]} barSize={14}>
            {data.map((_, i) => <BarCell key={i} fill={BARS[i % BARS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
