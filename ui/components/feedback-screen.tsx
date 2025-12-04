"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, ExternalLink, Sparkles } from "lucide-react"
import type { Question } from "@/app/types/quiz"

interface FeedbackScreenProps {
  question: Question
  userAnswer: string | string[] | undefined
  onNext: () => void
  isLastQuestion: boolean
  // 🔥 LLM değerlendirmesi (page.tsx’ten geliyor)
  evaluation?: {
    score?: number
    is_correct?: boolean
    feedback?: string
  } | null
}

// Source için yardımcı tip
interface SourceInfo {
  documentName?: string
  page?: number
  passageId?: string
  snippet?: string
}

export function FeedbackScreen({
  question,
  userAnswer,
  onNext,
  isLastQuestion,
  evaluation,
}: FeedbackScreenProps) {
  const isArray = Array.isArray(userAnswer)

  const rawCorrect =
    (question as any).correctAnswer ??
    (question as any).answer ??
    ""

  // 🔹 MCQ / True-False için klasik kontrol
  // 🔹 Açık uçlu / senaryo için LLM sonucu
  const isCorrect =
    question.type === "mcq" || question.type === "true_false"
      ? String(userAnswer ?? "").toLowerCase().trim() ===
        String(rawCorrect).toLowerCase().trim()
      : evaluation?.is_correct ?? false

  const title =
    question.type === "mcq" || question.type === "true_false"
      ? isCorrect
        ? "Correct!"
        : "Not Quite"
      : evaluation?.is_correct
      ? "Great job!"
      : "AI Feedback"

  return (
    <div className="animate-fade-in space-y-6">
      <Card
        className={`p-8 space-y-6 border-2 ${
          isCorrect ? "border-accent" : "border-destructive"
        }`}
      >
        {/* Üst başlık */}
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
            <h3 className="text-2xl font-semibold text-card-foreground">
              {title}
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              {question.type === "mcq" || question.type === "true_false"
                ? isCorrect
                  ? "Great job! You got it right."
                  : "Don't worry, let's learn from this."
                : "See how the AI evaluated your response."}
            </p>
          </div>
        </div>

        {/* Kullanıcının cevabı */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-card-foreground uppercase tracking-wide">
            Your Answer
          </h4>
          <div className="p-4 rounded-lg bg-muted/50 border border-border text-sm text-card-foreground leading-relaxed">
            {isArray
              ? (userAnswer as string[]).map((ans, i) => (
                  <div key={i} className="mb-2 last:mb-0">
                    <span className="font-medium">Step {i + 1}:</span>{" "}
                    {ans}
                  </div>
                ))
              : userAnswer || "No answer provided"}
          </div>
        </div>

        {/* Doğru cevap (senaryo/ açık uçlu hariç) */}
        {rawCorrect &&
          (question.type === "mcq" ||
            question.type === "true_false" ||
            question.type === "short_answer") && (
            <div className="p-4 rounded-lg bg-muted/50 border border-border space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Correct Answer
              </p>
              <p className="text-base text-card-foreground font-medium">
                {String(rawCorrect)}
              </p>
            </div>
          )}

        {/* Açıklama (rationale) */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-card-foreground uppercase tracking-wide">
            Explanation
          </h4>
          <p className="text-base text-muted-foreground leading-relaxed">
            {question.rationale ||
              "No explanation provided for this question."}
          </p>
        </div>

        {/* 🔥 AI Evaluation bloğu: sadece open_ended + scenario için */}
        {evaluation &&
          (question.type === "open_ended" ||
            question.type === "scenario") && (
            <div className="mt-2 p-4 rounded-lg border border-primary/40 bg-primary/5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <p className="text-xs font-semibold text-primary">
                    AI Evaluation
                  </p>
                </div>
                {typeof evaluation.score === "number" && (
                  <Badge variant="outline" className="text-xs">
                    Score: {evaluation.score}/5
                  </Badge>
                )}
              </div>
              {evaluation.feedback && (
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {evaluation.feedback}
                </p>
              )}
            </div>
          )}

        {/* Kaynak kartı (varsa) */}
        {question.source && (
          <div className="pt-4 border-t border-border">
            <SourceCard source={question.source as any} />
          </div>
        )}

        <Button
          onClick={onNext}
          className="w-full h-12 text-base font-medium"
          size="lg"
        >
          {isLastQuestion ? "View Results" : "Next Question"}
        </Button>
      </Card>
    </div>
  )
}

function SourceCard({ source }: { source?: SourceInfo | string | null }) {
  if (!source || typeof source === "string") return null

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-card-foreground uppercase tracking-wide">
        Source Reference
      </h4>
      <div className="p-4 rounded-lg bg-card border border-border hover:shadow-md transition-shadow">
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <p className="font-medium text-card-foreground">
                {source.documentName || "Unknown source"}
              </p>
              {(typeof source.page === "number" || source.passageId) && (
                <p className="text-sm text-muted-foreground">
                  {typeof source.page === "number"
                    ? `Page ${source.page}`
                    : ""}
                  {typeof source.page === "number" && source.passageId
                    ? " • "
                    : ""}
                  {source.passageId
                    ? `Passage ${source.passageId}`
                    : ""}
                </p>
              )}
            </div>
            <Button variant="ghost" size="sm" className="flex-shrink-0">
              <ExternalLink className="w-4 h-4" />
            </Button>
          </div>

          <div className="p-3 rounded bg-muted/50 border-l-2 border-primary">
            <p className="text-sm text-muted-foreground italic leading-relaxed">
              {source.snippet
                ? `"${source.snippet}"`
                : "No snippet available for this question."}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
