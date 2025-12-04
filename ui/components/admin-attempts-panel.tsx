"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  User,
  Clock,
  CheckCircle2,
  XCircle,
  Percent,
  Filter,
  Sparkles,
} from "lucide-react"

interface AdminQuestionAttempt {
  question_id: string
  stem: string
  user_answer: string | string[] | null
  correct_answer: string | string[] | null
  is_correct: boolean
  eval_score?: number | null
  eval_feedback?: string | null
}

interface AdminQuizAttempt {
  id: number
  user_id: number
  username?: string | null
  topic?: string | null
  difficulty?: string | null
  total_questions: number
  correct_answers?: number | null
  score?: number | null
  quiz_date: string
  start_time?: string | null
  end_time?: string | null
  total_duration_ms?: number | null
}

interface AdminQuizAttemptDetail extends AdminQuizAttempt {
  questions: AdminQuestionAttempt[]
}

interface AdminAttemptsPanelProps {
  token: string
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"

export function AdminAttemptsPanel({ token }: AdminAttemptsPanelProps) {
  const [attempts, setAttempts] = useState<AdminQuizAttempt[]>([])
  const [details, setDetails] = useState<Record<number, AdminQuizAttemptDetail>>(
    {},
  )
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const [userIdFilter, setUserIdFilter] = useState<string>("")
  const [topicFilter, setTopicFilter] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showOnlyIncorrect, setShowOnlyIncorrect] = useState(false)

  const fetchAttempts = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (userIdFilter.trim()) params.append("user_id", userIdFilter.trim())
      if (topicFilter.trim()) params.append("topic", topicFilter.trim())
      params.append("limit", "50")

      const res = await fetch(
        `${API_BASE_URL}/admin/quiz/attempts?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      )

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data: AdminQuizAttempt[] = await res.json()
      setAttempts(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Quiz attempt'lar alınırken bir hata oluştu.",
      )
    } finally {
      setIsLoading(false)
    }
  }

  const fetchDetail = async (id: number) => {
    if (details[id]) return
    try {
      const res = await fetch(`${API_BASE_URL}/admin/quiz/attempts/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data: AdminQuizAttemptDetail = await res.json()
      setDetails((prev) => ({ ...prev, [id]: data }))
    } catch (err) {
      console.error("[admin] get detail failed", err)
    }
  }

  useEffect(() => {
    fetchAttempts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const toggleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    await fetchDetail(id)
    setExpandedId(id)
  }

  const formatDuration = (ms?: number | null) => {
    if (!ms || ms <= 0) return "—"
    const sec = Math.round(ms / 1000)
    if (sec < 60) return `${sec} sn`
    const min = Math.floor(sec / 60)
    const s = sec % 60
    return `${min} dk ${s}s`
  }

  const formatDateTime = (dt: string | null | undefined) => {
    if (!dt) return ""
    const d = new Date(dt)
    return d.toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const formatTopic = (topic?: string | null) => {
    if (!topic) return "—"
    return topic
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  }

  const getAccuracyLabel = (a: AdminQuizAttempt) => {
    const total = a.total_questions || 0
    const correct = a.correct_answers ?? 0
    if (!total) return "0%"
    const pct = Math.round((correct / total) * 100)
    return `${pct}%`
  }

  return (
    <div className="space-y-4">
      <Card className="p-4 flex items-center justify-between">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-primary/10 text-primary">
              ✓
            </span>
            Quiz Attempt Viewer
          </h3>
          <p className="text-xs text-muted-foreground">
            Kullanıcıların çözdüğü quiz denemelerini, verilen cevapları ve AI
            değerlendirmelerini inceleyin.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={fetchAttempts}
          disabled={isLoading}
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          Yenile
        </Button>
      </Card>

      {/* Filtreler */}
      <Card className="p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1 space-y-1">
            <Label htmlFor="user-id">User ID</Label>
            <Input
              id="user-id"
              placeholder="Örn: 1"
              value={userIdFilter}
              onChange={(e) => setUserIdFilter(e.target.value)}
            />
          </div>
          <div className="flex-1 space-y-1">
            <Label htmlFor="topic">Topic</Label>
            <Input
              id="topic"
              placeholder="product_basics"
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
            />
          </div>
        </div>
        <div className="flex items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Filter className="w-3 h-3" />
            <span>Filtre uygulayarak belirli kullanıcı veya konuya odaklanın</span>
          </div>
          <Button
            size="sm"
            onClick={fetchAttempts}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <Search className="w-4 h-4" />
            Filtrele
          </Button>
        </div>
      </Card>

      {error && (
        <Card className="p-3 border-destructive/40 bg-destructive/10 text-sm text-destructive">
          {error}
        </Card>
      )}

      {/* Global seçenek: sadece yanlış soruları göster */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          Toplam {attempts.length} attempt listelendi.
        </div>
        <Button
          size="sm"
          variant={showOnlyIncorrect ? "default" : "outline"}
          className="flex items-center gap-1"
          onClick={() => setShowOnlyIncorrect((p) => !p)}
        >
          <XCircle className="w-3 h-3" />
          <span className="text-xs">
            {showOnlyIncorrect
              ? "Tüm soruları göster"
              : "Sadece yanlış soruları göster"}
          </span>
        </Button>
      </div>

      {/* Attempt list */}
      <div className="space-y-3">
        {attempts.map((a) => {
          const isExpanded = expandedId === a.id
          const detail = details[a.id]

          return (
            <Card key={a.id} className="p-3 md:p-4 space-y-3">
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold px-2 py-1 rounded bg-muted">
                    #{a.id}
                  </span>
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-sm font-medium">
                        {a.username ?? `User ${a.user_id}`}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {a.topic && (
                        <Badge variant="outline" className="text-xs">
                          {formatTopic(a.topic)}
                        </Badge>
                      )}
                      {a.difficulty && (
                        <Badge variant="outline" className="text-xs">
                          {a.difficulty}
                        </Badge>
                      )}
                      <Badge
                        variant="outline"
                        className="text-xs flex items-center gap-1"
                      >
                        <Percent className="w-3 h-3" />
                        {getAccuracyLabel(a)}
                      </Badge>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 justify-between md:justify-end">
                  <div className="flex flex-col items-end text-xs text-muted-foreground">
                    <span>{formatDateTime(a.start_time ?? a.quiz_date)}</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDuration(a.total_duration_ms)}
                    </span>
                  </div>
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={() => toggleExpand(a.id)}
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Detail */}
              {isExpanded && detail && (
                <div className="pt-3 border-t border-border/60 space-y-3">
                  {detail.questions
                    .filter((q) => (showOnlyIncorrect ? !q.is_correct : true))
                    .map((q, idx) => {
                      const userAnswer = Array.isArray(q.user_answer)
                        ? q.user_answer.join(", ")
                        : q.user_answer ?? ""
                      const correctAnswer = Array.isArray(q.correct_answer)
                        ? q.correct_answer.join(", ")
                        : q.correct_answer ?? ""

                      return (
                        <div
                          key={`${q.question_id}-${idx}`}
                          className={`p-3 rounded-md border text-sm space-y-2 ${
                            q.is_correct
                              ? "border-emerald-500/40 bg-emerald-500/5"
                              : "border-destructive/40 bg-destructive/5"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <p className="font-medium text-card-foreground">
                              {q.stem}
                            </p>
                            {q.is_correct ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                            ) : (
                              <XCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                            )}
                          </div>

                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">
                              Senin cevabın:
                            </p>
                            <p className="text-xs md:text-sm text-card-foreground">
                              {userAnswer || "—"}
                            </p>
                          </div>

                          {correctAnswer && (
                            <div className="space-y-1">
                              <p className="text-xs text-muted-foreground">
                                Doğru cevap:
                              </p>
                              <p className="text-xs md:text-sm text-emerald-500">
                                {correctAnswer}
                              </p>
                            </div>
                          )}

                          {(q.eval_score != null || q.eval_feedback) && (
                            <div className="pt-1 space-y-1">
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant="outline"
                                  className="text-[10px] flex items-center gap-1"
                                >
                                  <Sparkles className="w-3 h-3 text-primary" />
                                  AI değerlendirme
                                </Badge>
                                {typeof q.eval_score === "number" && (
                                  <Badge
                                    variant="outline"
                                    className="text-[10px]"
                                  >
                                    Skor: {q.eval_score}/5
                                  </Badge>
                                )}
                              </div>
                              {q.eval_feedback && (
                                <p className="text-[11px] text-muted-foreground leading-relaxed">
                                  {q.eval_feedback}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}

                  {detail.questions.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      Bu attempt için soru detayı kaydedilmemiş.
                    </p>
                  )}
                </div>
              )}
            </Card>
          )
        })}

        {!isLoading && attempts.length === 0 && (
          <Card className="p-6 text-sm text-muted-foreground text-center">
            Henüz kayıtlı bir quiz attempt bulunamadı.
          </Card>
        )}
      </div>
    </div>
  )
}
