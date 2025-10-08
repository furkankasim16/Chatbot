"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import type { Question } from "@/app/page"

interface QuizInterfaceProps {
  question: Question
  questionNumber: number
  totalQuestions: number
  onSubmit: (questionId: string, answer: string | string[]) => void
}

export function QuizInterface({ question, questionNumber, totalQuestions, onSubmit }: QuizInterfaceProps) {
  const [answer, setAnswer] = useState<string>("")
  const [scenarioAnswers, setScenarioAnswers] = useState<Record<number, string>>({})
  const [currentStep, setCurrentStep] = useState(1)

  console.log("[QuizInterface] Rendering question type:", question.type)

  const progress = (questionNumber / totalQuestions) * 100

  const handleSubmit = () => {
    if (question.type === "scenario") {
      const allAnswers = Object.values(scenarioAnswers)
      onSubmit(question.id, allAnswers)
    } else {
      onSubmit(question.id, answer)
    }
  }

  const handleScenarioNext = () => {
    if (question.steps && currentStep < question.steps.length) {
      setCurrentStep((prev) => prev + 1)
    } else {
      handleSubmit()
    }
  }

  const isAnswerValid = () => {
    if (question.type === "scenario") {
      return scenarioAnswers[currentStep]?.trim().length > 0
    }
    return answer.trim().length > 0
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Progress bar */}
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
        {question.type !== "scenario" ? (
          <>
            {/* Question header */}
            <div className="space-y-3">
              <div className="inline-block px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                {question.type === "mcq"
                  ? "Multiple Choice"
                  : question.type === "true_false"
                  ? "True/False"
                  : question.type === "open_ended"
                  ? "Open Ended"
                  : "Short Answer"}
              </div>
              <h2 className="text-2xl font-semibold text-card-foreground text-balance leading-relaxed">
                {question.stem}
              </h2>
            </div>

            {/* MCQ */}
            {question.type === "mcq" && question.options && (
              <RadioGroup value={answer} onValueChange={setAnswer} className="space-y-3">
                {question.options.map((option, index) => (
                  <div
                    key={index}
                    className="flex items-start space-x-3 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => setAnswer(option)}
                  >
                    <RadioGroupItem value={option} id={`option-${index}`} className="mt-0.5" />
                    <Label htmlFor={`option-${index}`} className="flex-1 cursor-pointer leading-relaxed">
                      {option}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            )}

            {/* True/False */}
            {question.type === "true_false" && (
              <RadioGroup value={answer} onValueChange={setAnswer} className="space-y-3">
                {["true", "false"].map((option) => (
                  <div
                    key={option}
                    className="flex items-center space-x-3 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => setAnswer(option)}
                  >
                    <RadioGroupItem value={option} id={option} />
                    <Label htmlFor={option} className="flex-1 cursor-pointer capitalize text-lg">
                      {option}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            )}

            {/* Short Answer & Open Ended */}
            {(question.type === "short_answer" || question.type === "open_ended") && (
              <div className="space-y-2">
                <Label htmlFor="answer" className="text-sm font-medium">
                  Your Answer
                </Label>
                <Textarea
                  id="answer"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  className={
                    question.type === "open_ended"
                      ? "min-h-40 text-base leading-relaxed"
                      : "min-h-24 text-base leading-relaxed"
                  }
                />
              </div>
            )}
          </>
        ) : (
          <>
            {/* Scenario mode */}
            <div className="space-y-3">
              <div className="inline-block px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                Scenario - Step {currentStep} of {question.steps?.length || 1}
              </div>
              <h2 className="text-2xl font-semibold text-card-foreground text-balance leading-relaxed">
                {question.stem}
              </h2>
            </div>

            {question.steps && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-muted/50 border border-border">
                  <p className="text-sm font-medium text-muted-foreground mb-2">Step {currentStep}</p>
                  <p className="text-base text-card-foreground leading-relaxed">
                    {question.steps[currentStep - 1].prompt}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="scenario-answer" className="text-sm font-medium">
                    Your Response
                  </Label>
                  <Textarea
                    id="scenario-answer"
                    value={scenarioAnswers[currentStep] || ""}
                    onChange={(e) =>
                      setScenarioAnswers((prev) => ({
                        ...prev,
                        [currentStep]: e.target.value,
                      }))
                    }
                    placeholder="Describe your approach..."
                    className="min-h-32 text-base leading-relaxed"
                  />
                </div>
              </div>
            )}
          </>
        )}

        {/* Submit / Next button */}
        <Button
          onClick={question.type === "scenario" ? handleScenarioNext : handleSubmit}
          disabled={!isAnswerValid()}
          className="w-full h-12 text-base font-medium"
          size="lg"
        >
          {question.type === "scenario" && currentStep < (question.steps?.length || 1)
            ? "Next Step"
            : "Submit Answer"}
        </Button>
      </Card>
    </div>
  )
}
