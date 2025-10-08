"use client"

import { useState, useEffect } from "react"
import { HomeScreen } from "@/components/home-screen"
import { QuizInterface } from "@/components/quiz-interface"
import { FeedbackScreen } from "@/components/feedback-screen"
import { ResultsScreen } from "@/components/results-screen"
import { AuthScreen } from "@/components/auth-screen"
import { StatsScreen } from "@/components/stats-screen"
import { AdminPanel } from "@/components/admin-panel"
import { UserMenu } from "@/components/user-menu"
import { ThemeToggle } from "@/components/theme-toggle"
import {
  getQuestionsFromDB,
  generateQuiz,
  login,
  register,
  getUserStats,
  submitQuizResult,
  type Question as APIQuestion,
  type UserStats,
  type LoginResponse,
} from "@/lib/api"
import { Loader2, AlertCircle, Sparkles } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export type QuizMode = "quick" | "daily" | "scenario"
export type QuestionType = "mcq" | "true_false" | "short_answer" | "scenario" | "open_ended"
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
  useOllama?: boolean
}

interface ExtendedLoginResponse extends LoginResponse {
  is_admin?: boolean
}

export default function QuizWidget() {
  const [screen, setScreen] = useState<"auth" | "home" | "quiz" | "feedback" | "results" | "stats" | "admin">("auth")
  const [config, setConfig] = useState<QuizConfig | null>(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [userAnswers, setUserAnswers] = useState<Record<string, string | string[]>>({})
  const [showFeedback, setShowFeedback] = useState(false)
  const [questions, setQuestions] = useState<Question[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  const [user, setUser] = useState<ExtendedLoginResponse | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)

  useEffect(() => {
    const savedToken = localStorage.getItem("auth_token")
    const savedUsername = localStorage.getItem("username")
    const savedIsAdmin = localStorage.getItem("is_admin") === "true"

    if (savedToken && savedUsername) {
      setUser({ access_token: savedToken, token_type: "bearer", username: savedUsername, is_admin: savedIsAdmin })
      setScreen("home")
      loadUserStats(savedToken)
    }
  }, [])

  const loadUserStats = async (token: string) => {
    try {
      const stats = await getUserStats(token)
      setUserStats(stats)
    } catch (error) {
      console.error("[v0] Failed to load user stats:", error)
    }
  }

  const handleStartQuiz = async (quizConfig: QuizConfig) => {
    setConfig(quizConfig)
    setCurrentQuestionIndex(0)
    setUserAnswers({})
    setShowFeedback(false)
    setIsLoading(true)
    setError(null)

    const controller = new AbortController()
    setAbortController(controller)

    console.log("[v0] Starting quiz with config:", quizConfig)
    console.log("[v0] API URL:", process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    console.log("[v0] Mock mode:", process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true")

    try {
      const questionCount = quizConfig.mode === "daily" ? 1 : quizConfig.mode === "quick" ? 5 : 3

      let apiQuestions: APIQuestion[]

      if (quizConfig.useOllama) {
        console.log("[v0] Using Ollama to generate questions...")
        const quizResponse = await generateQuiz(quizConfig.topic, quizConfig.difficulty, questionCount)
        apiQuestions = quizResponse.items
      } else {
        console.log("[v0] Fetching questions from database...")
        apiQuestions = await getQuestionsFromDB(quizConfig.topic, quizConfig.difficulty, questionCount)
      }

      setQuestions(apiQuestions.map(convertAPIQuestionToLocal))
      setScreen("quiz")
    } catch (err) {
      console.error("[v0] Error fetching questions:", err)
      const errorMessage = err instanceof Error ? err.message : "Failed to load questions"
      setError(
        `${errorMessage}\n\nTroubleshooting:\n• Backend'inizin çalıştığından emin olun: ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}\n• ${quizConfig.useOllama ? "Ollama servisinin çalıştığından emin olun" : "questions.db dosyasında sorular olduğundan emin olun"}\n• CORS ayarlarını kontrol edin\n• Veya mock mode'u aktif edin: NEXT_PUBLIC_USE_MOCK_DATA=true`,
      )
    } finally {
      setIsLoading(false)
      setAbortController(null)
    }
  }

  const handleCancel = () => {
    if (abortController) {
      abortController.abort()
      setAbortController(null)
    }
    setIsLoading(false)
    setError("Soru üretimi iptal edildi.")
  }

  const convertAPIQuestionToLocal = (apiQuestion: APIQuestion): Question => {
    console.log("[v0] API Question type:", apiQuestion.type)

    let questionType: QuestionType = apiQuestion.type as QuestionType

    const typeStr = apiQuestion.type.toLowerCase().replace(/[-_\s]/g, "")

    if (typeStr === "short" || typeStr === "kisa" || typeStr === "kısacevap" || typeStr === "kisacevap") {
      questionType = "short_answer"
    } else if (typeStr === "senaryo" || typeStr === "scenario") {
      questionType = "scenario"
    } else if (
      typeStr === "open" ||
      typeStr === "openended" ||
      typeStr === "acikuclu" ||
      typeStr === "açıkuçlu" ||
      typeStr === "acik" ||
      typeStr === "açık"
    ) {
      questionType = "open_ended"
    } else if (typeStr === "truefalse" || typeStr === "dogruyanlıs" || typeStr === "dogruyanlis") {
      questionType = "true_false"
    }

    console.log("[v0] Converted question type:", questionType)
    console.log("[v0] Original type string:", apiQuestion.type)

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

  const handleNext = async () => {
    const totalQuestions = config?.mode === "daily" ? 1 : config?.mode === "quick" ? 5 : 3

    if (currentQuestionIndex < totalQuestions - 1) {
      setCurrentQuestionIndex((prev) => prev + 1)
      setShowFeedback(false)
      setScreen("quiz")
    } else {
      if (config?.mode === "daily") {
        localStorage.setItem("lastDailyQuizCompletion", new Date().toISOString())
      }

      if (user && config) {
        const correctCount = questions.filter((q) => {
          const userAnswer = userAnswers[q.id]
          if (!userAnswer) return false

          if (q.type === "mcq" || q.type === "true_false") {
            return String(userAnswer).toLowerCase() === String(q.correctAnswer).toLowerCase()
          }
          return false
        }).length

        try {
          await submitQuizResult(user.access_token, {
            topic: config.topic,
            difficulty: config.difficulty,
            total_questions: questions.length,
            correct_answers: correctCount,
            completed_at: new Date().toISOString(),
          })

          await loadUserStats(user.access_token)
        } catch (error) {
          console.error("[v0] Failed to submit quiz result:", error)
        }
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

  const handleLogin = async (username: string, password: string) => {
    const response = (await login(username, password)) as ExtendedLoginResponse
    setUser(response)
    localStorage.setItem("auth_token", response.access_token)
    localStorage.setItem("username", response.username)
    localStorage.setItem("is_admin", String(response.is_admin || false))
    setScreen("home")
    await loadUserStats(response.access_token)
  }

  const handleRegister = async (username: string, email: string, password: string) => {
    const response = (await register(username, email, password)) as ExtendedLoginResponse
    setUser(response)
    localStorage.setItem("auth_token", response.access_token)
    localStorage.setItem("username", response.username)
    localStorage.setItem("is_admin", String(response.is_admin || false))
    setScreen("home")
    await loadUserStats(response.access_token)
  }

  const handleLogout = () => {
    setUser(null)
    setUserStats(null)
    localStorage.removeItem("auth_token")
    localStorage.removeItem("username")
    localStorage.removeItem("is_admin")
    setScreen("auth")
    handleRestart()
  }

  const handleViewStats = () => {
    setScreen("stats")
  }

  const handleViewAdminPanel = () => {
    setScreen("admin")
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
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <UserMenu
                username={user.username}
                isAdmin={user.is_admin}
                onViewStats={handleViewStats}
                onViewAdminPanel={handleViewAdminPanel}
                onLogout={handleLogout}
              />
            )}
          </div>
        </div>

        {screen === "auth" && <AuthScreen onLogin={handleLogin} onRegister={handleRegister} />}

        {screen === "stats" && userStats && <StatsScreen stats={userStats} onBack={() => setScreen("home")} />}

        {screen === "admin" && user && <AdminPanel token={user.access_token} onBack={() => setScreen("home")} />}

        {screen === "home" && <HomeScreen onStartQuiz={handleStartQuiz} />}

        {isLoading && (
          <Card className="p-12 flex flex-col items-center justify-center space-y-4">
            <div className="relative">
              <Loader2 className="w-12 h-12 animate-spin text-primary" />
              {config?.useOllama && (
                <Sparkles className="w-5 h-5 text-primary absolute -top-1 -right-1 animate-pulse" />
              )}
            </div>
            <div className="text-center space-y-4">
              <p className="text-lg font-medium text-foreground">
                {config?.useOllama ? "Sorular üretiliyor..." : "Quiz yükleniyor..."}
              </p>
              {config?.useOllama && (
                <p className="text-sm text-muted-foreground">İşlem tamamlanana kadar lütfen bekleyin</p>
              )}
              <Button onClick={handleCancel} variant="outline" size="sm">
                İptal Et
              </Button>
            </div>
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
