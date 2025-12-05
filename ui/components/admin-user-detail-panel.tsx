"use client"

import { useEffect, useMemo, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  BarChart3,
  ArrowLeft,
  Clock,
  Award,
  Target,
} from "lucide-react"
import {
  adminGetQuizAttempts,
  type AdminQuizAttempt,
} from "@/lib/api"

interface AdminUserDetailPanelProps {
  token: string
  userId: number
  username: string
  onBack: () => void
}

export function AdminUserDetailPanel({
  token,
  userId,
  username,
  onBack,
}: AdminUserDetailPanelProps) {
  const [attempts, setAttempts] = useState<AdminQuizAttempt[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    ;(async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await adminGetQuizAttempts(token, {
          user_id: userId,
          limit: 200,
        })
        setAttempts(data)
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : "Kullanıcı denemeleri yüklenemedi",
        )
      } finally {
        setIsLoading(false)
      }
    })()
  }, [token, userId])

  const stats = useMemo(() => {
    if (attempts.length === 0) {
      return {
        totalQuizzes: 0,
        totalQuestions: 0,
        correctAnswers: 0,
        avgScorePct: 0,
        avgDurationMs: 0,
        topicStats: {} as Record<string, { correct: number; total: number }>,
        difficultyStats: {} as Record<string, { correct: number; total: number }>,
      }
    }

    let totalQuestions = 0
    let correctAnswers = 0
    let scoreSum = 0
    let durationSum = 0
    let durationCount = 0

    const topicStats: Record<string, { correct: number; total: number }> = {}
    const difficultyStats: Record<string, { correct: number; total: number }> =
      {}

    for (const a of attempts) {
      const correct = a.correct_answers ?? 0
      const total = a.total_questions ?? 0
      const score = a.score ?? 0

      totalQuestions += total
      correctAnswers += correct

      // skor zaten yüzde ise direkt al, 0–1 aralığındaysa çarp
      const pct = score <= 1 ? score * 100 : score
      scoreSum += pct

      if (a.total_duration_ms && a.total_duration_ms > 0) {
        durationSum += a.total_duration_ms
        durationCount += 1
      }

      const topicKey = a.topic ?? "general"
      if (!topicStats[topicKey]) {
        topicStats[topicKey] = { correct: 0, total: 0 }
      }
      topicStats[topicKey].correct += correct
      topicStats[topicKey].total += total

      const diffKey = a.difficulty ?? "unknown"
      if (!difficultyStats[diffKey]) {
        difficultyStats[diffKey] = { correct: 0, total: 0 }
      }
      difficultyStats[diffKey].correct += correct
      difficultyStats[diffKey].total += total
    }

    const totalQuizzes = attempts.length
    const avgScorePct =
      totalQuizzes > 0 ? Math.round(scoreSum / totalQuizzes) : 0
    const avgDurationMs =
      durationCount > 0 ? Math.round(durationSum / durationCount) : 0

    return {
      totalQuizzes,
      totalQuestions,
      correctAnswers,
      avgScorePct,
      avgDurationMs,
      topicStats,
      difficultyStats,
    }
  }, [attempts])

  const formatDuration = (ms?: number | null) => {
    if (!ms || ms <= 0) return "—"
    const totalSeconds = Math.round(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes === 0) return `${seconds}s`
    return `${minutes}dk ${seconds.toString().padStart(2, "0")}sn`
  }

  const formatTopic = (topic?: string | null) => {
    if (!topic) return "Genel"
    return topic
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  }

  const formatDifficulty = (d?: string | null) => {
    if (!d) return "Bilinmiyor"
    if (d === "beginner") return "Başlangıç"
    if (d === "intermediate") return "Orta"
    if (d === "advanced") return "İleri"
    return d
  }

  if (isLoading) {
    return (
      <Card className="p-6">
        <p className="text-center text-muted-foreground">
          Kullanıcı detayları yükleniyor...
        </p>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <h2 className="text-lg font-semibold">
            {username} - Öğrenci Detayı
          </h2>
          <div className="w-9" />
        </div>
        <p className="text-red-600 dark:text-red-400 text-sm">
          Hata: {error}
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h2 className="text-2xl font-bold">{username}</h2>
            <p className="text-xs text-muted-foreground">
              Kullanıcı performans özeti
            </p>
          </div>
        </div>
      </div>

      {/* Üst istatistik kartları */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4">
        <Card className="p-4 space-y-1">
          <p className="text-xs text-muted-foreground">Toplam Quiz</p>
          <p className="text-2xl font-bold">{stats.totalQuizzes}</p>
        </Card>
        <Card className="p-4 space-y-1">
          <p className="text-xs text-muted-foreground">Toplam Soru</p>
          <p className="text-2xl font-bold">{stats.totalQuestions}</p>
        </Card>
        <Card className="p-4 space-y-1">
          <p className="text-xs text-muted-foreground">Doğru Cevap</p>
          <p className="text-2xl font-bold">{stats.correctAnswers}</p>
        </Card>
        <Card className="p-4 space-y-1">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <BarChart3 className="w-3 h-3" />
            Ortalama Skor
          </p>
          <p className="text-2xl font-bold">
            {stats.avgScorePct}%
          </p>
        </Card>
      </div>

      {/* Zaman kartı */}
      <Card className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
            <Clock className="w-4 h-4 text-primary" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">
              Ortalama Quiz Süresi
            </p>
            <p className="text-lg font-semibold">
              {formatDuration(stats.avgDurationMs)}
            </p>
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {stats.totalQuizzes} deneme üzerinden
        </div>
      </Card>

      {/* Konu bazlı performans */}
      {Object.keys(stats.topicStats).length > 0 && (
        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Award className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold">
              Konu Bazlı Performans
            </h3>
          </div>
          <div className="space-y-3">
            {Object.entries(stats.topicStats).map(([topic, t]) => {
              const pct =
                t.total > 0
                  ? Math.round((t.correct / t.total) * 100)
                  : 0
              return (
                <div key={topic} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">
                      {formatTopic(topic)}
                    </span>
                    <span className="text-muted-foreground">
                      {t.correct}/{t.total} ({pct}%)
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Zorluk bazlı performans */}
      {Object.keys(stats.difficultyStats).length > 0 && (
        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold">
              Zorluk Bazlı Performans
            </h3>
          </div>
          <div className="space-y-3">
            {Object.entries(stats.difficultyStats).map(([diff, d]) => {
              const pct =
                d.total > 0
                  ? Math.round((d.correct / d.total) * 100)
                  : 0
              return (
                <div key={diff} className="flex items-center justify-between text-xs">
                  <span className="font-medium">
                    {formatDifficulty(diff)}
                  </span>
                  <span className="text-muted-foreground">
                    {d.correct}/{d.total} ({pct}%)
                  </span>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Son quiz listesi */}
      <Card className="p-6 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold">
            Son Quiz Denemeleri
          </h3>
        </div>

        {attempts.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Kullanıcının henüz quiz denemesi yok.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-muted-foreground border-b">
                <tr>
                  <th className="text-left py-1 pr-2">Tarih</th>
                  <th className="text-left py-1 pr-2">Konu</th>
                  <th className="text-left py-1 pr-2">Zorluk</th>
                  <th className="text-left py-1 pr-2">Skor</th>
                  <th className="text-left py-1 pr-2">Süre</th>
                </tr>
              </thead>
              <tbody>
                {attempts.map((a) => {
                  const rawScore = a.score ?? 0
                  const pct =
                    rawScore <= 1
                      ? Math.round(rawScore * 100)
                      : Math.round(rawScore)

                  return (
                    <tr key={a.id} className="border-b last:border-0">
                      <td className="py-1 pr-2">
                        {a.quiz_date}
                      </td>
                      <td className="py-1 pr-2">
                        {formatTopic(a.topic ?? undefined)}
                      </td>
                      <td className="py-1 pr-2">
                        {formatDifficulty(a.difficulty)}
                      </td>
                      <td className="py-1 pr-2">{pct}%</td>
                      <td className="py-1 pr-2">
                        {formatDuration(a.total_duration_ms)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
