"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChevronDown, ChevronRight, Search, Filter } from "lucide-react"
import { getUserActivity, type QuizAttempt } from "@/lib/api"

interface UserActivityTableProps {
  token: string
}

export function UserActivityTable({ token }: UserActivityTableProps) {
  const [attempts, setAttempts] = useState<QuizAttempt[]>([])
  const [filteredAttempts, setFilteredAttempts] = useState<QuizAttempt[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Filters
  const [searchQuery, setSearchQuery] = useState("")
  const [topicFilter, setTopicFilter] = useState<string>("all")
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all")

  useEffect(() => {
    loadActivity()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [attempts, searchQuery, topicFilter, difficultyFilter])

  const loadActivity = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await getUserActivity(token)
      setAttempts(data)
    } catch (error) {
      setError(error instanceof Error ? error.message : "Veri yüklenirken hata oluştu")
    } finally {
      setIsLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...attempts]
    if (searchQuery) {
      filtered = filtered.filter((a) => a.username.toLowerCase().includes(searchQuery.toLowerCase()))
    }
    if (topicFilter !== "all") filtered = filtered.filter((a) => a.topic === topicFilter)
    if (difficultyFilter !== "all") filtered = filtered.filter((a) => a.difficulty === difficultyFilter)
    setFilteredAttempts(filtered)
  }

  const toggleRow = (id: string) => {
    const next = new Set(expandedRows)
    next.has(id) ? next.delete(id) : next.add(id)
    setExpandedRows(next)
  }

  const getUniqueTopics = () => Array.from(new Set(attempts.map((a) => a.topic)))

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "-"
    const normalized = dateString.includes("T") ? dateString : dateString.replace(" ", "T")
    const d = new Date(normalized)
    if (Number.isNaN(d.getTime())) return dateString
    return d.toLocaleString("tr-TR", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const getScoreColor = (percentage: number) => {
    if (percentage >= 80) return "text-green-600 dark:text-green-400"
    if (percentage >= 60) return "text-yellow-600 dark:text-yellow-400"
    return "text-red-600 dark:text-red-400"
  }

  const getQuestionsForAttempt = (attempt: QuizAttempt) => {
    const raw = (attempt as any).questions_attempted
    if (Array.isArray(raw)) return raw
    if (typeof raw === "string") {
      try {
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    }
    return []
  }

  if (isLoading) {
    return (
      <Card className="p-6">
        <p className="text-center text-muted-foreground">Yükleniyor...</p>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center space-y-2">
          <p className="text-red-600 dark:text-red-400">Hata: {error}</p>
          <Button onClick={loadActivity} variant="outline" size="sm">
            Tekrar Dene
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Kullanıcı ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={topicFilter} onValueChange={setTopicFilter}>
            <SelectTrigger className="w-full md:w-[180px]">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Konu" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tüm Konular</SelectItem>
              {getUniqueTopics().map((topic) => (
                <SelectItem key={topic} value={topic}>
                  {topic}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={difficultyFilter} onValueChange={setDifficultyFilter}>
            <SelectTrigger className="w-full md:w-[180px]">
              <SelectValue placeholder="Zorluk" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tüm Zorluklar</SelectItem>
              <SelectItem value="beginner">Başlangıç</SelectItem>
              <SelectItem value="intermediate">Orta</SelectItem>
              <SelectItem value="advanced">İleri</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]"></TableHead>
              <TableHead>Kullanıcı</TableHead>
              <TableHead>Tarih</TableHead>
              <TableHead>Konu</TableHead>
              <TableHead>Zorluk</TableHead>
              <TableHead>Skor</TableHead>
              <TableHead className="text-right">Yüzde</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAttempts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  {attempts.length === 0 ? (
                    <div className="space-y-2">
                      <p>Henüz quiz çözülmemiş</p>
                      <p className="text-xs">Kullanıcılar quiz çözdükçe burada görünecek</p>
                    </div>
                  ) : (
                    "Filtrelere uygun sonuç bulunamadı"
                  )}
                </TableCell>
              </TableRow>
            ) : (
              filteredAttempts.flatMap((attempt, idx) => {
                const rows: JSX.Element[] = []
                const rowId = String((attempt as any).id ?? (attempt as any).attempt_id ?? idx)
                const rawScore = attempt.score ?? 0
                const percentage = rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore)

                // Ana satır
                rows.push(
                  <TableRow
                    key={`row-${rowId}`}
                    className="cursor-pointer"
                    onClick={() => toggleRow(rowId)}
                  >
                    <TableCell>
                      <Button variant="ghost" size="icon" className="w-8 h-8">
                        {expandedRows.has(rowId) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-medium">{attempt.username}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(attempt.quiz_date)}
                    </TableCell>
                    <TableCell>{attempt.topic}</TableCell>
                    <TableCell className="capitalize">{attempt.difficulty}</TableCell>
                    <TableCell>
                      {attempt.correct_answers}/{attempt.total_questions}
                    </TableCell>
                    <TableCell className={`text-right font-semibold ${getScoreColor(percentage)}`}>
                      {percentage}%
                    </TableCell>
                  </TableRow>,
                )

                // Detay satırı
                if (expandedRows.has(rowId)) {
                  const questions = getQuestionsForAttempt(attempt)

                  rows.push(
                    <TableRow key={`detail-${rowId}`}>
                      <TableCell colSpan={7} className="bg-muted/50">
                        <div className="p-4 space-y-3">
                          <h4 className="font-semibold text-sm">Soru Detayları</h4>
                          <div className="space-y-2">
                            {questions.length === 0 ? (
                              <p className="text-xs text-muted-foreground">
                                Bu quiz için soru detay kaydı bulunmuyor.
                              </p>
                            ) : (
                              questions.map((q: any, qIdx: number) => {
                                const qKey = q.id ?? q.question_id ?? `${rowId}-${qIdx}`
                                return (
                                  <div
                                    key={qKey}
                                    className={`p-3 rounded-lg border ${
                                      q.is_correct
                                        ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900"
                                        : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900"
                                    }`}
                                  >
                                    <div className="flex items-start justify-between gap-2">
                                      <div className="flex-1">
                                        <p className="text-sm font-medium mb-1">Soru {qIdx + 1}</p>
                                        <p className="text-xs text-muted-foreground">
                                          Kullanıcı Cevabı:{" "}
                                          <span className="font-medium">{q.user_answer || "Boş"}</span>
                                        </p>
                                      </div>
                                      <div
                                        className={`text-xs font-semibold px-2 py-1 rounded ${
                                          q.is_correct
                                            ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300"
                                            : "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300"
                                        }`}
                                      >
                                        {q.is_correct ? "Doğru" : "Yanlış"}
                                      </div>
                                    </div>
                                  </div>
                                )
                              })
                            )}
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>,
                  )
                }

                return rows
              })
            )}
          </TableBody>
        </Table>
      </Card>

      <div className="text-sm text-muted-foreground text-center">
        Toplam {filteredAttempts.length} sonuç gösteriliyor
      </div>
    </div>
  )
}
