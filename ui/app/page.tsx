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
import { ChatScreen } from "@/components/chat-screen"
import { useQuizTimer } from "@/hooks/use-quiz-timer"
import type { Question, QuestionType } from "@/app/types/quiz"
import type {
  Question as APIQuestion,
  UserStats,
  LoginResponse,
  EvaluateAnswerOut as EvaluateAnswerResponse,
} from "@/lib/api"

import {
  getQuestionsFromDB,
  generateQuiz,
  login,
  register,
  getUserStats,
  evaluateAnswer,
  startQuizTiming,
  endQuizTiming,
  startQuestionTiming,
  endQuestionTiming,
} from "@/lib/api"

import { Loader2, AlertCircle, Sparkles, Clock } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export type QuizMode = "quick" | "daily" | "scenario"
export type Difficulty = "beginner" | "intermediate" | "advanced" | "mixed"

export interface QuizConfig {
  mode: QuizMode
  topic: string
  difficulty: Difficulty
  useOllama?: boolean
}

interface ExtendedLoginResponse extends LoginResponse {
  is_admin: boolean
  user_id?: number
}

type QuestionResultDetail = {
  question_id: string
  stem: string
  user_answer: string | string[]
  correct_answer: string | string[]
  is_correct: boolean
  eval_score?: number
  eval_feedback?: string
  rubric?: Array<{
    criteria: string
    score: number
    max_score: number
    feedback: string
  }>
}

export default function QuizWidget() {
  const [screen, setScreen] = useState<
    "auth" | "home" | "quiz" | "feedback" | "results" | "stats" | "admin" | "chat"
  >("auth")
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

  const timer = useQuizTimer()
  const [quizAttemptId, setQuizAttemptId] = useState<number | null>(null)
  const [currentQuestionTimingId, setCurrentQuestionTimingId] = useState<number | null>(null)

  const [currentEvaluation, setCurrentEvaluation] =
    useState<EvaluateAnswerResponse | null>(null)

  const [evalResults, setEvalResults] = useState<
    Record<string, EvaluateAnswerResponse>
  >({})

  const [detailedResults, setDetailedResults] = useState<QuestionResultDetail[] | null>(null)

  useEffect(() => {
    const savedToken = localStorage.getItem("auth_token")
    const savedUsername = localStorage.getItem("username")
    const savedIsAdmin = localStorage.getItem("is_admin") === "true"

    if (savedToken && savedUsername) {
      setUser({
        access_token: savedToken,
        token_type: "bearer",
        username: savedUsername,
        is_admin: savedIsAdmin,
      })
      setScreen("home")
      loadUserStats(savedToken)
    }
  }, [])

  // ✅ Chat -> Quiz event listener
  useEffect(() => {
    const onStart = () => {
      const raw = localStorage.getItem("pending_quiz")
      if (!raw) return

      try {
        const p = JSON.parse(raw)

        const quizConfig: QuizConfig = {
          mode: "quick",
          topic: p.topic ?? "security_policy",
          difficulty: (p.level ?? "beginner") as Difficulty,
          useOllama: !!p.use_ollama,
        }

        handleStartQuiz(quizConfig)
        localStorage.removeItem("pending_quiz")
      } catch (e) {
        console.error("[CHAT->QUIZ] pending_quiz parse failed:", e)
      }
    }

    window.addEventListener("start-quiz-from-chat", onStart as any)
    return () => window.removeEventListener("start-quiz-from-chat", onStart as any)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

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

    try {
      const questionCount =
        quizConfig.mode === "daily" ? 1 : quizConfig.mode === "quick" ? 5 : 3

      let apiQuestions: APIQuestion[]

      if (quizConfig.useOllama) {
        console.log("[v0] Using Ollama to generate questions...")
        const quizResponse = await generateQuiz(
          quizConfig.topic,
          quizConfig.difficulty,
          questionCount,
          true,
          "mcq",
        )
        apiQuestions = quizResponse.items
      } else {
        console.log("[v0] Fetching questions from database...")
        apiQuestions = await getQuestionsFromDB(
          quizConfig.topic,
          quizConfig.difficulty,
          questionCount,
        )
      }

      setQuestions(apiQuestions.map(convertAPIQuestionToLocal))

      if (user) {
        try {
          console.log("[v0] [TIMING] Calling startQuizTiming API...")

          const payload = {
            topic: quizConfig.topic,
            difficulty: quizConfig.difficulty,
            total_questions: questionCount,
            start_time: new Date().toISOString(),
            mode: quizConfig.mode,
          }

          console.log("[v0] [TIMING] payload:", payload)

          const quizStart = await startQuizTiming(user.access_token, payload)
          setQuizAttemptId(quizStart.attempt_id)
          timer.startQuiz()
          console.log("[v0] [TIMING] timer.startQuiz() called successfully")
        } catch (error) {
          console.error("[v0] [TIMING] Failed to start quiz timing:", error)
        }
      } else {
        console.warn("[v0] [TIMING] No user logged in, skipping quiz timing")
      }

      setScreen("quiz")
    } catch (err) {
      console.error("[v0] Error fetching questions:", err)
      const errorMessage = err instanceof Error ? err.message : "Failed to load questions"
      setError(
        `${errorMessage}\n\nTroubleshooting:\n• Backend'inizin çalıştığından emin olun\n• CORS ayarlarını kontrol edin`,
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

  /* ---------------------- API -> UI Question dönüştürücü ---------------------- */
  type RawQ = any
  const safeLower = (v: unknown) => (typeof v === "string" ? v.toLowerCase() : "")

  const convertAPIQuestionToLocal = (apiQuestion: RawQ): Question => {
    const rawType =
      apiQuestion?.question_type ??
      apiQuestion?.qtype ??
      apiQuestion?.type ??
      apiQuestion?.meta?.qtype ??
      "mcq"

    const typeStr = safeLower(String(rawType).replace(/[-_\s]/g, ""))

    let questionType: QuestionType = "mcq"

    if (["short", "kisa", "kısacevap", "kisacevap", "shortanswer"].includes(typeStr)) {
      questionType = "short_answer"
    } else if (["senaryo", "scenario"].includes(typeStr)) {
      questionType = "scenario"
    } else if (["open", "openended", "acikuclu", "açıkuçlu", "acik", "açık"].includes(typeStr)) {
      questionType = "open_ended"
    } else if (["truefalse", "dogruyanlıs", "dogruyanlis", "true_false", "tf"].includes(typeStr)) {
      questionType = "true_false"
    }

    // ❗ Boş scenario -> open_ended'e çevir
    let steps = apiQuestion?.steps
    if (questionType === "scenario") {
      if (!Array.isArray(steps) || steps.length === 0) {
        questionType = "open_ended"
        steps = []
      }
    }

    const stem: string = apiQuestion?.stem ?? apiQuestion?.question ?? ""

    const options: string[] = Array.isArray(apiQuestion?.choices)
      ? apiQuestion.choices
      : Array.isArray(apiQuestion?.options)
        ? apiQuestion.options
        : []

    // ---------- CEVAP NORMALİZASYONU ----------
    let correctAnswer: string | string[] = ""

    // 1. Array cevap kontrolü (backend ["Daily Scrum", "Günlük Scrum"] dönebilir)
    if (Array.isArray(apiQuestion?.answer) && apiQuestion.answer.length > 0) {
      correctAnswer = apiQuestion.answer
    }
    // 2. String cevap kontrolü
    else if (typeof apiQuestion?.answer === "string" && apiQuestion.answer.trim() !== "") {
      correctAnswer = apiQuestion.answer
    }

    // 3. Answer index veya options üzerinden bulma logic'i (MCQ için)
    if ((!correctAnswer || correctAnswer === "") && options.length > 0) {
      if (questionType === "short_answer") {
        // Short answer için options genellikle kabul edilen cevaplar listesidir
        correctAnswer = options
      } else {
        let idx: number | null = null
        const rawIdx = apiQuestion?.answer_index
        // ... (existing parsing logic) ...
        if (typeof rawIdx === "number") {
          idx = rawIdx
        } else if (typeof rawIdx === "string" && rawIdx.trim() !== "") {
          const parsed = parseInt(rawIdx, 10)
          if (!Number.isNaN(parsed)) idx = parsed
        }

        const rawCorrectIdx =
          apiQuestion?.correct_option_indexes ?? apiQuestion?.correct_option_index

        if (idx === null && Array.isArray(rawCorrectIdx) && rawCorrectIdx.length > 0) {
          const parsed = Number(rawCorrectIdx[0])
          if (!Number.isNaN(parsed)) idx = parsed
        } else if (
          idx === null &&
          (typeof rawCorrectIdx === "number" || typeof rawCorrectIdx === "string")
        ) {
          const parsed = Number(rawCorrectIdx)
          if (!Number.isNaN(parsed)) idx = parsed
        }

        if (idx !== null && idx >= 0 && idx < options.length) {
          correctAnswer = options[idx]
        }
      }
    }

    if ((!correctAnswer || correctAnswer === "") && questionType === "true_false") {
      if (typeof apiQuestion?.answer === "boolean") {
        correctAnswer = String(apiQuestion.answer)
      }
    }

    if (
      (!correctAnswer || correctAnswer === "") &&
      typeof apiQuestion?.expected === "string" &&
      apiQuestion.expected.trim() !== ""
    ) {
      correctAnswer = apiQuestion.expected
    }

    console.log("[DEBUG] convertAPIQuestionToLocal", {
      id: apiQuestion?.id,
      type: questionType,
      stem,
      options,
      answer_raw: apiQuestion?.answer,
      correctAnswer,
    })

    return {
      rationale: apiQuestion?.rationale ?? "",
      id: String(apiQuestion?.id ?? Math.random()),
      type: questionType,
      stem,
      options,
      answer:
        typeof correctAnswer === "string"
          ? correctAnswer
          : correctAnswer.length > 0
            ? correctAnswer[0]
            : undefined,
      correctAnswer,
      topic: apiQuestion?.topic ?? null,
      level: apiQuestion?.level ?? null,
      steps: steps ?? [],
      meta: apiQuestion?.meta ?? {},
      source: apiQuestion?.source ?? null,
    }
  }

  const handleAnswerSubmit = async (questionId: string | number, answer: string | string[]) => {
    // ... existing handleAnswerSubmit ...
    const key = String(questionId)
    setUserAnswers((prev) => ({ ...prev, [key]: answer }))

    const q = questions[currentQuestionIndex]
    let evalResult: EvaluateAnswerResponse | null = null

    if (user && q && (q.type === "open_ended" || q.type === "scenario" || q.type === "short_answer")) {
      // ... existing eval logic ...
      try {
        const rawCorrect =
          typeof (q as any).correctAnswer === "string"
            ? (q as any).correctAnswer
            : Array.isArray((q as any).correctAnswer)
              ? (q as any).correctAnswer.join(" ")
              : typeof (q as any).answer === "string"
                ? (q as any).answer
                : ""

        const userText = Array.isArray(answer)
          ? answer.map((ans, idx) => `Step ${idx + 1}: ${ans}`).join("\n")
          : String(answer)

        const result = await evaluateAnswer(user.access_token, q.stem, rawCorrect, userText)

        evalResult = result
        setEvalResults((prev) => ({ ...prev, [key]: result }))
      } catch (err) {
        console.error("[v0] evaluateAnswer (per-question) failed:", err)
      }
    }

    setCurrentEvaluation(evalResult)
    setShowFeedback(true)
    setScreen("feedback")
  }

  const handleNext = async () => {
    setCurrentEvaluation(null)

    if (currentQuestionTimingId && user) {
      try {
        await endQuestionTiming(user.access_token, {
          timing_id: currentQuestionTimingId,
          client_end_time: new Date().toISOString(),
        })
        timer.endQuestion()
      } catch (error) {
        console.error("[v0] Failed to end question timing:", error)
      }
    }

    const totalQuestions =
      config?.mode === "daily" ? 1 : config?.mode === "quick" ? 5 : 3

    if (currentQuestionIndex < totalQuestions - 1) {
      setCurrentQuestionIndex((prev) => prev + 1)
      setShowFeedback(false)
      setScreen("quiz")
      return
    }

    timer.endQuiz()

    if (config?.mode === "daily") {
      localStorage.setItem("lastDailyQuizCompletion", new Date().toISOString())
    }

    if (user && config) {
      let correctCount = 0
      const detailedQuestions: QuestionResultDetail[] = []

      for (const q of questions) {
        const key = String(q.id)
        const userAnswer = userAnswers[key]
        const evalForQ = evalResults[key]

        const rawCorrect =
          typeof (q as any).correctAnswer === "string"
            ? (q as any).correctAnswer
            : Array.isArray((q as any).correctAnswer)
              ? (q as any).correctAnswer.join(" ")
              : typeof (q as any).answer === "string"
                ? (q as any).answer
                : ""

        if (!userAnswer) {
          detailedQuestions.push({
            question_id: key,
            stem: q.stem,
            user_answer: "",
            correct_answer: (q as any).correctAnswer ?? rawCorrect,
            is_correct: false,
          })
          continue
        }

        let isCorrect = false

        if (q.type === "mcq" || q.type === "true_false") {
          isCorrect =
            String(userAnswer).toLowerCase().trim() ===
            String(rawCorrect).toLowerCase().trim()
        } else if (q.type === "short_answer") {
          if (evalForQ) {
            isCorrect = evalForQ.is_correct
          } else {
            const norm = (s: string) => s.toLowerCase().trim().replace(/[.,!?;:]/g, "")
            const userNorm = norm(String(userAnswer))

            // 🆕 Array support for short_answer
            if (Array.isArray((q as any).correctAnswer)) {
              const possibilities = (q as any).correctAnswer as string[]
              isCorrect = possibilities.some(poss => norm(poss) === userNorm)
            } else {
              isCorrect = userNorm === norm(String(rawCorrect))
            }
          }
        } else {
          // ... existing logic for open_ended ...
          if (evalForQ) {
            isCorrect = evalForQ.is_correct
          } else {
            const userWords = String(userAnswer).toLowerCase().split(/\s+/)
            const expectedWords = String(rawCorrect).toLowerCase().split(/\s+/)
            const matchCount = userWords.filter((w) => expectedWords.includes(w)).length
            const similarity = matchCount / Math.max(userWords.length, expectedWords.length || 1)
            isCorrect = similarity > 0.4
          }
        }

        if (isCorrect) correctCount++

        detailedQuestions.push({
          question_id: key,
          stem: q.stem,
          user_answer: userAnswer,
          correct_answer: (q as any).correctAnswer ?? rawCorrect,
          is_correct: isCorrect,
          eval_score: evalForQ?.score,
          eval_feedback: evalForQ?.feedback,
          rubric: evalForQ?.rubric,
        })
      }

      setDetailedResults(detailedQuestions)

      const totalQuestionsInResult = questions.length
      const numericScore =
        totalQuestionsInResult > 0 ? (correctCount / totalQuestionsInResult) * 100 : 0
      const score = Math.round(numericScore)

      if (quizAttemptId) {
        try {
          await endQuizTiming(user.access_token, {
            attempt_id: quizAttemptId,
            correct_answers: correctCount,
            score,
            client_end_time: new Date().toISOString(),
            total_duration_ms: timer.totalQuizTime,
            questions_attempted: JSON.stringify(detailedQuestions),
          })
        } catch (error) {
          console.error("[v0] Failed to finalize quiz attempt:", error)
        }
      }

      try {
        await loadUserStats(user.access_token)
      } catch (error) {
        console.error("[v0] Failed to reload user stats:", error)
      }
    }

    setScreen("results")
  }

  const handleRestart = () => {
    setScreen("home")
    setConfig(null)
    setCurrentQuestionIndex(0)
    setUserAnswers({})
    setShowFeedback(false)
    setQuestions([])
    setError(null)
    setQuizAttemptId(null)
    setCurrentQuestionTimingId(null)
    setCurrentEvaluation(null)
    setEvalResults({})
    setDetailedResults(null)
    timer.reset()
  }

  const handleLogin = async (username: string, password: string) => {
    const response = await login(username, password)
    setUser(response)
    localStorage.setItem("auth_token", response.access_token)
    localStorage.setItem("username", response.username)
    localStorage.setItem("is_admin", String(response.is_admin))
    setScreen("home")
    await loadUserStats(response.access_token)
  }

  const handleRegister = async (username: string, email: string, password: string) => {
    const response = await register(username, email, password)
    setUser(response)
    localStorage.setItem("auth_token", response.access_token)
    localStorage.setItem("username", response.username)
    localStorage.setItem("is_admin", String(response.is_admin))
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

  const handleViewStats = () => setScreen("stats")
  const handleViewAdminPanel = () => setScreen("admin")

  const currentQuestion = questions[currentQuestionIndex]

  useEffect(() => {
    if (screen === "quiz" && currentQuestion && quizAttemptId && user) {
      const startTiming = async () => {
        try {
          const questionStart = await startQuestionTiming(user.access_token, {
            attempt_id: quizAttemptId,
            question_id: String(currentQuestion.id),
          })
          setCurrentQuestionTimingId(questionStart.timing_id)
          timer.startQuestion(String(currentQuestion.id))
        } catch (error) {
          console.error("[v0] [TIMING] Failed to start question timing:", error)
        }
      }
      startTiming()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen, currentQuestion, quizAttemptId, user])

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">Q</span>
            </div>
            <h1 className="text-2xl font-bold text-foreground">QuizBot</h1>
            {timer.isQuizActive && (
              <div className="flex items-center gap-2">
                <Badge
                  variant={timer.isPaused ? "secondary" : "default"}
                  className="flex items-center gap-1.5"
                >
                  <Clock className="w-3.5 h-3.5" />
                  {timer.formatTime(timer.totalQuizTime)}
                </Badge>
                {timer.isPaused && (
                  <Badge variant="outline" className="text-xs">
                    {timer.pauseReason === "hidden" ? "Sekme Gizli" : "Boşta"}
                  </Badge>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <UserMenu
                username={user.username}
                isAdmin={user.is_admin || false}
                onViewStats={handleViewStats}
                onViewAdminPanel={handleViewAdminPanel}
                onLogout={handleLogout}
              />
            )}
          </div>
        </div>

        {screen === "auth" && <AuthScreen onLogin={handleLogin} onRegister={handleRegister} />}

        {screen === "stats" && userStats && user && (
          <StatsScreen stats={userStats} token={user.access_token} onBack={() => setScreen("home")} />
        )}

        {screen === "admin" && user && (
          <AdminPanel token={user.access_token} onBack={() => setScreen("home")} />
        )}

        {/* ✅ Chat Screen (props fixed) */}
        {screen === "chat" && user && (
          <ChatScreen
            token={user.access_token}
            defaultTopic={config?.topic ?? "security_policy"}
            defaultLevel={config?.difficulty ?? "beginner"}
            onBack={() => setScreen("home")}
          />
        )}

        {screen === "home" && (
          <HomeScreen onStartQuiz={handleStartQuiz} onChatMode={() => setScreen("chat")} />
        )}

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
                <p className="text-sm text-muted-foreground">
                  İşlem tamamlanana kadar lütfen bekleyin
                </p>
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
                <h3 className="text-xl font-semibold text-destructive">
                  Backend Bağlantı Hatası
                </h3>
                <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono bg-muted p-4 rounded-lg">
                  {error}
                </pre>
              </div>
            </div>
            <Button onClick={handleRestart} variant="outline" className="w-full bg-transparent">
              Ana Sayfaya Dön
            </Button>
          </Card>
        )}

        {screen === "quiz" && questions[currentQuestionIndex] && !isLoading && (
          <QuizInterface
            question={questions[currentQuestionIndex]}
            questionNumber={currentQuestionIndex + 1}
            totalQuestions={config?.mode === "daily" ? 1 : config?.mode === "quick" ? 5 : 3}
            onSubmit={handleAnswerSubmit}
            questionTime={timer.currentQuestionTime}
            formatTime={timer.formatTime}
          />
        )}

        {screen === "feedback" && currentQuestion && (
          <FeedbackScreen
            question={currentQuestion}
            userAnswer={userAnswers[String(currentQuestion.id)]}
            onNext={handleNext}
            isLastQuestion={
              currentQuestionIndex === (config?.mode === "daily" ? 0 : config?.mode === "quick" ? 4 : 2)
            }
            evaluation={currentEvaluation ?? undefined}
          />
        )}

        {screen === "results" && (
          <ResultsScreen
            questions={questions}
            userAnswers={userAnswers}
            detailedResults={detailedResults}
            onRestart={handleRestart}
          />
        )}
      </div>
    </div>
  )
}
