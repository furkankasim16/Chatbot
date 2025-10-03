"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Trophy, RotateCcw, TrendingUp } from "lucide-react"
import type { Question } from "@/app/page"

interface ResultsScreenProps {
  questions: Question[]
  userAnswers: Record<string, string | string[]>
  onRestart: () => void
}

export function ResultsScreen({ questions, userAnswers, onRestart }: ResultsScreenProps) {
  const correctCount = questions.filter((q) => {
    const userAnswer = userAnswers[q.id]
    if (!userAnswer) return false

    if (q.type === "scenario") return true

    if (Array.isArray(userAnswer)) {
      return JSON.stringify(userAnswer.sort()) === JSON.stringify((q.correctAnswer as string[]).sort())
    }

    return userAnswer.toLowerCase().trim() === (q.correctAnswer as string).toLowerCase().trim()
  }).length

  const percentage = Math.round((correctCount / questions.length) * 100)
  const status = percentage >= 80 ? "Excellent" : percentage >= 60 ? "Good" : "Keep Practicing"

  return (
    <div className="animate-fade-in space-y-6">
      <Card className="p-8 space-y-6 text-center">
        <div className="flex justify-center">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center">
            <Trophy className="w-10 h-10 text-primary" />
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-card-foreground">Quiz Complete!</h2>
          <p className="text-muted-foreground text-lg">Here's how you performed</p>
        </div>

        <div className="py-6 space-y-4">
          <div className="text-6xl font-bold text-primary">{percentage}%</div>
          <div className="space-y-1">
            <p className="text-xl font-semibold text-card-foreground">{status}</p>
            <p className="text-muted-foreground">
              {correctCount} out of {questions.length} correct
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3 pt-4">
          <div className="p-4 rounded-lg bg-muted/50 space-y-1">
            <p className="text-2xl font-bold text-accent">{correctCount}</p>
            <p className="text-sm text-muted-foreground">Correct</p>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 space-y-1">
            <p className="text-2xl font-bold text-destructive">{questions.length - correctCount}</p>
            <p className="text-sm text-muted-foreground">Incorrect</p>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 space-y-1">
            <p className="text-2xl font-bold text-primary">{questions.length}</p>
            <p className="text-sm text-muted-foreground">Total</p>
          </div>
        </div>

        <div className="pt-4 space-y-3">
          <Button onClick={onRestart} className="w-full h-12 text-base font-medium" size="lg">
            <RotateCcw className="w-4 h-4 mr-2" />
            Start New Quiz
          </Button>

          {percentage < 80 && (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
              <TrendingUp className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
              <p className="text-sm text-muted-foreground leading-relaxed text-left">
                Review the explanations and source materials to improve your understanding. Practice makes perfect!
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
