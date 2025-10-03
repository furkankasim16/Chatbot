"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { CheckCircle2, XCircle, ExternalLink } from "lucide-react"
import type { Question } from "@/app/page"

interface FeedbackScreenProps {
  question: Question
  userAnswer: string | string[]
  onNext: () => void
  isLastQuestion: boolean
}

export function FeedbackScreen({ question, userAnswer, onNext, isLastQuestion }: FeedbackScreenProps) {
  const isCorrect = checkAnswer(question, userAnswer)

  return (
    <div className="animate-fade-in space-y-6">
      <Card className={`p-8 space-y-6 border-2 ${isCorrect ? "border-accent" : "border-destructive"}`}>
        <div className="flex items-start gap-4">
          {isCorrect ? (
            <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 className="w-6 h-6 text-accent" />
            </div>
          ) : (
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center flex-shrink-0">
              <XCircle className="w-6 h-6 text-destructive" />
            </div>
          )}

          <div className="flex-1 space-y-2">
            <h3 className="text-2xl font-semibold text-card-foreground">{isCorrect ? "Correct!" : "Not Quite"}</h3>
            <p className="text-muted-foreground leading-relaxed">
              {isCorrect ? "Great job! You got it right." : "Don't worry, let's learn from this."}
            </p>
          </div>
        </div>

        {!isCorrect && question.type !== "scenario" && (
          <div className="p-4 rounded-lg bg-muted/50 border border-border space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Correct Answer</p>
            <p className="text-base text-card-foreground font-medium">
              {Array.isArray(question.correctAnswer) ? question.correctAnswer.join(", ") : question.correctAnswer}
            </p>
          </div>
        )}

        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-card-foreground uppercase tracking-wide">Explanation</h4>
          <p className="text-base text-muted-foreground leading-relaxed">{question.rationale}</p>
        </div>

        <div className="pt-4 border-t border-border">
          <SourceCard source={question.source} />
        </div>

        <Button onClick={onNext} className="w-full h-12 text-base font-medium" size="lg">
          {isLastQuestion ? "View Results" : "Next Question"}
        </Button>
      </Card>
    </div>
  )
}

function SourceCard({ source }: { source: Question["source"] }) {
  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-card-foreground uppercase tracking-wide">Source Reference</h4>
      <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-shadow">
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <p className="font-medium text-card-foreground">{source.documentName}</p>
              <p className="text-sm text-muted-foreground">
                Page {source.page} • Passage {source.passageId}
              </p>
            </div>
            <Button variant="ghost" size="sm" className="flex-shrink-0">
              <ExternalLink className="w-4 h-4" />
            </Button>
          </div>

          <div className="p-3 rounded bg-muted/50 border-l-2 border-primary">
            <p className="text-sm text-muted-foreground italic leading-relaxed">"{source.snippet}"</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function checkAnswer(question: Question, userAnswer: string | string[]): boolean {
  if (question.type === "scenario") {
    return true // Scenario questions are evaluated differently
  }

  if (Array.isArray(userAnswer)) {
    return JSON.stringify(userAnswer.sort()) === JSON.stringify((question.correctAnswer as string[]).sort())
  }

  return userAnswer.toLowerCase().trim() === (question.correctAnswer as string).toLowerCase().trim()
}
