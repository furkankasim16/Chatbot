// app/components/admin-llm-stats.tsx
"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AlertCircle, Brain } from "lucide-react"
import { fetchLlmStatsSummary } from "@/lib/api"
import type { LlmStatsSummary } from "@/app/types/llm"

export function AdminLlmStats() {
  const [stats, setStats] = useState<LlmStatsSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const data = await fetchLlmStatsSummary()
        if (cancelled) return
        setStats(data)
      } catch (err) {
        if (cancelled) return
        console.error("[AdminLlmStats] fetch error:", err)
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">LLM Performans Özeti</h3>
        </div>
      </div>

      {isLoading && (
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          Veriler yükleniyor…
        </p>
      )}

      {!isLoading && error && (
        <div className="flex items-start gap-2 text-sm text-red-400 bg-red-950/30 border border-red-800 rounded-md p-3">
          <AlertCircle className="w-4 h-4 mt-0.5" />
          <div>
            <p className="font-medium">Veriler alınırken hata oluştu</p>
            <p className="text-xs opacity-80">{error}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && (!stats || stats.length === 0) && (
        <p className="text-sm text-muted-foreground">
          Henüz LLM ile üretilmiş soru kaydı bulunmuyor.
        </p>
      )}

      {!isLoading && !error && stats && stats.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Model</TableHead>
              <TableHead>Toplam Çağrı</TableHead>
              <TableHead>Başarılı</TableHead>
              <TableHead>Başarı Oranı</TableHead>
              <TableHead>Ortalama Süre (ms)</TableHead>
              <TableHead>Ort. Skor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stats.map((s, idx) => {
              // type alan isimleri senin type’ına göre değişebilir,
              // o yüzden olabildiğince esnek okuyoruz
              const totalCalls = (s as any).total_calls ?? (s as any).count ?? 0
              const successCalls = (s as any).success_calls ?? (s as any).success ?? 0
              const successRate =
                totalCalls > 0 ? Math.round((successCalls / totalCalls) * 100) : 0
              const avgLatency = (s as any).avg_latency_ms ?? (s as any).avg_ms ?? 0
              const avgScore = (s as any).avg_score ?? null

              return (
                <TableRow key={idx}>
                  <TableCell className="font-medium">
                    {(s as any).model ?? (s as any).model_name ?? "-"}
                  </TableCell>
                  <TableCell>{totalCalls}</TableCell>
                  <TableCell>{successCalls}</TableCell>
                  <TableCell>{successRate}%</TableCell>
                  <TableCell>{Math.round(avgLatency)}</TableCell>
                  <TableCell>{avgScore != null ? avgScore.toFixed(2) : "—"}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}
    </Card>
  )
}
