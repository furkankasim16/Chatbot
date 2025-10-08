"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Trophy, RotateCcw, TrendingUp, AlertCircle, CheckCircle2, XCircle } from "lucide-react"
import type { Question } from "@/app/page"

interface ResultsScreenProps {
  questions: Question[]
  userAnswers: Record<string, string | string[]>
  onRestart: () => void
}

function normalizeAnswer(answer: string): string {
  return answer
    .toLowerCase()
    .trim()
    .replace(/[.,!?;:]/g, "") // Noktalama işaretlerini kaldır
    .replace(/\s+/g, " ") // Birden fazla boşluğu tek boşluğa çevir
}

function calculateSimilarity(str1: string, str2: string): number {
  const s1 = normalizeAnswer(str1)
  const s2 = normalizeAnswer(str2)

  if (s1 === s2) return 100

  // Basit benzerlik hesaplama (Levenshtein benzeri)
  const longer = s1.length > s2.length ? s1 : s2
  const shorter = s1.length > s2.length ? s2 : s1

  if (longer.length === 0) return 100

  const editDistance = levenshteinDistance(longer, shorter)
  return ((longer.length - editDistance) / longer.length) * 100
}

function levenshteinDistance(str1: string, str2: string): number {
  const matrix: number[][] = []

  for (let i = 0; i <= str2.length; i++) {
    matrix[i] = [i]
  }

  for (let j = 0; j <= str1.length; j++) {
    matrix[0][j] = j
  }

  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1]
      } else {
        matrix[i][j] = Math.min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1)
      }
    }
  }

  return matrix[str2.length][str1.length]
}

export function ResultsScreen({ questions, userAnswers, onRestart }: ResultsScreenProps) {
  const autoGradedQuestions = questions.filter(
    (q) => q.type === "mcq" || q.type === "true_false" || q.type === "short_answer",
  )

  const manualReviewQuestions = questions.filter((q) => q.type === "open_ended" || q.type === "scenario")

  const correctCount = autoGradedQuestions.filter((q) => {
    const userAnswer = userAnswers[q.id]
    if (!userAnswer) return false

    if (Array.isArray(userAnswer)) {
      return JSON.stringify(userAnswer.sort()) === JSON.stringify((q.correctAnswer as string[]).sort())
    }

    // MCQ ve True/False için tam eşleşme
    if (q.type === "mcq" || q.type === "true_false") {
      return normalizeAnswer(userAnswer) === normalizeAnswer(q.correctAnswer as string)
    }

    // Short answer için benzerlik kontrolü
    const similarity = calculateSimilarity(userAnswer, q.correctAnswer as string)
    return similarity >= 85 // %85 benzerlik yeterli
  }).length

  const percentage = autoGradedQuestions.length > 0 ? Math.round((correctCount / autoGradedQuestions.length) * 100) : 0
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

        {autoGradedQuestions.length > 0 && (
          <>
            <div className="py-6 space-y-4">
              <div className="text-6xl font-bold text-primary">{percentage}%</div>
              <div className="space-y-1">
                <p className="text-xl font-semibold text-card-foreground">{status}</p>
                <p className="text-muted-foreground">
                  {correctCount} out of {autoGradedQuestions.length} correct
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3 pt-4">
              <div className="p-4 rounded-lg bg-muted/50 space-y-1">
                <p className="text-2xl font-bold text-accent">{correctCount}</p>
                <p className="text-sm text-muted-foreground">Correct</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50 space-y-1">
                <p className="text-2xl font-bold text-destructive">{autoGradedQuestions.length - correctCount}</p>
                <p className="text-sm text-muted-foreground">Incorrect</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50 space-y-1">
                <p className="text-2xl font-bold text-primary">{autoGradedQuestions.length}</p>
                <p className="text-sm text-muted-foreground">Auto-Graded</p>
              </div>
            </div>
          </>
        )}

        {manualReviewQuestions.length > 0 && (
          <div className="pt-4 space-y-4">
            <div className="flex items-center gap-2 justify-center text-muted-foreground">
              <AlertCircle className="w-5 h-5" />
              <p className="text-sm font-medium">
                {manualReviewQuestions.length} question{manualReviewQuestions.length > 1 ? "s" : ""} require manual
                review
              </p>
            </div>

            <div className="space-y-3 text-left">
              {manualReviewQuestions.map((q, index) => {
                const userAnswer = userAnswers[q.id]
                return (
                  <Card key={q.id} className="p-4 space-y-3">
                    <div className="space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-primary/10 text-primary">
                          {q.type === "scenario" ? "Scenario" : "Open Ended"}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-card-foreground">{q.stem}</p>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">Your Answer:</p>
                      <div className="p-3 rounded-lg bg-muted/50 text-sm text-card-foreground leading-relaxed">
                        {Array.isArray(userAnswer)
                          ? userAnswer.map((ans, i) => (
                              <div key={i} className="mb-2 last:mb-0">
                                <span className="font-medium">Step {i + 1}:</span> {ans}
                              </div>
                            ))
                          : userAnswer || "No answer provided"}
                      </div>
                    </div>

                    {q.correctAnswer && (
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">Sample Answer:</p>
                        <div className="p-3 rounded-lg bg-accent/5 text-sm text-card-foreground leading-relaxed">
                          {Array.isArray(q.correctAnswer)
                            ? q.correctAnswer.map((ans, i) => (
                                <div key={i} className="mb-2 last:mb-0">
                                  <span className="font-medium">Step {i + 1}:</span> {ans}
                                </div>
                              ))
                            : q.correctAnswer}
                        </div>
                      </div>
                    )}
                  </Card>
                )
              })}
            </div>
          </div>
        )}

        <div className="pt-4 space-y-3">
          <Button onClick={onRestart} className="w-full h-12 text-base font-medium" size="lg">
            <RotateCcw className="w-4 h-4 mr-2" />
            Start New Quiz
          </Button>

          {percentage < 80 && autoGradedQuestions.length > 0 && (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
              <TrendingUp className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
              <p className="text-sm text-muted-foreground leading-relaxed text-left">
                Review the explanations and source materials to improve your understanding. Practice makes perfect!
              </p>
            </div>
          )}
        </div>
      </Card>

      {autoGradedQuestions.length > 0 && (
        <Card className="p-6 space-y-4">
          <h3 className="text-lg font-semibold text-card-foreground">Answer Review</h3>
          <div className="space-y-3">
            {autoGradedQuestions.map((q, index) => {
              const userAnswer = userAnswers[q.id]
              const isCorrect = (() => {
                if (!userAnswer) return false
                if (Array.isArray(userAnswer)) {
                  return JSON.stringify(userAnswer.sort()) === JSON.stringify((q.correctAnswer as string[]).sort())
                }
                if (q.type === "mcq" || q.type === "true_false") {
                  return normalizeAnswer(userAnswer) === normalizeAnswer(q.correctAnswer as string)
                }
                return calculateSimilarity(userAnswer, q.correctAnswer as string) >= 85
              })()

              return (
                <div key={q.id} className="flex items-start gap-3 p-4 rounded-lg border border-border">
                  {isCorrect ? (
                    <CheckCircle2 className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1 space-y-2 text-left">
                    <p className="text-sm font-medium text-card-foreground">{q.stem}</p>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        Your answer: <span className="text-card-foreground">{userAnswer || "No answer"}</span>
                      </p>
                      {!isCorrect && (
                        <p className="text-xs text-muted-foreground">
                          Correct answer: <span className="text-accent">{q.correctAnswer as string}</span>
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}
    </div>
  )
}
