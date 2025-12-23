// app/components/admin-llm-stats-chart.tsx
"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { AlertCircle } from "lucide-react"
import { fetchLlmStatsSummary } from "@/lib/api"
import type { LlmStatsSummary } from "@/app/types/llm"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts"

export function LlmPerformanceChart({ token }: { token: string }) {
  const [data, setData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const stats = await fetchLlmStatsSummary(token)
        if (cancelled) return

        const chartData = (stats as LlmStatsSummary[]).map((s) => {
          const anyS = s as any
          let rawName = anyS.model ?? anyS.model_name ?? "Model"
          // Prefix cleaning for better display
          rawName = rawName.replace("ollama:", "").replace("openai:", "")

          return {
            name: rawName,
            avgLatency: anyS.avg_latency_ms ?? anyS.avg_ms ?? 0,
            successRate:
              anyS.success_rate != null
                ? Math.round(anyS.success_rate * 100)
                : anyS.success_percentage ?? 0,
          }
        })

        setData(chartData)
      } catch (err) {
        if (cancelled) return
        console.error("[LlmPerformanceChart] fetch error:", err)
        setError(
          err instanceof Error
            ? err.message
            : "LLM performans verileri alınamadı",
        )
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Card className="p-6 space-y-4">
      <h3 className="text-lg font-semibold">LLM Performans Grafiği</h3>

      {isLoading && (
        <p className="text-sm text-muted-foreground">
          Grafik yükleniyor…
        </p>
      )}

      {!isLoading && error && (
        <div className="flex items-start gap-2 text-sm text-red-400 bg-red-950/30 border border-red-800 rounded-md p-3">
          <AlertCircle className="w-4 h-4 mt-0.5" />
          <div>
            <p className="font-medium">Grafik verisi alınırken hata oluştu</p>
            <p className="text-xs opacity-80">{error}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Grafikte gösterilecek veri bulunmuyor.
        </p>
      )}

      {!isLoading && !error && data.length > 0 && (
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis
                dataKey="name"
                interval={0}
                angle={-30}
                textAnchor="end"
                height={60}
                tick={{ fontSize: 12 }}
              />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                itemStyle={{ color: "#f3f4f6" }}
              />
              <Legend />
              <Bar
                yAxisId="left"
                dataKey="avgLatency"
                name="Ort. Süre (ms)"
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                yAxisId="right"
                dataKey="successRate"
                name="Başarı Oranı (%)"
                fill="#10b981"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}
