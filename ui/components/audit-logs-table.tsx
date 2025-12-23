"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2 } from "lucide-react"
import { getAuditLogs, AuditLog } from "@/lib/api"
import { AuditCharts } from "@/components/audit-charts"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Eye } from "lucide-react"

export function AuditLogsTable({ token }: { token: string }) {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)

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
    <div className="space-y-6">
      <AuditCharts token={token} />

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold">Audit Logları</h3>
          <span className="text-sm text-muted-foreground">Toplam: {logs.length}</span>
        </div>

        <div className="rounded-md border max-h-[600px] overflow-y-auto">
          <Table>
            <TableHeader className="bg-muted/50 sticky top-0">
              <TableRow>
                <TableHead className="w-[180px]">Tarih</TableHead>
                <TableHead>Kullanıcı</TableHead>
                <TableHead>Aksiyon</TableHead>
                <TableHead className="w-[100px] text-right">Detaylar</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs">
                    {new Date(log.created_at).toLocaleString("tr-TR")}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium text-sm">{log.username || "Bilinmiyor"}</span>
                      <span className="text-xs text-muted-foreground">ID: {log.user_id}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {log.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedLog(log)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                          <DialogTitle>Log Detayı</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-4 text-sm border-b pb-4">
                            <div>
                              <span className="text-muted-foreground">Tarih:</span>
                              <div className="font-semibold">{new Date(log.created_at).toLocaleString("tr-TR")}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Aksiyon:</span>
                              <div className="font-mono">{log.action}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Kullanıcı:</span>
                              <div>{log.username} (#{log.user_id})</div>
                            </div>
                          </div>
                          <div className="space-y-2">
                            <h4 className="font-semibold text-sm">Detaylar (JSON):</h4>
                            <LogDetailsRenderer details={log.details} />
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  )
}

function LogDetailsRenderer({ details }: { details: any }) {
  let parsedDetails = details

  // Try parsing if string
  if (typeof details === "string") {
    try {
      parsedDetails = JSON.parse(details)
      // Double parse check
      if (typeof parsedDetails === "string" && (parsedDetails.startsWith("{") || parsedDetails.startsWith("["))) {
        try { parsedDetails = JSON.parse(parsedDetails) } catch { }
      }
    } catch { }
  }

  if (!parsedDetails || (typeof parsedDetails === 'object' && Object.keys(parsedDetails).length === 0)) {
    return <div className="text-muted-foreground text-sm italic">Detay yok.</div>
  }

  return (
    <div className="bg-muted p-4 rounded-md text-sm overflow-x-auto">
      {typeof parsedDetails === 'object' ? (
        <div className="space-y-2">
          {Object.entries(parsedDetails).map(([key, val]) => (
            <div key={key} className="grid grid-cols-[120px_1fr] gap-2 border-b border-muted-foreground/10 last:border-0 pb-2 last:pb-0">
              <span className="font-semibold text-muted-foreground capitalize text-xs">
                {key.replace(/_/g, " ")}
              </span>
              <div className="text-xs break-all">
                {renderValue(key, val)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <pre className="whitespace-pre-wrap break-all">{String(parsedDetails)}</pre>
      )}
    </div>
  )
}

function renderValue(key: string, val: any): React.ReactNode {
  if (val === null || val === undefined) return <span className="text-muted-foreground">-</span>

  // Handle questions_attempted specifically
  if (key === "questions_attempted") {
    let questions = val
    if (typeof val === "string") {
      try {
        questions = JSON.parse(val)
      } catch {
        return <span className="text-xs break-all">{val}</span>
      }
    }

    if (Array.isArray(questions)) {
      return (
        <div className="mt-2 space-y-2 w-full">
          {questions.map((q: any, i: number) => (
            <div key={i} className="border p-2 rounded text-xs bg-background/50">
              <div className="font-semibold mb-1">{q.stem || q.question}</div>
              <div className="flex flex-wrap gap-2 items-center">
                <Badge variant={q.is_correct ? "default" : "destructive"} className="h-5 px-1.5">
                  {q.is_correct ? "D" : "Y"}
                </Badge>
                <span className="text-muted-foreground">Cevap:</span>
                <span className="font-medium">{Array.isArray(q.user_answer) ? q.user_answer.join(", ") : String(q.user_answer)}</span>
                {q.eval_score && (
                  <span className="text-muted-foreground ml-2">
                    Puan: <span className="font-bold text-foreground">{q.eval_score}</span>
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )
    }
  }

  if (key === "score") {
    const num = Number(val)
    const color = num >= 4 ? "text-green-600" : num >= 2.5 ? "text-yellow-600" : "text-red-600"
    return <span className={`font-bold ${color}`}>{val}</span>
  }

  if (key === "is_correct") {
    return val ? (
      <Badge className="bg-green-500 hover:bg-green-600 h-5 px-2">Doğru</Badge>
    ) : (
      <Badge variant="destructive" className="h-5 px-2">Yanlış</Badge>
    )
  }

  if (["topic", "difficulty", "level", "qtype", "model"].includes(key)) {
    return <Badge variant="secondary" className="h-5">{String(val)}</Badge>
  }

  if (typeof val === "boolean") {
    return val ? "Evet" : "Hayır"
  }

  if (typeof val === "object") {
    return <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(val, null, 2)}</pre>
  }

  return String(val)
}
