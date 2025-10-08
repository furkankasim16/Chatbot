"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Zap, Calendar, GitBranch, Clock, Loader2, Sparkles } from "lucide-react"
import type { QuizMode, Difficulty, QuizConfig } from "@/app/page"
import { getTopics } from "@/lib/api"
import useSWR from "swr"

interface HomeScreenProps {
  onStartQuiz: (config: QuizConfig) => void
}

export function HomeScreen({ onStartQuiz }: HomeScreenProps) {
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
      onStartQuiz({ mode: selectedMode, topic, difficulty, useOllama })
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
    {
      id: "scenario" as QuizMode,
      title: "Scenario Task",
      description: "Multi-step real-world scenarios",
      icon: GitBranch,
      color: "bg-secondary",
    },
  ]

  const availableTopics = topicsData?.topics
    ? Object.keys(topicsData.topics)
    : ["product_basics", "support_flow", "technical_concepts"]

  return (
    <div className="animate-fade-in space-y-8">
      <div className="text-center space-y-3">
        <h2 className="text-4xl font-bold text-foreground text-balance">Choose Your Learning Path</h2>
        <p className="text-muted-foreground text-lg">Select a quiz mode and customize your learning experience</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {modes.map((mode) => {
          const Icon = mode.icon
          const isSelected = selectedMode === mode.id
          const isDisabled = mode.id === "daily" && !isDailyAvailable

          return (
            <Card
              key={mode.id}
              className={`p-6 cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105 ${
                isSelected ? "ring-2 ring-primary shadow-lg" : ""
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
                    {isDisabled ? `Available in ${nextDailyTime}` : mode.description}
                  </p>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {selectedMode && (
        <Card className="p-6 animate-slide-in space-y-6">
          <h3 className="text-lg font-semibold text-card-foreground">Customize Your Quiz</h3>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Topic</label>
              <Select value={topic} onValueChange={setTopic} disabled={topicsLoading}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {topicsLoading ? (
                    <SelectItem value="loading" disabled>
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Loading topics...
                      </div>
                    </SelectItem>
                  ) : topicsError ? (
                    <SelectItem value="error" disabled>
                      Error loading topics
                    </SelectItem>
                  ) : (
                    availableTopics.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t
                          .split("_")
                          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(" ")}
                        {topicsData?.topics[t] && ` (${topicsData.topics[t]} questions)`}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Difficulty</label>
              <Select value={difficulty} onValueChange={(v) => setDifficulty(v as Difficulty)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="beginner">Beginner</SelectItem>
                  <SelectItem value="intermediate">Intermediate</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-start space-x-3 p-4 rounded-lg border border-border bg-muted/30">
            <Checkbox
              id="use-ollama"
              checked={useOllama}
              onCheckedChange={(checked) => setUseOllama(checked === true)}
            />
            <div className="space-y-1 flex-1">
              <Label htmlFor="use-ollama" className="flex items-center gap-2 cursor-pointer font-medium">
                <Sparkles className="w-4 h-4 text-primary" />
                Ollama ile Dinamik Soru Üret
              </Label>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {useOllama
                  ? "⚠️ Soru üretimi 20-30 saniye sürebilir. Veritabanından çekmek için kapatın."
                  : "Veritabanından hazır sorular çekilecek (hızlı). Yeni sorular üretmek için aktif edin."}
              </p>
            </div>
          </div>

          <Button
            onClick={handleStart}
            className="w-full h-12 text-base font-medium"
            size="lg"
            disabled={selectedMode === "daily" && !isDailyAvailable}
          >
            {selectedMode === "daily" && !isDailyAvailable ? `Available in ${nextDailyTime}` : "Start Quiz"}
          </Button>
        </Card>
      )}
    </div>
  )
}
