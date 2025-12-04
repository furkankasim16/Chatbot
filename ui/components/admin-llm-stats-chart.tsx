"use client";

import { useEffect, useState } from "react";
import type { LlmStatsSummary } from "@/app/types/llm";
import { fetchLlmStatsSummary } from "@/lib/api";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";

export function LlmPerformanceChart() {
  const [data, setData] = useState<
    { model_name: string; avgLatencySec: number; total_calls: number }[]
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const stats = await fetchLlmStatsSummary();

        setData(
          stats.map((row: LlmStatsSummary) => ({
            model_name: row.model_name,
            avgLatencySec: (row.avg_latency_ms ?? 0) / 1000,
            total_calls: row.total_calls,
          }))
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Grafik yükleniyor...</div>;
  if (!data.length) return <div>Henüz LLM kaydı yok.</div>;

  return (
    <div className="w-full h-[350px]">
      <h2 className="text-xl font-semibold mb-3">
        Model Karşılaştırma Grafiği
      </h2>

      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey="model_name" />
          <YAxis
            tickFormatter={(v) => `${v}s`}
            label={{
              value: "Latency (sn)",
              angle: -90,
              position: "insideLeft",
            }}
          />
          <Tooltip
            formatter={(value: any, _name, props: any) => {
              const row = props.payload as (typeof data)[number];
              return [`${row.avgLatencySec.toFixed(2)} sn`, "Ortalama Latency"];
            }}
          />
          <Bar
            dataKey="avgLatencySec"
            name="Ortalama Latency (sn)"
            fill="#6366F1"           // 🔥 SABİT, CANLI BİR RENK
            radius={[6, 6, 0, 0]}    // köşeleri yuvarlak
          >
            <LabelList
              dataKey="avgLatencySec"
              position="top"
              formatter={(v: number) => `${v.toFixed(1)}s`}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}