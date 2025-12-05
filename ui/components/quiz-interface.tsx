// app/components/quiz-interface.tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Clock, Loader2 } from "lucide-react"
import type { Question } from "@/app/types/quiz"

interface QuizInterfaceProps {
  question: Question
  questionNumber: number
  totalQuestions: number
  // 🔥 async de destekle
  onSubmit: (
    questionId: string | number,
    answer: string | string[],
  ) => void | Promise<void>
  questionTime?: number
  formatTime?: (ms: number) => string

  // Opsiyonel (dışarıdan MCQ seçimini kontrol etmek istersen)
  selected?: number | null
  setSelected?: (v: number | null) => void
}

export function QuizInterface({
  question,
  questionNumber,
  totalQuestions,
  onSubmit,
  questionTime = 0,
  formatTime = (ms) => {
    const totalSeconds = Math.floor(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes.toString().padStart(2, "0")}:${seconds
      .toString()
      .padStart(2, "0")}`
  },
  selected,
  setSelected,
}: QuizInterfaceProps) {
  const raw = question as any

  // --- Tip normalizasyonu ---
  const rawType =
    raw.type ??
    raw.question_type ??
    raw.qtype ??
    "mcq"

  const typeStr = String(rawType).toLowerCase().replace(/[-_\s]/g, "")

  let qtype: "mcq" | "true_false" | "short_answer" | "open_ended" | "scenario" =
    "mcq"

  if (["truefalse", "dogruyanlıs", "dogruyanlis", "true_false", "tf"].includes(typeStr)) {
    qtype = "true_false"
  } else if (["short", "kisa", "kısacevap", "kisacevap", "shortanswer"].includes(typeStr)) {
    qtype = "short_answer"
  } else if (["open", "openended", "acikuclu", "açıkuçlu", "acik", "açık"].includes(typeStr)) {
    qtype = "open_ended"
  } else if (["senaryo", "scenario"].includes(typeStr)) {
    qtype = "scenario"
  } else {
    qtype = "mcq"
  }

  const stem: string = raw.stem ?? raw.question ?? ""
  const options: string[] = raw.options ?? raw.choices ?? []

  const steps = raw.steps as any[] | undefined

  // Eğer parent'tan selected gelmediyse burada yönet
  const [localSelected, setLocalSelected] = useState<number | null>(null)
  const effectiveSelected = selected ?? localSelected
  const setEffectiveSelected = setSelected ?? setLocalSelected

  // open-ended / true-false / scenario cevapları
  const [textAnswer, setTextAnswer] = useState<string>("")
  const [scenarioAnswers, setScenarioAnswers] = useState<Record<number, string>>({})
  const [currentStep, setCurrentStep] = useState(1)

  // 🔥 yeni: submit sırasında kilitlemek için
  const [isSubmitting, setIsSubmitting] = useState(false)

  const progress = (questionNumber / totalQuestions) * 100

  // --- Gönderim ---
  const handleSubmit = async () => {
    if (isSubmitting) return // ikinci tıklamayı engelle

    const qid = raw.id ?? ""

    setIsSubmitting(true)
    try {
      if (qtype === "scenario") {
        const allAnswers = Object.values(scenarioAnswers)
        await onSubmit(qid, allAnswers)
        return
      }

      if (qtype === "mcq") {
        if (effectiveSelected == null) return
        const chosen = options[effectiveSelected]
        await onSubmit(qid, chosen)
        return
      }

      // true_false, short_answer, open_ended
      await onSubmit(qid, textAnswer)
    } finally {
      // component ekrandan kalksa bile ekstra zararı yok
      setIsSubmitting(false)
    }
  }

  const handleScenarioNext = async () => {
    if (steps && currentStep < steps.length) {
      setCurrentStep((prev) => prev + 1)
    } else {
      // Son adım → submit (LLM call burada)
      await handleSubmit()
    }
  }

  const isAnswerValid = () => {
    if (qtype === "scenario") {
      return (scenarioAnswers[currentStep] ?? "").trim().length > 0
    }
    if (qtype === "mcq") {
      return effectiveSelected != null
    }
    return textAnswer.trim().length > 0
  }

  const typeLabel =
    qtype === "mcq"
      ? "Multiple Choice"
      : qtype === "true_false"
      ? "True / False"
      : qtype === "open_ended"
      ? "Open Ended"
      : qtype === "short_answer"
      ? "Short Answer"
      : "Scenario"

  return (
    <div className="animate-fade-in space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Question {questionNumber} of {totalQuestions}
          </span>
          <span>{Math.round(progress)}% Complete</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      <Card className="p-8 space-y-6">
        {/* NOT SCENARIO */}
        {qtype !== "scenario" ? (
          <>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="inline-block px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                  {typeLabel}
                </div>

                <Badge variant="outline" className="flex items-center gap-1.5">
                  <Clock className="w-3 h-3" />
                  <span className="text-xs">{formatTime(questionTime)}</span>
                </Badge>
              </div>

              <h2 className="text-2xl font-semibold whitespace-pre-line">
                {stem}
              </h2>
            </div>

            {/* Multiple Choice */}
            {qtype === "mcq" && options.length > 0 && (
              <RadioGroup
                value={
                  effectiveSelected != null ? String(effectiveSelected) : ""
                }
                onValueChange={(val) => {
                  const idx = parseInt(val)
                  if (!isNaN(idx)) setEffectiveSelected(idx)
                }}
                className="space-y-3"
              >
                {options.map((opt, index) => (
                  <div
                    key={index}
                    className="flex items-start space-x-3 p-4 rounded-lg border hover:bg-muted/50 cursor-pointer"
                    onClick={() => setEffectiveSelected(index)}
                  >
                    <RadioGroupItem value={String(index)} id={`opt-${index}`} />
                    <Label htmlFor={`opt-${index}`} className="flex-1 cursor-pointer">
                      {opt}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            )}

            {/* True / False */}
            {qtype === "true_false" && (
              <RadioGroup
                value={textAnswer}
                onValueChange={setTextAnswer}
                className="space-y-3"
              >
                {["true", "false"].map((opt) => (
                  <div
                    key={opt}
                    className="flex items-center space-x-3 p-4 rounded-lg border hover:bg-muted/50 cursor-pointer"
                    onClick={() => setTextAnswer(opt)}
                  >
                    <RadioGroupItem value={opt} id={opt} />
                    <Label htmlFor={opt} className="flex-1 capitalize text-lg">
                      {opt}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            )}

            {/* Short Answer / Open Ended */}
            {(qtype === "short_answer" || qtype === "open_ended") && (
              <div className="space-y-2">
                <Label htmlFor="answer" className="text-sm font-medium">
                  Your Answer
                </Label>
                <Textarea
                  id="answer"
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  className={qtype === "open_ended" ? "min-h-40" : "min-h-24"}
                />
              </div>
            )}
          </>
        ) : (
          // SCENARIO
          <>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="inline-block px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                  Scenario - Step {currentStep} of{" "}
                  {Array.isArray(steps) && steps.length > 0 ? steps.length : 1}
                </div>

                <Badge variant="outline" className="flex items-center gap-1.5">
                  <Clock className="w-3 h-3" />
                  <span className="text-xs">{formatTime(questionTime)}</span>
                </Badge>
              </div>

              <h2 className="text-2xl font-semibold whitespace-pre-line">
                {stem}
              </h2>
            </div>

            <div className="space-y-4">
              {Array.isArray(steps) &&
                steps.length > 0 &&
                (() => {
                  const step = steps[currentStep - 1] || {}
                  const stepText = step.prompt ?? step.stem ?? ""
                  return (
                    <div className="p-4 rounded-lg bg-muted/50 border">
                      <p className="text-sm font-medium mb-2">
                        Step {currentStep}
                      </p>
                      <p className="text-base whitespace-pre-line">
                        {stepText}
                      </p>
                    </div>
                  )
                })()}

              {/* steps olsun olmasın her zaman textarea gösteriyoruz */}
              <Textarea
                value={scenarioAnswers[currentStep] || ""}
                onChange={(e) =>
                  setScenarioAnswers((prev) => ({
                    ...prev,
                    [currentStep]: e.target.value,
                  }))
                }
                placeholder="Describe your approach for this step..."
                className="min-h-32"
              />
            </div>
          </>
        )}

        <Button
          onClick={
            qtype === "scenario" ? handleScenarioNext : handleSubmit
          }
          disabled={!isAnswerValid() || isSubmitting}
          className="w-full h-12"
          size="lg"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Cevap değerlendiriliyor...
            </>
          ) : qtype === "scenario" &&
            Array.isArray(steps) &&
            currentStep < (steps?.length || 1) ? (
            "Next Step"
          ) : (
            "Submit Answer"
          )}
        </Button>
      </Card>
    </div>
  )
}
