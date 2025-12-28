// app/components/admin-llm-stats.tsx
"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { AlertCircle, Brain, ArrowUpDown } from "lucide-react"
import { fetchLlmStatsSummary } from "@/lib/api"
import type { LlmStatsSummary } from "@/app/types/llm"

export function AdminLlmStats({ token }: { token: string }) {
  const [stats, setStats] = useState<LlmStatsSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const data = await fetchLlmStatsSummary(token)
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

  const handleSort = (key: string) => {
    let direction: "asc" | "desc" = "asc"
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc"
    }
    setSortConfig({ key, direction })
  }

  const sortedAndFilteredStats = (() => {
    if (!stats) return []

    let data = [...stats]

    // 1. Filtering
    if (searchTerm) {
      data = data.filter((s) => {
        const modelName = ((s as any).model ?? (s as any).model_name ?? "").toLowerCase()
        return modelName.includes(searchTerm.toLowerCase())
      })
    }

    // 2. Sorting
    if (sortConfig) {
      data.sort((a, b) => {
        const getValue = (item: any, key: string) => {
          if (key === "model") return (item.model ?? item.model_name ?? "").toLowerCase()
          if (key === "totalCalls") return (item.total_calls ?? item.count ?? 0)
          if (key === "successCalls") return (item.success_calls ?? item.success ?? 0)
          if (key === "successRate") {
            const t = (item.total_calls ?? item.count ?? 0)
            const s = (item.success_calls ?? item.success ?? 0)
            return t > 0 ? (s / t) : 0
          }
          if (key === "avgLatency") return (item.avg_latency_ms ?? item.avg_ms ?? 0)
          if (key === "avgScore") return (item.avg_score ?? 0)
          return 0
        }

        const valA = getValue(a, sortConfig.key)
        const valB = getValue(b, sortConfig.key)

        if (valA < valB) return sortConfig.direction === "asc" ? -1 : 1
        if (valA > valB) return sortConfig.direction === "asc" ? 1 : -1
        return 0
      })
    }

    return data
  })()

  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">LLM Performans Özeti</h3>
        </div>
        {!isLoading && !error && stats && stats.length > 0 && (
          <Input
            placeholder="Model ara..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-xs h-9 bg-background/50"
          />
        )}
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
        <div className="rounded-md border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => handleSort("model")}
                >
                  <div className="flex items-center gap-1">
                    Model {sortConfig?.key === "model" && <ArrowUpDown className="w-3 h-3" />}
                  </div>
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-muted/50 transition-colors text-right"
                  onClick={() => handleSort("totalCalls")}
                >
                  <div className="flex items-center justify-end gap-1">
                    Toplam Çağrı {sortConfig?.key === "totalCalls" && <ArrowUpDown className="w-3 h-3" />}
                  </div>
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-muted/50 transition-colors text-right"
                  onClick={() => handleSort("successCalls")}
                >
                  <div className="flex items-center justify-end gap-1">
                    Başarılı {sortConfig?.key === "successCalls" && <ArrowUpDown className="w-3 h-3" />}
                  </div>
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-muted/50 transition-colors text-right"
                  onClick={() => handleSort("successRate")}
                >
                  <div className="flex items-center justify-end gap-1">
                    Başarı Oranı {sortConfig?.key === "successRate" && <ArrowUpDown className="w-3 h-3" />}
                  </div>
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-muted/50 transition-colors text-right"
                  onClick={() => handleSort("avgLatency")}
                >
                  <div className="flex items-center justify-end gap-1">
                    Ort. Süre (ms) {sortConfig?.key === "avgLatency" && <ArrowUpDown className="w-3 h-3" />}
                  </div>
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-muted/50 transition-colors text-right"
                  onClick={() => handleSort("avgScore")}
                >
                  <div className="flex items-center justify-end gap-1">
                    Ort. Skor {sortConfig?.key === "avgScore" && <ArrowUpDown className="w-3 h-3" />}
                  </div>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedAndFilteredStats.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                    Sonuç bulunamadı.
                  </TableCell>
                </TableRow>
              ) : (
                sortedAndFilteredStats.map((s, idx) => {
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
                      <TableCell className="text-right">{totalCalls}</TableCell>
                      <TableCell className="text-right">{successCalls}</TableCell>
                      <TableCell className="text-right">{successRate}%</TableCell>
                      <TableCell className="text-right">{Math.round(avgLatency)}</TableCell>
                      <TableCell className="text-right">{avgScore != null ? avgScore.toFixed(2) : "—"}</TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  )
}
