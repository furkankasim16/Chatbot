"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Zap, Calendar, GitBranch, Clock, Loader2, Sparkles } from "lucide-react"
import type { QuizMode, Difficulty, QuizConfig } from "@/app/types/quiz"
import { getTopics } from "@/lib/api"
import useSWR from "swr"

interface HomeScreenProps {
  onStartQuiz: (config: QuizConfig) => void
  onChatMode: () => void
}

export function HomeScreen({ onStartQuiz, onChatMode }: HomeScreenProps) {
  const [selectedMode, setSelectedMode] = useState<QuizMode | null>(null)
  const [topic, setTopic] = useState("product_basics")
  const [difficulty, setDifficulty] = useState<Difficulty>("beginner")
  const [isDailyAvailable, setIsDailyAvailable] = useState(true)
  const [nextDailyTime, setNextDailyTime] = useState<string>("")
  const [useOllama, setUseOllama] = useState(false)

  const {
    data: topicsData,
    error: topicsError,
    isLoading: topicsLoading,
  } = useSWR("topics", getTopics, { revalidateOnFocus: false })

  useEffect(() => {
    console.log("[v0] [TOPICS] Loading:", topicsLoading)
    console.log("[v0] [TOPICS] Error:", topicsError)
    console.log("[v0] [TOPICS] Data:", topicsData)
  }, [topicsLoading, topicsError, topicsData])

  useEffect(() => {
    const lastDailyCompletion = localStorage.getItem("lastDailyQuizCompletion")
    if (lastDailyCompletion) {
      const lastTime = new Date(lastDailyCompletion).getTime()
      const now = new Date().getTime()
      const hoursPassed = (now - lastTime) / (1000 * 60 * 60)

      if (hoursPassed < 24) {
        setIsDailyAvailable(false)
        const nextAvailable = new Date(lastTime + 24 * 60 * 60 * 1000)
        const hours = Math.floor((nextAvailable.getTime() - now) / (1000 * 60 * 60))
        const minutes = Math.floor(((nextAvailable.getTime() - now) % (1000 * 60 * 60)) / (1000 * 60))
        setNextDailyTime(`${hours}h ${minutes}m`)
      }
    }
  }, [])

  const handleStart = () => {
    if (selectedMode === "daily" && !isDailyAvailable) {
      return
    }
    if (selectedMode) {
      onStartQuiz({ mode: selectedMode, topic, difficulty, useOllama: false })
    }
  }

  const modes = [
    {
      id: "quick" as QuizMode,
      title: "Quick Quiz",
      description: "5-10 questions to test your knowledge",
      icon: Zap,
      color: "bg-primary",
    },
    {
      id: "daily" as QuizMode,
      title: "Daily Question",
      description: "One question per day to stay sharp",
      icon: Calendar,
      color: "bg-accent",
    },
  ]

  const availableTopics = topicsData?.topics
    ? Object.keys(topicsData.topics)
    : ["product_basics", "support_flow", "security_policy"]

  useEffect(() => {
    console.log("[v0] [TOPICS] Available topics:", availableTopics)
    console.log("[v0] [TOPICS] Current topic:", topic)
  }, [availableTopics, topic])

  const formatTopicName = (topicValue: string) => {
    return topicValue
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  }

  return (
    <div className="animate-fade-in space-y-8">
      <div className="text-center space-y-3">
        <h2 className="text-4xl font-bold text-foreground text-balance">Öğrenme Yolunu Seç</h2>
        <p className="text-muted-foreground text-lg">Bir quiz modu seç ve öğrenme deneyimini özelleştir</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 max-w-4xl mx-auto">
        {modes.map((mode) => {
          const Icon = mode.icon
          const isSelected = selectedMode === mode.id
          const isDisabled = mode.id === "daily" && !isDailyAvailable

          return (
            <Card
              key={mode.id}
              className={`p-6 cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105 ${isSelected ? "ring-2 ring-primary shadow-lg" : ""
                } ${isDisabled ? "opacity-50 cursor-not-allowed hover:scale-100" : ""}`}
              onClick={() => !isDisabled && setSelectedMode(mode.id)}
            >
              <div className="space-y-4">
                <div className={`w-12 h-12 rounded-xl ${mode.color} flex items-center justify-center relative`}>
                  <Icon className={`w-6 h-6 ${mode.id === "scenario" ? "text-secondary-foreground" : "text-white"}`} />
                  {isDisabled && (
                    <div className="absolute inset-0 bg-background/80 rounded-xl flex items-center justify-center">
                      <Clock className="w-5 h-5 text-muted-foreground" />
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold text-card-foreground">{mode.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {isDisabled ? `${nextDailyTime} içinde erişilebilir` : mode.description}
                  </p>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      <Card className="p-6 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-foreground">Chat Modu</h3>
            <p className="text-sm text-muted-foreground">Yapay zeka ile sohbet edin, sorularınızı sorun</p>
          </div>
          <Button onClick={onChatMode} variant="secondary" size="lg">
            Chat Moduna Geç
          </Button>
        </div>
      </Card>

      {selectedMode && (
        <Card className="p-6 animate-slide-in space-y-6">
          <h3 className="text-lg font-semibold text-card-foreground">Quiz'ini Özelleştir</h3>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Konu</label>
              <Select value={topic} onValueChange={setTopic} disabled={topicsLoading}>
                <SelectTrigger>
                  <SelectValue>
                    {topicsLoading ? (
                      <span className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Konular yükleniyor...
                      </span>
                    ) : topic ? (
                      formatTopicName(topic)
                    ) : (
                      <span className="text-muted-foreground">Bir konu seç</span>
                    )}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {topicsLoading ? (
                    <SelectItem value="loading" disabled>
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Konular yükleniyor...
                      </div>
                    </SelectItem>
                  ) : topicsError ? (
                    <SelectItem value="error" disabled>
                      Konular yüklenirken hata oluştu
                    </SelectItem>
                  ) : availableTopics.length === 0 ? (
                    <SelectItem value="no-topics" disabled>
                      Mevcut konu yok
                    </SelectItem>
                  ) : (
                    availableTopics.map((t) => (
                      <SelectItem key={t} value={t}>
                        {formatTopicName(t)}
                        {topicsData?.topics[t] && ` (${topicsData.topics[t]} soru)`}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Zorluk</label>
              <Select value={difficulty} onValueChange={(v) => setDifficulty(v as Difficulty)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="beginner">Başlangıç</SelectItem>
                  <SelectItem value="intermediate">Orta</SelectItem>
                  <SelectItem value="advanced">İleri</SelectItem>
                  {/* 🔥 Yeni mixed seviye */}
                  <SelectItem value="mixed">Karışık (Tüm Seviyeler)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>



          <Button
            onClick={handleStart}
            className="w-full h-12 text-base font-medium"
            size="lg"
            disabled={selectedMode === "daily" && !isDailyAvailable}
          >
            {selectedMode === "daily" && !isDailyAvailable
              ? `${nextDailyTime} içinde erişilebilir`
              : "Quiz'e Başla"}
          </Button>
        </Card>
      )}
    </div>
  )
}
