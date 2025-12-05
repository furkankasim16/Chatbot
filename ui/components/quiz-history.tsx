"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Clock,
  Sparkles,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from "lucide-react"
import {
  getRecentAttempts,
  type QuizAttemptHistory,
  type QuizAttemptHistoryQuestion,
} from "@/lib/api"

interface QuizHistoryProps {
  token: string
}

export function QuizHistory({ token }: QuizHistoryProps) {
  const [items, setItems] = useState<QuizAttemptHistory[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  useEffect(() => {
    const load = async () => {
      if (!token) return
      setIsLoading(true)
      setError(null)
      try {
        const data = await getRecentAttempts(token, 10)
        setItems(data)
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Geçmiş quizler yüklenemedi",
        )
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [token])

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

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

  const formatTopic = (topic?: string | null) => {
    if (!topic) return "-"
    return topic
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  }

  const getScoreColor = (score?: number | null) => {
    const s = typeof score === "number" ? score : 0
    const percentage = s <= 1 ? s * 100 : s
    if (percentage >= 80) return "text-emerald-500"
    if (percentage >= 60) return "text-amber-400"
    return "text-red-500"
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

  const formatDurationFromMs = (ms?: number | null) => {
    if (!ms || ms <= 0) return "—"
    const totalSeconds = Math.round(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes === 0) return `${seconds}s`
    return `${minutes}dk ${seconds.toString().padStart(2, "0")}sn`
  }

  if (!token) return null

  return (
    <Card className="p-6 space-y-4 mt-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-foreground">
            Son Quiz Denemelerim
          </h3>
          <p className="text-xs text-muted-foreground">
            En son çözdüğünüz quizler, skorlarınız ve soru bazlı detaylar.
          </p>
        </div>
        <Sparkles className="w-4 h-4 text-primary" />
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Yükleniyor...</p>
      ) : error ? (
        <div className="space-y-2">
          <p className="text-sm text-red-500">Hata: {error}</p>
          <p className="text-xs text-muted-foreground">
            Daha sonra tekrar deneyebilirsiniz.
          </p>
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Henüz quiz geçmişiniz bulunmuyor.
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((attempt) => {
            const rawScore = attempt.score ?? 0
            const percentage =
              rawScore <= 1
                ? Math.round(rawScore * 100)
                : Math.round(rawScore)

            const questions = attempt.questions ?? []

            return (
              <div
                key={attempt.id}
                className="rounded-lg border border-border/60 bg-card/80"
              >
                {/* Ana satır (tıklanabilir) */}
                <button
                  type="button"
                  onClick={() => toggle(attempt.id)}
                  className="w-full flex flex-col gap-3 md:flex-row md:items-center md:justify-between p-3 md:p-4 hover:bg-muted/60 transition-colors text-left"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-1">
                      {expanded.has(attempt.id) ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                    </div>
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold">
                          {formatTopic(attempt.topic)}
                        </span>
                        {attempt.difficulty && (
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] ${getDifficultyBadgeClasses(
                              attempt.difficulty,
                            )}`}
                          >
                            {attempt.difficulty}
                          </span>
                        )}
                        <span className="text-[11px] text-muted-foreground">
                          {formatDate(attempt.quiz_date)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {attempt.correct_answers ?? 0}/
                        {attempt.total_questions} doğru
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 justify-end">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      {formatDurationFromMs(attempt.total_duration_ms)}
                    </div>
                    <div
                      className={`text-base font-semibold ${getScoreColor(
                        attempt.score,
                      )}`}
                    >
                      {percentage}%
                    </div>
                  </div>
                </button>

                {/* Detay bloğu */}
                {expanded.has(attempt.id) && (
                  <div className="border-t border-border/60 bg-muted/40 px-3 md:px-4 pb-3 md:pb-4 pt-2 md:pt-3">
                    {questions.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        Bu quiz için soru detay kaydı bulunmuyor.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {questions.map(
                          (q: QuizAttemptHistoryQuestion, idx: number) => {
                            const isCorrect = q.is_correct
                            const ua = Array.isArray(q.user_answer)
                              ? q.user_answer.join(", ")
                              : q.user_answer ?? "Boş"
                            const ca = Array.isArray(q.correct_answer)
                              ? q.correct_answer.join(", ")
                              : q.correct_answer ?? "—"

                            return (
                              <div
                                key={q.question_id || idx}
                                className={`p-3 rounded-lg border text-xs md:text-sm space-y-2 ${
                                  isCorrect
                                    ? "bg-emerald-50 dark:bg-emerald-950/15 border-emerald-200 dark:border-emerald-900"
                                    : "bg-red-50 dark:bg-red-950/15 border-red-200 dark:border-red-900"
                                }`}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1">
                                    <p className="font-semibold mb-1">
                                      Soru {idx + 1}
                                    </p>
                                    <p className="text-xs md:text-sm mb-1">
                                      {q.stem}
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

                                <p className="text-xs text-muted-foreground">
                                  <span className="font-medium">
                                    Senin cevabın:
                                  </span>{" "}
                                  <span className="text-foreground">{ua}</span>
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  <span className="font-medium">
                                    Doğru cevap:
                                  </span>{" "}
                                  <span className="text-foreground">{ca}</span>
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
                              </div>
                            )
                          },
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
