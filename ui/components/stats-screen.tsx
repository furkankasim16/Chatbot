"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Trophy, Target, TrendingUp, Calendar, Award, BarChart3 } from "lucide-react"
import type { UserStats } from "@/lib/api"

interface StatsScreenProps {
  stats: UserStats
  onBack: () => void
}

export function StatsScreen({ stats, onBack }: StatsScreenProps) {
  const accuracyPercentage =
    stats.total_questions > 0 ? Math.round((stats.correct_answers / stats.total_questions) * 100) : 0

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
                <div className={`w-12 h-12 rounded-xl ${stat.color} flex items-center justify-center`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

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
                  topicStats.total > 0 ? Math.round((topicStats.correct / topicStats.total) * 100) : 0
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
                        {topicStats.correct}/{topicStats.total} ({topicAccuracy}%)
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
    </div>
  )
}
