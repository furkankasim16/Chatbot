"use client"

import { useState } from "react"
import { HomeScreen } from "@/components/home-screen"
import { QuizInterface } from "@/components/quiz-interface"
import { FeedbackScreen } from "@/components/feedback-screen"
import { ResultsScreen } from "@/components/results-screen"
import { ThemeToggle } from "@/components/theme-toggle"
import { getQuestionsFromDB, type Question as APIQuestion } from "@/lib/api"
import { Loader2, AlertCircle } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export type QuizMode = "quick" | "daily" | "scenario"
export type QuestionType = "mcq" | "true_false" | "short_answer" | "scenario"
export type Difficulty = "beginner" | "intermediate" | "advanced"

export interface Question {
  id: string
  type: QuestionType
  stem: string
  options?: string[]
  correctAnswer: string | string[]
  rationale: string
  source: {
    documentName: string
    page: number
    passageId: string
    snippet: string
  }
  steps?: {
    stepNumber: number
    prompt: string
    expectedAnswer: string
  }[]
}

export interface QuizConfig {
  mode: QuizMode
  topic: string
  difficulty: Difficulty
}

export default function QuizWidget() {
  const [screen, setScreen] = useState<"home" | "quiz" | "feedback" | "results">("home")
  const [config, setConfig] = useState<QuizConfig | null>(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [userAnswers, setUserAnswers] = useState<Record<string, string | string[]>>({})
  const [showFeedback, setShowFeedback] = useState(false)
  const [questions, setQuestions] = useState<Question[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStartQuiz = async (quizConfig: QuizConfig) => {
    setConfig(quizConfig)
    setCurrentQuestionIndex(0)
    setUserAnswers({})
    setShowFeedback(false)
    setIsLoading(true)
    setError(null)

    console.log("[v0] Starting quiz with config:", quizConfig)
    console.log("[v0] API URL:", process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    console.log("[v0] Mock mode:", process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true")

    try {
      const questionCount = quizConfig.mode === "daily" ? 1 : quizConfig.mode === "quick" ? 5 : 3

      const apiQuestions = await getQuestionsFromDB(quizConfig.topic, quizConfig.difficulty, questionCount)

      setQuestions(apiQuestions.map(convertAPIQuestionToLocal))
      setScreen("quiz")
    } catch (err) {
      console.error("[v0] Error fetching questions:", err)
      const errorMessage = err instanceof Error ? err.message : "Failed to load questions"
      setError(
        `${errorMessage}\n\nTroubleshooting:\n• Backend'inizin çalıştığından emin olun: ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}\n• questions.db dosyasında sorular olduğundan emin olun\n• CORS ayarlarını kontrol edin\n• Veya mock mode'u aktif edin: NEXT_PUBLIC_USE_MOCK_DATA=true`,
      )
    } finally {
      setIsLoading(false)
    }
  }

  const convertAPIQuestionToLocal = (apiQuestion: APIQuestion): Question => {
    console.log("[v0] API Question type:", apiQuestion.type)

    let questionType: QuestionType = apiQuestion.type as QuestionType
    if (apiQuestion.type === "short") {
      questionType = "short_answer"
    }

    console.log("[v0] Converted question type:", questionType)

    return {
      id: apiQuestion.id || Math.random().toString(),
      type: questionType,
      stem: apiQuestion.stem,
      options: apiQuestion.choices,
      correctAnswer:
        apiQuestion.type === "mcq" && apiQuestion.answer_index !== undefined
          ? apiQuestion.choices?.[apiQuestion.answer_index] || ""
          : apiQuestion.type === "true_false"
            ? String(apiQuestion.answer)
            : apiQuestion.expected || "",
      rationale: apiQuestion.rationale,
      source: {
        documentName: apiQuestion.source?.doc || "Unknown Document",
        page: apiQuestion.source?.chunk || 0,
        passageId: `${apiQuestion.source?.topic || "unknown"}-${apiQuestion.source?.chunk || 0}`,
        snippet: apiQuestion.rationale.substring(0, 150) + "...",
      },
      steps: apiQuestion.expected_points?.map((point, idx) => ({
        stepNumber: idx + 1,
        prompt: point,
        expectedAnswer: point,
      })),
    }
  }

  const handleAnswerSubmit = (questionId: string, answer: string | string[]) => {
    setUserAnswers((prev) => ({ ...prev, [questionId]: answer }))
    setShowFeedback(true)
    setScreen("feedback")
  }

  const handleNext = () => {
    const totalQuestions = config?.mode === "daily" ? 1 : config?.mode === "quick" ? 5 : 3

    if (currentQuestionIndex < totalQuestions - 1) {
      setCurrentQuestionIndex((prev) => prev + 1)
      setShowFeedback(false)
      setScreen("quiz")
    } else {
      if (config?.mode === "daily") {
        localStorage.setItem("lastDailyQuizCompletion", new Date().toISOString())
      }
      setScreen("results")
    }
  }

  const handleRestart = () => {
    setScreen("home")
    setConfig(null)
    setCurrentQuestionIndex(0)
    setUserAnswers({})
    setShowFeedback(false)
    setQuestions([])
    setError(null)
  }

  const currentQuestion = questions[currentQuestionIndex]

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">Q</span>
            </div>
            <h1 className="text-2xl font-bold text-foreground">QuizBot</h1>
          </div>
          <ThemeToggle />
        </div>

        {screen === "home" && <HomeScreen onStartQuiz={handleStartQuiz} />}

        {isLoading && (
          <Card className="p-12 flex flex-col items-center justify-center space-y-4">
            <Loader2 className="w-12 h-12 animate-spin text-primary" />
            <p className="text-lg text-muted-foreground">Loading your quiz...</p>
          </Card>
        )}

        {error && (
          <Card className="p-8 space-y-4 border-destructive/50">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-destructive flex-shrink-0 mt-0.5" />
              <div className="space-y-2 flex-1">
                <h3 className="text-xl font-semibold text-destructive">Backend Connection Error</h3>
                <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono bg-muted p-4 rounded-lg">
                  {error}
                </pre>
              </div>
            </div>
            <Button onClick={handleRestart} variant="outline" className="w-full bg-transparent">
              Return to Home
            </Button>
          </Card>
        )}

        {screen === "quiz" && currentQuestion && !isLoading && (
          <QuizInterface
            question={currentQuestion}
            questionNumber={currentQuestionIndex + 1}
            totalQuestions={config?.mode === "daily" ? 1 : config?.mode === "quick" ? 5 : 3}
            onSubmit={handleAnswerSubmit}
          />
        )}

        {screen === "feedback" && currentQuestion && (
          <FeedbackScreen
            question={currentQuestion}
            userAnswer={userAnswers[currentQuestion.id]}
            onNext={handleNext}
            isLastQuestion={currentQuestionIndex === (config?.mode === "daily" ? 0 : config?.mode === "quick" ? 4 : 2)}
          />
        )}

        {screen === "results" && (
          <ResultsScreen questions={questions} userAnswers={userAnswers} onRestart={handleRestart} />
        )}
      </div>
    </div>
  )
}
