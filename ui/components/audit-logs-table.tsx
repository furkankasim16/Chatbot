"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2 } from "lucide-react"
import { getAuditLogs, AuditLog } from "@/lib/api"

export function AuditLogsTable({ token }: { token: string }) {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAuditLogs(token)
        setLogs(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Loglar yüklenemedi")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  if (loading)
    return (
      <Card className="p-6 flex justify-center items-center">
        <Loader2 className="w-6 h-6 animate-spin" />
      </Card>
    )

  if (error)
    return (
      <Card className="p-6 text-destructive">
        Loglar yüklenemedi: {error}
      </Card>
    )

  return (
    <Card className="p-6">
      <h3 className="text-xl font-semibold mb-4">Audit Logları</h3>

      <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
        {logs.map((log) => (
          <div
            key={log.id}
            className="border p-4 rounded-lg bg-muted hover:bg-muted/70 transition"
          >
            <div className="flex justify-between mb-2">
              <Badge variant="default">{log.action}</Badge>
              <span className="text-sm opacity-70">
                {new Date(log.created_at).toLocaleString()}
              </span>
            </div>

            <p className="text-sm">
              <strong>Kullanıcı:</strong>{" "}
              {log.username ? log.username : `#${log.user_id}`}
            </p>

            <details className="mt-2 bg-background p-2 rounded border cursor-pointer">
              <summary className="cursor-pointer text-sm font-medium">
                Detaylar
              </summary>
              <pre className="text-xs mt-2 whitespace-pre-wrap break-all">
                {JSON.stringify(log.details, null, 2)}
              </pre>
            </details>
          </div>
        ))}
      </div>
    </Card>
  )
}
