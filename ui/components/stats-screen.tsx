"use client"

import { useEffect, useState } from "react"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Trophy,
  Target,
  TrendingUp,
  Calendar,
  Award,
  BarChart3,
  Clock,
  ListChecks,
} from "lucide-react"
import type { UserStats, QuizAttemptHistory } from "@/lib/api"
import { getRecentAttempts } from "@/lib/api"

interface StatsScreenProps {
  stats: UserStats
  token: string
  onBack: () => void
}

export function StatsScreen({ stats, token, onBack }: StatsScreenProps) {
  const accuracyPercentage =
    stats.total_questions > 0
      ? Math.round((stats.correct_answers / stats.total_questions) * 100)
      : 0

  const statCards = [
    {
      title: "Toplam Quiz",
      value: stats.total_quizzes,
      icon: BarChart3,
      color: "bg-blue-500",
    },
    {
      title: "Toplam Soru",
      value: stats.total_questions,
      icon: Target,
      color: "bg-purple-500",
    },
    {
      title: "Doğru Cevap",
      value: stats.correct_answers,
      icon: Trophy,
      color: "bg-green-500",
    },
    {
      title: "Başarı Oranı",
      value: `${accuracyPercentage}%`,
      icon: TrendingUp,
      color: "bg-orange-500",
    },
  ]

  // ⏱️ ms → Xm YYs formatına çeviren helper
  const formatMsToMinSec = (ms?: number) => {
    if (!ms || ms <= 0) return "—"
    const totalSeconds = Math.round(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes}dk ${seconds.toString().padStart(2, "0")}sn`
  }

  // 🔥 Son quiz denemeleri (backend /quiz/attempts/recent)
  const [attempts, setAttempts] = useState<QuizAttemptHistory[] | null>(null)
  const [loadingAttempts, setLoadingAttempts] = useState(false)
  const [attemptsError, setAttemptsError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        setLoadingAttempts(true)
        setAttemptsError(null)
        const data = await getRecentAttempts(token, 5)
        setAttempts(data)
      } catch (err) {
        console.error("[v0] getRecentAttempts failed:", err)
        setAttemptsError("Son quiz denemeleri yüklenemedi.")
      } finally {
        setLoadingAttempts(false)
      }
    }

    if (token) {
      load()
    }
  }, [token])

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-3xl font-bold text-foreground">İstatistiklerim</h2>
          <p className="text-muted-foreground">Öğrenme yolculuğunuzu takip edin</p>
        </div>
        <Button onClick={onBack} variant="outline">
          Geri Dön
        </Button>
      </div>

      {/* Genel istatistik kartları */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title} className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">{stat.title}</p>
                  <p className="text-3xl font-bold text-foreground">{stat.value}</p>
                </div>
                <div
                  className={`w-12 h-12 rounded-xl ${stat.color} flex items-center justify-center`}
                >
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Son aktivite */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Son Aktivite</h3>
              <p className="text-sm text-muted-foreground">
                {stats.last_quiz_date
                  ? new Date(stats.last_quiz_date).toLocaleDateString("tr-TR", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })
                  : "Henüz quiz çözülmedi"}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* ⏱️ Zaman istatistikleri */}
      {(stats.total_quiz_duration_ms ||
        stats.avg_quiz_duration_ms ||
        stats.avg_question_duration_ms) && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Clock className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Zaman İstatistikleri</h3>
                <p className="text-sm text-muted-foreground">
                  Quiz ve soru süreleriniz time modülünden alınmıştır.
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Toplam Quiz Süresi</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatMsToMinSec(stats.total_quiz_duration_ms)}
                </p>
              </div>

              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Ortalama Quiz Süresi</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatMsToMinSec(stats.avg_quiz_duration_ms)}
                </p>
              </div>

              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Ortalama Soru Süresi</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatMsToMinSec(stats.avg_question_duration_ms)}
                </p>
                {typeof stats.total_questions_timed === "number" && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Ölçülen soru sayısı: {stats.total_questions_timed}
                  </p>
                )}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Konu bazlı performans */}
      {stats.topic_stats && Object.keys(stats.topic_stats).length > 0 && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Award className="w-5 h-5 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground">Konu Bazlı Performans</h3>
            </div>
            <div className="space-y-3">
              {Object.entries(stats.topic_stats).map(([topic, topicStats]) => {
                const topicAccuracy =
                  topicStats.total > 0
                    ? Math.round((topicStats.correct / topicStats.total) * 100)
                    : 0
                return (
                  <div key={topic} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-foreground">
                        {topic
                          .split("_")
                          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(" ")}
                      </span>
                      <span className="text-muted-foreground">
                        {topicStats.correct}/{topicStats.total} ({topicAccuracy}
                        %)
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${topicAccuracy}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </Card>
      )}

      {/* 🆕 Son quiz denemeleri */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ListChecks className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold text-card-foreground">
              Son Quiz Denemelerim
            </h3>
          </div>
        </div>

        {loadingAttempts && (
          <p className="text-sm text-muted-foreground">Yükleniyor...</p>
        )}

        {attemptsError && (
          <p className="text-sm text-destructive">{attemptsError}</p>
        )}

        {!loadingAttempts && !attemptsError && attempts && attempts.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Henüz kayıtlı quiz denemeniz yok.
          </p>
        )}

        {!loadingAttempts && !attemptsError && attempts && attempts.length > 0 && (
          <div className="space-y-3">
            {attempts.map((attempt) => (
              <Card key={attempt.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-card-foreground">
                      {attempt.topic ?? "Genel"} ({attempt.difficulty ?? "mixed"})
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {attempt.quiz_date} • Skor: {attempt.score} •{" "}
                      {attempt.correct_answers}/{attempt.total_questions} doğru
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      {attempt.start_time
                        ? attempt.start_time.slice(11, 16)
                        : "--:--"}
                    </span>
                  </div>
                </div>

                {attempt.questions && attempt.questions.length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-primary cursor-pointer">
                      Soru detaylarını göster
                    </summary>
                    <div className="mt-2 space-y-2">
                      {attempt.questions.map((q) => (
                        <div
                          key={q.question_id}
                          className="p-2 rounded border border-border text-xs space-y-1"
                        >
                          <p className="font-medium text-card-foreground">
                            {q.stem}
                          </p>
                          <p className="text-muted-foreground">
                            Senin cevabın:{" "}
                            <span className="text-card-foreground">
                              {Array.isArray(q.user_answer)
                                ? q.user_answer.join(" | ")
                                : q.user_answer || "—"}
                            </span>
                          </p>
                          <p className="text-muted-foreground">
                            Doğru cevap:{" "}
                            <span className="text-accent">
                              {Array.isArray(q.correct_answer)
                                ? q.correct_answer.join(" | ")
                                : q.correct_answer || "—"}
                            </span>
                          </p>
                          {typeof q.eval_score === "number" && (
                            <p className="text-[11px] text-muted-foreground">
                              AI skor: {q.eval_score}/5
                            </p>
                          )}
                          {q.eval_feedback && (
                            <p className="text-[11px] text-muted-foreground">
                              {q.eval_feedback}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </Card>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
