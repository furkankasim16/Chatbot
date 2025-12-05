"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Search,
  Filter,
  Clock,
  Sparkles,
  CheckCircle2,
  XCircle,
  Eye,
} from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { getUserActivity, type QuizAttempt } from "@/lib/api"

interface UserActivityTableProps {
  token: string
}

export function UserActivityTable({ token }: UserActivityTableProps) {
  const [attempts, setAttempts] = useState<QuizAttempt[]>([])
  const [filteredAttempts, setFilteredAttempts] = useState<QuizAttempt[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState("")
  const [topicFilter, setTopicFilter] = useState<string>("all")
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all")

  // 🔍 Detay modal state
  const [selectedAttempt, setSelectedAttempt] = useState<QuizAttempt | null>(null)
  const [selectedQuestions, setSelectedQuestions] = useState<any[] | null>(null)

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
      setError(
        error instanceof Error
          ? error.message
          : "Veri yüklenirken hata oluştu",
      )
    } finally {
      setIsLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...attempts]

    if (searchQuery) {
      filtered = filtered.filter((a) =>
        a.username.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    }

    if (topicFilter !== "all") {
      filtered = filtered.filter((a) => a.topic === topicFilter)
    }

    if (difficultyFilter !== "all") {
      filtered = filtered.filter((a) => a.difficulty === difficultyFilter)
    }

    setFilteredAttempts(filtered)
  }

  const getUniqueTopics = () =>
    Array.from(new Set(attempts.map((a) => a.topic).filter(Boolean))) as string[]

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "-"
    const normalized = dateString.includes("T")
      ? dateString
      : dateString.replace(" ", "T")
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

  const formatDuration = (ms?: number | null) => {
    if (!ms || ms <= 0) return "—"
    const totalSeconds = Math.round(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes === 0) return `${seconds}s`
    return `${minutes}dk ${seconds.toString().padStart(2, "0")}sn`
  }

  const formatTopic = (topic?: string | null) => {
    if (!topic) return "-"
    return topic
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  }

  const getScoreColor = (percentage: number) => {
    if (percentage >= 80) return "text-green-600 dark:text-green-400"
    if (percentage >= 60) return "text-yellow-600 dark:text-yellow-400"
    return "text-red-600 dark:text-red-400"
  }

  const getDifficultyBadgeClasses = (difficulty?: string | null) => {
    switch (difficulty) {
      case "beginner":
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/40"
      case "intermediate":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/40"
      case "advanced":
        return "bg-red-500/10 text-red-400 border border-red-500/40"
      default:
        return "bg-muted text-muted-foreground border border-border/40"
    }
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

  const openDetail = (attempt: QuizAttempt) => {
    setSelectedAttempt(attempt)
    setSelectedQuestions(getQuestionsForAttempt(attempt))
  }

  const closeDetail = () => {
    setSelectedAttempt(null)
    setSelectedQuestions(null)
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
            <SelectTrigger className="w-full md:w-[200px]">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Konu" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tüm Konular</SelectItem>
              {getUniqueTopics().map((topic) => (
                <SelectItem key={topic} value={topic}>
                  {formatTopic(topic)}
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
              <TableHead className="w-[50px]" />
              <TableHead>Kullanıcı</TableHead>
              <TableHead>Tarih</TableHead>
              <TableHead>Konu</TableHead>
              <TableHead>Zorluk</TableHead>
              <TableHead>Skor</TableHead>
              <TableHead>Süre</TableHead>
              <TableHead className="text-right">Yüzde</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAttempts.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground py-8"
                >
                  {attempts.length === 0 ? (
                    <div className="space-y-2">
                      <p>Henüz quiz çözülmemiş</p>
                      <p className="text-xs">
                        Kullanıcılar quiz çözdükçe burada görünecek
                      </p>
                    </div>
                  ) : (
                    "Filtrelere uygun sonuç bulunamadı"
                  )}
                </TableCell>
              </TableRow>
            ) : (
              filteredAttempts.map((attempt, idx) => {
                const rowId =
                  (attempt as any).id ??
                  (attempt as any).attempt_id ??
                  idx
                const rawScore = attempt.score ?? 0
                const percentage =
                  rawScore <= 1
                    ? Math.round(rawScore * 100)
                    : Math.round(rawScore)

                const durationMs =
                  (attempt as any).total_duration_ms ??
                  (attempt as any).duration_ms ??
                  (attempt as any).quiz_duration_ms ??
                  null

                return (
                  <TableRow key={rowId} className="hover:bg-muted/40">
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="w-8 h-8"
                        aria-label="Detayları görüntüle"
                        onClick={() => openDetail(attempt)}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                    </TableCell>

                    <TableCell className="font-medium">
                      {attempt.username}
                    </TableCell>

                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(attempt.quiz_date)}
                    </TableCell>

                    <TableCell>
                      <span className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs">
                        {formatTopic(attempt.topic)}
                      </span>
                    </TableCell>

                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${getDifficultyBadgeClasses(
                          attempt.difficulty,
                        )}`}
                      >
                        {attempt.difficulty ?? "-"}
                      </span>
                    </TableCell>

                    <TableCell>
                      <span className="text-sm font-medium">
                        {attempt.correct_answers}/{attempt.total_questions}
                      </span>
                    </TableCell>

                    <TableCell className="text-sm text-muted-foreground">
                      <div className="inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDuration(durationMs)}
                      </div>
                    </TableCell>

                    <TableCell
                      className={`text-right font-semibold ${getScoreColor(
                        percentage,
                      )}`}
                    >
                      {percentage}%
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </Card>

      <div className="text-sm text-muted-foreground text-center">
        Toplam {filteredAttempts.length} sonuç gösteriliyor
      </div>

      {/* 🔍 Detay modalı */}
      <Dialog open={!!selectedAttempt} onOpenChange={(open) => !open && closeDetail()}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          {selectedAttempt && (
            <>
              <DialogHeader>
                <DialogTitle className="flex flex-col gap-1">
                  <span className="text-base text-muted-foreground">
                    {selectedAttempt.username}
                  </span>
                  <span className="text-lg font-semibold">
                    {formatTopic(selectedAttempt.topic)} –{" "}
                    {selectedAttempt.difficulty ?? "-"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(selectedAttempt.quiz_date)}
                  </span>
                </DialogTitle>
              </DialogHeader>

              <div className="grid gap-4 md:grid-cols-3 mt-2 mb-4">
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Skor</p>
                  <p className="text-lg font-semibold">
                    {selectedAttempt.correct_answers}/
                    {selectedAttempt.total_questions}
                  </p>
                </Card>
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Yüzde</p>
                  <p
                    className={`text-lg font-semibold ${getScoreColor(
                      selectedAttempt.score ?? 0,
                    )}`}
                  >
                    {selectedAttempt.score ?? 0}%
                  </p>
                </Card>
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Toplam Süre</p>
                  <p className="text-lg font-semibold">
                    {formatDuration(
                      (selectedAttempt as any).total_duration_ms ??
                        (selectedAttempt as any).duration_ms ??
                        (selectedAttempt as any).quiz_duration_ms ??
                        null,
                    )}
                  </p>
                </Card>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Sparkles className="w-3 h-3" />
                  AI değerlendirmeli sorular işaretlenir.
                </div>

                <div className="space-y-2">
                  {(!selectedQuestions || selectedQuestions.length === 0) ? (
                    <p className="text-xs text-muted-foreground">
                      Bu quiz için soru detay kaydı bulunmuyor.
                    </p>
                  ) : (
                    selectedQuestions.map((q: any, qIdx: number) => {
                      const questionId =
                        q.id ?? q.question_id ?? `${selectedAttempt.id}-${qIdx}`

                      const isCorrect = Boolean(q.is_correct)
                      const stem =
                        q.stem || q.question || `Soru ${qIdx + 1}`

                      const userAnswer = Array.isArray(q.user_answer)
                        ? q.user_answer.join(", ")
                        : q.user_answer || "Boş"

                      const correctAnswer = Array.isArray(q.correct_answer)
                        ? q.correct_answer.join(", ")
                        : q.correct_answer || "—"

                      return (
                        <Card
                          key={questionId}
                          className={`p-3 space-y-2 border ${
                            isCorrect
                              ? "border-emerald-300/60 dark:border-emerald-900 bg-emerald-50/70 dark:bg-emerald-950/10"
                              : "border-red-300/60 dark:border-red-900 bg-red-50/70 dark:bg-red-950/10"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <p className="text-xs font-semibold mb-1">
                                Soru {qIdx + 1}
                              </p>
                              <p className="text-xs md:text-sm mb-1">
                                {stem}
                              </p>
                            </div>
                            <div
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                                isCorrect
                                  ? "bg-emerald-600 text-white"
                                  : "bg-red-600 text-white"
                              }`}
                            >
                              {isCorrect ? (
                                <CheckCircle2 className="w-3 h-3" />
                              ) : (
                                <XCircle className="w-3 h-3" />
                              )}
                              {isCorrect ? "Doğru" : "Yanlış"}
                            </div>
                          </div>

                          <p className="text-[11px] text-muted-foreground">
                            <span className="font-medium">
                              Senin cevabın:
                            </span>{" "}
                            <span className="text-foreground">
                              {userAnswer}
                            </span>
                          </p>

                          <p className="text-[11px] text-muted-foreground">
                            <span className="font-medium">
                              Doğru cevap:
                            </span>{" "}
                            <span className="text-foreground">
                              {correctAnswer}
                            </span>
                          </p>

                          {(q.eval_score || q.eval_feedback) && (
                            <div className="mt-1 p-2 rounded-md bg-primary/5 border border-primary/20">
                              <div className="flex items-center gap-2 mb-1">
                                <Sparkles className="w-3 h-3 text-primary" />
                                <span className="text-[11px] font-semibold text-primary">
                                  AI Değerlendirmesi
                                </span>
                                {typeof q.eval_score === "number" && (
                                  <span className="ml-auto text-[11px] px-2 py-0.5 rounded-full border border-primary/30">
                                    Skor: {q.eval_score}/5
                                  </span>
                                )}
                              </div>
                              {q.eval_feedback && (
                                <p className="text-[11px] text-muted-foreground leading-relaxed">
                                  {q.eval_feedback}
                                </p>
                              )}
                            </div>
                          )}
                        </Card>
                      )
                    })
                  )}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
