"use client"

import { useEffect, useMemo, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getAllQuestions, deleteQuestion, type Question } from "@/lib/api"
import {
  Loader2,
  Trash2,
  Filter,
  ChevronDown,
  ChevronRight,
} from "lucide-react"

interface AdminQuestionBankProps {
  token: string
}

type FilterColumn = "topic" | "level" | "type" | "stem" | null

export function AdminQuestionBank({ token }: AdminQuestionBankProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [filterColumn, setFilterColumn] = useState<FilterColumn>(null)
  const [filterValue, setFilterValue] = useState("")

  const [deletingId, setDeletingId] = useState<string | null>(null)

  // ── DATA LOAD ───────────────────────────────────────────────
  useEffect(() => {
    ;(async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await getAllQuestions()
        setQuestions(data)
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Soru bankası yüklenemedi",
        )
      } finally {
        setIsLoading(false)
      }
    })()
  }, [])

  // ── FILTERED DATA ──────────────────────────────────────────
  const filteredQuestions = useMemo(() => {
    if (!filterColumn || !filterValue.trim()) return questions
    const q = filterValue.toLowerCase()

    return questions.filter((item) => {
      if (filterColumn === "topic") {
        return (item.topic || "").toLowerCase().includes(q)
      }
      if (filterColumn === "level") {
        return (item.level || "").toLowerCase().includes(q)
      }
      if (filterColumn === "type") {
        return (String(item.type) || "").toLowerCase().includes(q)
      }
      if (filterColumn === "stem") {
        return (item.stem || "").toLowerCase().includes(q)
      }
      return true
    })
  }, [questions, filterColumn, filterValue])

  // ── HELPERS ────────────────────────────────────────────────
  const toggleRow = (id: string) => {
    const next = new Set(expandedRows)
    next.has(id) ? next.delete(id) : next.add(id)
    setExpandedRows(next)
  }

  const handleHeaderClick = (col: FilterColumn) => {
    if (filterColumn === col) {
      // aynı kolona tekrar basınca kapat
      setFilterColumn(null)
      setFilterValue("")
    } else {
      setFilterColumn(col)
      setFilterValue("")
    }
  }

  const getFilterPlaceholder = () => {
    switch (filterColumn) {
      case "topic":
        return "Konuya göre ara..."
      case "level":
        return "Zorluk seviyesine göre ara..."
      case "type":
        return "Soru tipine göre ara..."
      case "stem":
        return "Soru metninde ara..."
      default:
        return ""
    }
  }

  const formatType = (t: Question["type"]) => {
    switch (t) {
      case "mcq":
        return "Çoktan Seçmeli"
      case "true_false":
        return "Doğru / Yanlış"
      case "short_answer":
      case "short":
        return "Kısa Cevap"
      case "open_ended":
      case "open":
        return "Açık Uçlu"
      case "scenario":
      case "senaryo":
        return "Senaryo"
      default:
        return String(t)
    }
  }

  const handleDelete = async (q: Question) => {
    if (!q.id) return
    if (!confirm("Bu soruyu silmek istediğinize emin misiniz?")) return

    setDeletingId(String(q.id))
    setError(null)
    try {
      await deleteQuestion(token, String(q.id))
      setQuestions((prev) => prev.filter((item) => item.id !== q.id))
      setExpandedRows((prev) => {
        const next = new Set(prev)
        next.delete(String(q.id))
        return next
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Soru silinemedi")
    } finally {
      setDeletingId(null)
    }
  }

  // ── RENDER ─────────────────────────────────────────────────
  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Soru bankası yükleniyor...</span>
        </div>
      </Card>
    )
  }

  if (error && questions.length === 0) {
    return (
      <Card className="p-6 space-y-2">
        <p className="text-red-600 dark:text-red-400 text-sm">
          Hata: {error}
        </p>
        <p className="text-xs text-muted-foreground">
          Backend&apos;de /questions endpoint&apos;ini kontrol edin.
        </p>
      </Card>
    )
  }

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Soru Bankası</h3>
          <p className="text-xs text-muted-foreground">
            Satıra tıklayarak detayları açabilirsiniz. Filtre için sütun başlığına tıklayın.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          Toplam {filteredQuestions.length} soru
        </p>
      </div>

      {error && questions.length > 0 && (
        <div className="text-xs text-red-500">{error}</div>
      )}

      <div className="border rounded-md overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]" />
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => handleHeaderClick("topic")}
              >
                <div className="flex items-center gap-1">
                  Konu
                  <Filter
                    className={`w-3 h-3 ${
                      filterColumn === "topic"
                        ? "text-primary"
                        : "text-muted-foreground"
                    }`}
                  />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => handleHeaderClick("type")}
              >
                <div className="flex items-center gap-1">
                  Tip
                  <Filter
                    className={`w-3 h-3 ${
                      filterColumn === "type"
                        ? "text-primary"
                        : "text-muted-foreground"
                    }`}
                  />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => handleHeaderClick("level")}
              >
                <div className="flex items-center gap-1">
                  Zorluk
                  <Filter
                    className={`w-3 h-3 ${
                      filterColumn === "level"
                        ? "text-primary"
                        : "text-muted-foreground"
                    }`}
                  />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => handleHeaderClick("stem")}
              >
                <div className="flex items-center gap-1">
                  Soru
                  <Filter
                    className={`w-3 h-3 ${
                      filterColumn === "stem"
                        ? "text-primary"
                        : "text-muted-foreground"
                    }`}
                  />
                </div>
              </TableHead>
            </TableRow>

            {filterColumn && (
              <TableRow>
                <TableHead colSpan={5}>
                  <div className="flex items-center gap-2">
                    <Input
                      autoFocus
                      value={filterValue}
                      onChange={(e) => setFilterValue(e.target.value)}
                      placeholder={getFilterPlaceholder()}
                      className="h-8 text-xs"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setFilterColumn(null)
                        setFilterValue("")
                      }}
                    >
                      Temizle
                    </Button>
                  </div>
                </TableHead>
              </TableRow>
            )}
          </TableHeader>

          <TableBody>
            {filteredQuestions.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="py-6 text-center text-muted-foreground text-sm"
                >
                  Filtrelere uygun soru bulunamadı
                </TableCell>
              </TableRow>
            ) : (
              filteredQuestions.flatMap((q, idx) => {
                const rowId = String(q.id ?? idx)
                const isExpanded = expandedRows.has(rowId)

                const mainRow = (
                  <TableRow
                    key={`row-${rowId}`}
                    className="cursor-pointer hover:bg-muted/40"
                    onClick={() => toggleRow(rowId)}
                  >
                    <TableCell className="w-[40px]">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="w-7 h-7"
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleRow(rowId)
                        }}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="text-xs">
                      {q.topic || "—"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {formatType(q.type)}
                    </TableCell>
                    <TableCell className="text-xs">
                      {q.level || "—"}
                    </TableCell>
                    <TableCell className="text-sm max-w-[320px] truncate">
                      {q.stem}
                    </TableCell>
                  </TableRow>
                )

                if (!isExpanded) return [mainRow]

                const detailRow = (
                  <TableRow key={`detail-${rowId}`}>
                    <TableCell colSpan={5} className="bg-muted/40">
                      <div className="p-4 space-y-3 text-xs md:text-sm">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-[11px] text-muted-foreground">
                              ID: {q.id ?? "—"}
                            </p>
                            <p className="font-semibold mb-1">
                              {q.stem}
                            </p>
                          </div>
                          <Button
                            variant="outline"
                            size="icon"
                            disabled={!q.id || deletingId === String(q.id)}
                            onClick={() => handleDelete(q)}
                            title="Bu soruyu sil"
                          >
                            {deletingId === String(q.id) ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4 text-destructive" />
                            )}
                          </Button>
                        </div>

                        <div className="grid gap-2 md:grid-cols-3 text-[11px] text-muted-foreground">
                          <p>
                            <span className="font-medium">Konu:</span>{" "}
                            {q.topic || "—"}
                          </p>
                          <p>
                            <span className="font-medium">Zorluk:</span>{" "}
                            {q.level || "—"}
                          </p>
                          <p>
                            <span className="font-medium">Tip:</span>{" "}
                            {formatType(q.type)}
                          </p>
                        </div>

                        {q.choices && q.choices.length > 0 && (
                          <div className="space-y-1">
                            <p className="font-medium text-xs">
                              Seçenekler
                            </p>
                            <ul className="list-disc list-inside space-y-1 text-xs md:text-sm">
                              {q.choices.map((opt, i) => (
                                <li key={i}>{opt}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {q.rationale && (
                          <div className="space-y-1">
                            <p className="font-medium text-xs">
                              Açıklama
                            </p>
                            <p className="text-xs md:text-sm text-muted-foreground whitespace-pre-line">
                              {q.rationale}
                            </p>
                          </div>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )

                return [mainRow, detailRow]
              })
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  )
}
