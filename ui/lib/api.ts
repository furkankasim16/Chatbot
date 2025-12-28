// API Service - Tüm backend çağrıları buradan yapılır
import type { LlmStatsSummary } from "@/app/types/llm"

export type ChatRole = "user" | "assistant" | "system"

export interface ChatMessage {
  role: ChatRole
  content: string
}

export interface ChatModeConfig {
  id: string
  title: string
  description: string
  provider: string
  model: string
  temperature: number
  max_history: number
}

export interface ChatTurnRequest {
  mode: string
  topic?: string | null
  level?: string | null
  message: string
  history?: ChatMessage[]
  session_id?: string | null
  use_rag?: boolean
  language?: string // 🆕 Language
}

export interface ChatTurnResponse {
  mode: string
  topic?: string | null
  level?: string | null
  reply: string
  suggestions?: string[] | null
  raw_model?: string
  usage?: any
  error?: string | null
  session_id?: string
  actions?: { type: string; payload?: any }[] | null
}

export interface ChatJobResponse {
  job_id: string
  status: "queued" | "completed" | "failed" | "started" | "deferred" | "scheduled" | "not_found" | "expired"
  result?: ChatTurnResponse
  waited_ms?: number
  error?: string | null
}

// 🔹 Base URL’leri tek yerde topluyoruz
const API_ROOT = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API = `${API_ROOT}/api/v1`
const CHAT_API = `${API}/chat`

export interface Question {
  id?: string
  type:
  | "mcq"
  | "true_false"
  | "short_answer"
  | "scenario"
  | "open_ended"
  | "short"
  | "senaryo"
  | "open"
  topic: string
  level: string
  stem: string
  choices?: string[]
  answer_index?: number
  answer?: boolean
  expected?: string
  expected_points?: string[]
  rationale: string
  created_at?: string
  source?: {
    doc: string
    chunk: number
    topic: string
  }
  source_model?: string
  source_type?: string
  source_context?: string
}

export interface QuizResponse {
  items: Question[]
  shuffle: boolean
}

export interface TopicsResponse {
  topics: Record<string, number>
}

export interface LoginResponse {
  access_token: string
  token_type: string
  username: string
  is_admin: boolean
  xp?: number
  level?: number
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface TopicStatsEntry {
  correct: number
  total: number
}

export interface UserStats {
  id: number
  total_quizzes: number
  total_questions: number
  correct_answers: number
  last_quiz_date: string | null
  topic_stats: Record<string, TopicStatsEntry>
  total_quiz_duration_ms: number
  avg_quiz_duration_ms: number
  total_questions_timed: number
  total_question_duration_ms: number
  avg_question_duration_ms: number
  recommended_study_topics: string[]
}

export interface QuizResult {
  topic: string
  difficulty: string
  total_questions: number
  correct_answers: number
  completed_at: string
  questions_attempted?: string
  score?: number
}

export interface QuizAttempt {
  id: number
  username: string
  quiz_date: string
  topic: string | null
  difficulty: string | null
  total_questions: number
  correct_answers: number | null
  score: number | null
  questions_attempted?: string | any[]
  start_time?: string | null
  end_time?: string | null
  total_duration_ms?: number | null
}

export interface EvaluateAnswerRequest {
  question: string
  expected: string
  user_answer: string
}

export interface EvaluateAnswerOut {
  is_correct: boolean
  score?: number
  feedback?: string
  rubric?: Array<{
    criteria: string
    score: number
    max_score: number
    feedback: string
  }>
}

export interface ChatRequest {
  message: string
  context?: string
}

export interface ChatResponse {
  response: string
}

export interface QuizStartResponse {
  attempt_id: number
  start_time: string
}

export interface QuizEndResponse {
  attempt_id: number
  total_duration_ms: number
}

export interface QuestionStartResponse {
  timing_id: number
  start_time: string
}

export interface QuestionEndResponse {
  timing_id: number
  duration_ms: number
}

export interface StartQuizAttemptPayload {
  topic: string
  difficulty: string
  total_questions: number
  start_time: string
  mode?: string
}

export interface AuditLog {
  id: number
  user_id: number
  action: string
  details: any
  created_at: string
  username?: string
}

export async function getAuditLogs(
  token: string,
  limit = 200,
): Promise<AuditLog[]> {
  const url = `${API}/admin/audit-logs?limit=${limit}`
  console.log("[ADMIN] getAuditLogs ->", url)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000)

  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })

    console.log("[ADMIN] getAuditLogs status:", res.status)

    if (!res.ok) {
      const text = await res.text().catch(() => "")
      console.error("[ADMIN] getAuditLogs error body:", text)
      throw new Error(text || "Loglar yüklenemedi")
    }

    return res.json()
  } catch (err: any) {
    if (err?.name === "AbortError") {
      console.error("[ADMIN] getAuditLogs timeout (10s)")
      throw new Error("Log isteği zaman aşımına uğradı")
    }
    console.error("[ADMIN] getAuditLogs exception:", err)
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}


export interface AuditStats {
  daily_activity: { date: string; count: number }[]
  action_distribution: { action: string; count: number }[]
}

export async function getAuditStats(token: string): Promise<AuditStats> {
  const res = await fetch(`${API}/admin/audit-stats`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("İstatistikler alınamadı")
  return res.json()
}

export interface QuestionResultDetail {
  question_id: string
  stem: string
  user_answer: string | string[]
  correct_answer: string | string[]
  is_correct: boolean
  eval_score?: number
  eval_feedback?: string
}

export interface QuizAttemptHistoryQuestion {
  question_id: string
  stem: string
  user_answer: string | string[] | null
  correct_answer: string | string[] | null
  is_correct: boolean
  eval_score?: number | null
  eval_feedback?: string | null
}

export interface QuizAttemptHistory {
  id: number
  user_id: number
  username?: string | null
  topic?: string | null
  difficulty?: string | null
  total_questions: number
  correct_answers?: number | null
  score?: number | null
  quiz_date: string
  start_time?: string | null
  end_time?: string | null
  total_duration_ms?: number | null
  questions?: QuizAttemptHistoryQuestion[]
}

export interface AdminQuizAttempt {
  id: number
  user_id: number
  username?: string | null
  topic?: string | null
  difficulty?: string | null
  total_questions: number
  correct_answers?: number | null
  score?: number | null
  quiz_date: string
  start_time?: string | null
  end_time?: string | null
  total_duration_ms?: number | null
}

export interface AdminQuestionAttempt {
  question_id: string
  stem: string
  user_answer: any
  correct_answer: any
  is_correct: boolean
  eval_score?: number | null
  eval_feedback?: string | null
}

export interface AdminQuizAttemptDetail extends AdminQuizAttempt {
  questions: AdminQuestionAttempt[]
}

const MOCK_QUESTIONS: Question[] = [
  {
    id: "1",
    type: "mcq",
    topic: "React",
    level: "beginner",
    stem: "What is the purpose of useState in React?",
    choices: [
      "To manage component state",
      "To fetch data",
      "To style components",
      "To route pages",
    ],
    answer_index: 0,
    rationale:
      "useState is a React Hook that lets you add state to functional components.",
    source: {
      doc: "React Documentation",
      chunk: 1,
      topic: "React Hooks",
    },
  },
  {
    id: "2",
    type: "true_false",
    topic: "JavaScript",
    level: "beginner",
    stem: "JavaScript is a compiled language.",
    answer: false,
    rationale:
      "JavaScript is an interpreted language, not a compiled language.",
    source: {
      doc: "JavaScript Basics",
      chunk: 2,
      topic: "JavaScript Fundamentals",
    },
  },
  {
    id: "3",
    type: "short_answer",
    topic: "Web Development",
    level: "intermediate",
    stem: "What does API stand for?",
    expected: "Application Programming Interface",
    rationale:
      "API stands for Application Programming Interface, which allows different software to communicate.",
    source: {
      doc: "Web Development Guide",
      chunk: 3,
      topic: "APIs",
    },
  },
]

const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true"

// Health check
export async function checkHealth() {
  const res = await fetch(`${API}/health`)
  if (!res.ok) throw new Error("API is not available")
  return res.json()
}

export async function getTopics() {
  const res = await fetch(`${API}/questions/topics`)
  if (!res.ok) throw new Error("Failed to fetch topics")
  return res.json() as Promise<{ topics: Record<string, number> }>
}

export async function generateQuiz(
  topic: string,
  level = "beginner",
  n = 5,
  useOllama = false,
  qtype: string = "mcq",
) {
  const res = await fetch(`${API}/quiz/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, level, n, use_ollama: useOllama, qtype }),
  })
  if (!res.ok)
    throw new Error(`Failed to generate quiz: ${res.status} ${res.statusText}`)
  return res.json() as Promise<{ items: Question[]; shuffle: boolean }>
}

export async function getRandomQuestion(topic?: string, level?: string) {
  const params = new URLSearchParams()
  if (topic) params.append("topic", topic)
  if (level) params.append("level", level)
  const res = await fetch(`${API}/questions/random?${params}`)
  if (!res.ok)
    throw new Error(
      `Failed to fetch random question: ${res.status} ${res.statusText}`,
    )
  return res.json() as Promise<Question>
}

export async function generateQuestion(
  topic: string,
  level = "beginner",
  qtype = "mcq",
): Promise<Question> {
  const res = await fetch(
    `${API}/questions/generate?topic=${encodeURIComponent(
      topic,
    )}&level=${level}&qtype=${qtype}`,
    { method: "POST" },
  )
  if (!res.ok) throw new Error("Failed to generate question")
  return res.json()
}

export async function getAllQuestions() {
  const res = await fetch(`${API}/questions?limit=1000`)
  if (!res.ok) throw new Error("Failed to fetch questions")
  return res.json() as Promise<Question[]>
}

export async function searchDocuments(query: string) {
  const res = await fetch(`${API}/search?q=${encodeURIComponent(query)}`)
  if (!res.ok) throw new Error("Failed to search documents")
  return res.json()
}

export async function getQuestionsFromDB(
  topic: string,
  level: string,
  count: number,
) {
  const out: Question[] = []
  const exclude: string[] = []
  for (let i = 0; i < count; i++) {
    const params = new URLSearchParams({ topic, level })
    if (exclude.length) params.append("exclude", exclude.join(","))
    const res = await fetch(`${API}/questions/random?${params}`)
    if (!res.ok)
      throw new Error(
        `Failed to fetch question: ${res.status} ${res.statusText}`,
      )
    const q = (await res.json()) as Question
    out.push(q)
    if (q.id) exclude.push(String(q.id))
    if (i < count - 1) await new Promise((r) => setTimeout(r, 100))
  }
  return out
}

export async function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  const body = new URLSearchParams()
  body.append("username", username)
  body.append("password", password)

  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Giriş başarısız" }))
    throw new Error(error.detail || "Kullanıcı adı veya şifre hatalı")
  }

  return res.json()
}

export async function register(
  username: string,
  email: string,
  password: string,
) {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  })
  if (!res.ok)
    throw new Error("Bu kullanıcı adı veya e-posta zaten kullanılıyor")
  return res.json()
}

export async function getUserStats(token: string): Promise<UserStats> {
  console.log("[v0] getUserStats called")
  console.log("[v0] API URL:", `${API}/auth/stats`)

  const res = await fetch(`${API}/auth/stats`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  console.log("[v0] getUserStats response status:", res.status)

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error")
    console.error("[v0] getUserStats error:", errorText)
    throw new Error("İstatistikler yüklenemedi")
  }

  const stats = await res.json()
  console.log("[v0] getUserStats response data:", stats)
  return stats
}

export interface SubmitQuizResponse {
  ok: boolean
  xp_gained: number
  new_level: number
  level_up: boolean
  total_xp: number
}

export async function submitQuizResult(
  token: string,
  result: QuizResult,
): Promise<SubmitQuizResponse | null> {
  console.log("[v0] submitQuizResult called")
  console.log("[v0] API URL:", `${API}/auth/submit-result`)
  console.log("[v0] Result data:", result)

  const res = await fetch(`${API}/auth/submit-result`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(result),
  })

  console.log("[v0] submitQuizResult response status:", res.status)

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error")
    console.error("[v0] submitQuizResult error:", errorText)
    throw new Error("Sonuç kaydedilemedi")
  }

  const responseData = await res.json().catch(() => null)
  console.log("[v0] submitQuizResult response data:", responseData)
  return responseData
}

export interface LeaderboardEntry {
  username: string
  xp: number
  level: number
}

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  const res = await fetch(`${API}/auth/leaderboard`)
  if (!res.ok) throw new Error("Liderlik tablosu alınamadı")
  return res.json()
}

export async function generateRandomQuestion(
  token: string,
  model: string,
): Promise<Question> {
  const res = await fetch(
    `${API}/admin/generate-random-question?model=${encodeURIComponent(model)}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Soru üretilemedi" }))
    throw new Error(error.detail || "Soru üretilemedi")
  }

  return res.json()
}

// 🔹 RAG / Knowledge Base
export async function uploadDocument(
  token: string,
  file: File,
  topic: string = "general",
): Promise<any> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("topic", topic)

  const res = await fetch(`${API}/rag/index`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Yükleme başarısız" }))
    throw new Error(error.detail || "Dosya yüklenemedi")
  }

  return res.json()
}

export async function generateQuestionWithParams(
  token: string,
  topic: string,
  level: string,
  qtype: string,
  model: string,
  useRag: boolean = false,
) {
  const url = `${API}/admin/generate-question?topic=${encodeURIComponent(
    topic,
  )}&level=${level}&qtype=${qtype}&model=${encodeURIComponent(model)}&use_rag=${useRag}`
  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Soru üretilemedi")
  return res.json()
}

async function authPost<T>(
  url: string,
  token: string,
  body: unknown,
): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let info: any = null
    try {
      info = await res.json()
    } catch {
      info = await res.text()
    }
    console.error("[API] POST failed", url, res.status, info)
    throw new Error("Quiz başlatılamadı")
  }

  return (await res.json()) as T
}

export async function deleteQuestion(
  token: string,
  questionId: string,
): Promise<void> {
  const res = await fetch(`${API}/admin/questions/${questionId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Soru silinemedi" }))
    throw new Error(error.detail || "Soru silinemedi")
  }
}

export async function createFirstAdmin(
  username: string,
  email: string,
  password: string,
): Promise<void> {
  const res = await fetch(`${API}/admin/create-first-admin`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, email, password }),
  })

  if (!res.ok) {
    const error = await res
      .json()
      .catch(() => ({ detail: "İlk admin oluşturulamadı" }))
    throw new Error(error.detail || "İlk admin oluşturulamadı")
  }
}

export async function getUserActivity(token: string): Promise<QuizAttempt[]> {
  const url = `${API}/admin/user-activity`
  console.log("[ADMIN] getUserActivity ->", url)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000)

  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })

    console.log("[ADMIN] getUserActivity status:", res.status)

    if (!res.ok) {
      const text = await res.text().catch(() => "")
      console.error("[ADMIN] getUserActivity error body:", text)
      throw new Error(
        text || `Kullanıcı aktivitesi yüklenemedi (status: ${res.status})`,
      )
    }

    return res.json()
  } catch (err: any) {
    if (err?.name === "AbortError") {
      console.error("[ADMIN] getUserActivity timeout (10s)")
      throw new Error("Kullanıcı aktivitesi isteği zaman aşımına uğradı")
    }
    console.error("[ADMIN] getUserActivity exception:", err)
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

// 🔹 Evaluate answer for open-ended and scenario questions
export async function evaluateAnswer(
  token: string,
  question: string,
  expected: string,
  userAnswer: string,
): Promise<EvaluateAnswerOut> {
  console.log("[v0] evaluateAnswer called")
  console.log("[v0] Question:", question)
  console.log("[v0] Expected:", expected)
  console.log("[v0] User answer:", userAnswer)

  const res = await fetch(`${API}/quiz/evaluate-answer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      expected,
      user_answer: userAnswer,
    }),
  })

  console.log("[v0] evaluateAnswer response status:", res.status)

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error")
    console.error("[v0] evaluateAnswer not available:", res.status, errorText)
    throw new Error("Cevap değerlendirilemedi")
  }

  const result = (await res.json()) as EvaluateAnswerOut
  console.log("[v0] evaluateAnswer response:", result)
  return result
}

// 🔹 CHAT
export async function sendChatTurn(
  token: string,
  payload: ChatTurnRequest,
): Promise<ChatTurnResponse | ChatJobResponse> {
  const res = await fetch(`${CHAT_API}/turn`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const txt = await res.text().catch(() => "")
    // 429 özel durum
    if (res.status === 429) {
      throw new Error("Sistem şu an çok yoğun, lütfen kısa süre sonra tekrar deneyin.")
    }
    throw new Error(`Mesaj gönderilemedi: ${res.status} ${txt}`)
  }
  return res.json()
}

export async function getChatJobResult(
  token: string,
  jobId: string,
): Promise<ChatJobResponse> {
  const res = await fetch(`${CHAT_API}/result/${jobId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    throw new Error(`Job result check failed: ${res.status}`)
  }
  return res.json()
}

export async function sendChatMessage(
  token: string,
  message: string,
  context?: string,
): Promise<ChatResponse> {
  console.log("[v0] sendChatMessage called")
  console.log("[v0] API URL:", `${API}/chat`)
  console.log("[v0] Message:", message)
  console.log("[v0] Context:", context)

  const requestBody = {
    message: message,
    ...(context && { context: context }),
  }

  console.log("[v0] Request body:", JSON.stringify(requestBody))

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120000)

  try {
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    console.log("[v0] sendChatMessage response status:", res.status)

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unknown error")
      console.error("[v0] sendChatMessage error response:", errorText)
      throw new Error(
        `Mesaj gönderilemedi: ${res.status} ${errorText}`,
      )
    }

    const result = await res.json()
    console.log("[v0] sendChatMessage response:", result)
    return result
  } catch (error) {
    clearTimeout(timeoutId)

    if (error instanceof Error && error.name === "AbortError") {
      console.error("[v0] sendChatMessage timeout")
      throw new Error(
        "İstek zaman aşımına uğradı. Lütfen daha kısa bir mesaj deneyin veya backend'in çalıştığından emin olun.",
      )
    }

    console.error("[v0] sendChatMessage error:", error)
    throw error
  }
}

// Start quiz timing
export async function startQuizTiming(
  token: string,
  payload: StartQuizAttemptPayload,
): Promise<{ attempt_id: number }> {
  return authPost<{ attempt_id: number }>(`${API}/quiz/attempt/start`, token, payload)
}

// 🔹 KNOWLEDGE BASE
export async function scanCorpus(token: string) {
  const res = await fetch(`${API}/admin/knowledge-base/scan`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) throw new Error("Tarama başlatılamadı")
  return res.json()
}

export async function resetKnowledgeBase(token: string) {
  const res = await fetch(`${API}/admin/knowledge-base/reset`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) throw new Error("Sıfırlama başarısız")
  return res.json()
}

// 🔹 Upload PDF explicitly for RAG Indexing
export async function uploadPdfToRag(
  token: string,
  file: File,
  topic: string = "general"
) {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("topic", topic)

  const res = await fetch(`${API}/rag/index`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: formData
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || "PDF yüklenemedi")
  }

  return res.json()
}

// End quiz timing
export interface EndQuizTimingPayload {
  attempt_id: number
  correct_answers: number
  score: number
  client_end_time?: string
  total_duration_ms?: number
  questions_attempted?: string
}

export async function endQuizTiming(
  token: string,
  body: EndQuizTimingPayload,
) {
  const url = `${API}/quiz/attempt/end`
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    console.error("[v0] endQuizTiming failed:", res.status, text)
    throw new Error(
      `Failed to finalize quiz attempt: ${res.status} ${text}`,
    )
  }

  return res.json()
}

export interface StartQuestionTimingPayload {
  attempt_id: number
  question_id: string
  client_start_time?: string
}

export interface EndQuestionTimingPayload {
  timing_id: number
  client_end_time?: string
}

export async function startQuestionTiming(
  token: string,
  payload: StartQuestionTimingPayload,
): Promise<{ timing_id: number }> {
  return authPost<{ timing_id: number }>(
    `${API}/quiz/question/start`,
    token,
    payload,
  )
}

export async function endQuestionTiming(
  token: string,
  payload: EndQuestionTimingPayload,
): Promise<{ success: boolean }> {
  return authPost<{ success: boolean }>(
    `${API}/quiz/question/end`,
    token,
    payload,
  )
}

export interface FinishQuizAttemptPayload {
  attempt_id: number
  correct_answers: number
  score: number
  client_end_time?: string
  total_duration_ms?: number
}

export async function finishQuizAttempt(
  token: string,
  body: FinishQuizAttemptPayload,
) {
  return authPost(
    `${API}/quiz/attempt/end`,
    token,
    body,
  )
}

export async function fetchLlmStatsSummary(token: string): Promise<LlmStatsSummary[]> {
  const url = `${API}/admin/llm-stats/summary`
  console.log("[LLM] fetchLlmStatsSummary ->", url)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000)

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      next: { revalidate: 0 },
      signal: controller.signal,
    })

    console.log("[LLM] fetchLlmStatsSummary status:", res.status)

    if (!res.ok) {
      const text = await res.text().catch(() => "")
      console.error("[LLM] fetchLlmStatsSummary error body:", text)
      throw new Error(
        text || `LLM stats fetch failed (status: ${res.status})`,
      )
    }

    return res.json()
  } catch (err: any) {
    if (err?.name === "AbortError") {
      console.error("[LLM] fetchLlmStatsSummary timeout (10s)")
      throw new Error("LLM istatistik isteği zaman aşımına uğradı")
    }
    console.error("[LLM] fetchLlmStatsSummary exception:", err)
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function getRecentAttempts(
  token: string,
  limit = 10,
): Promise<QuizAttemptHistory[]> {
  const res = await fetch(`${API}/quiz/attempts/recent?limit=${limit}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    throw new Error(`getRecentAttempts failed: ${res.status}`)
  }

  return res.json()
}

export async function adminGetQuizAttempts(
  token: string,
  params?: { user_id?: number; topic?: string; limit?: number; offset?: number },
): Promise<QuizAttemptHistory[]> {
  const url = new URL(`${API}/admin/quiz/attempts`)

  if (params?.user_id != null) url.searchParams.set("user_id", String(params.user_id))
  if (params?.topic) url.searchParams.set("topic", params.topic)
  if (params?.limit != null) url.searchParams.set("limit", String(params.limit))
  if (params?.offset != null) url.searchParams.set("offset", String(params.offset))

  const res = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    throw new Error(`adminGetQuizAttempts failed: ${res.status}`)
  }

  return res.json()
}

// 🔹 Tek attempt + soru detayları
export async function adminGetQuizAttemptDetail(
  token: string,
  attemptId: number,
): Promise<QuizAttemptHistory> {
  const res = await fetch(
    `${API}/admin/quiz/attempts/${attemptId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!res.ok) {
    throw new Error(`adminGetQuizAttemptDetail failed: ${res.status}`)
  }

  return res.json()
}

export async function getAdminQuizAttempts(
  token: string,
  params?: { user_id?: number; topic?: string; limit?: number; offset?: number },
): Promise<AdminQuizAttempt[]> {
  const url = new URL(`${API}/admin/quiz/attempts`)
  if (params?.user_id != null) url.searchParams.set("user_id", String(params.user_id))
  if (params?.topic) url.searchParams.set("topic", params.topic)
  if (params?.limit != null) url.searchParams.set("limit", String(params.limit))
  if (params?.offset != null) url.searchParams.set("offset", String(params.offset))

  const res = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    throw new Error(`getAdminQuizAttempts failed with status ${res.status}`)
  }

  return res.json()
}

export async function getAdminQuizAttemptDetail(
  token: string,
  attemptId: number,
): Promise<AdminQuizAttemptDetail> {
  const res = await fetch(
    `${API}/admin/quiz/attempts/${attemptId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!res.ok) {
    throw new Error(
      `getAdminQuizAttemptDetail failed with status ${res.status}`,
    )
  }

  return res.json()
}

// 🔹 PDF'ten soru üretme
export async function generateQuestionFromPdf(
  token: string,
  file: File,
  options: {
    topic?: string
    level?: string
    qtype?: string
    model?: string
  },
): Promise<Question> {
  const formData = new FormData()
  formData.append("file", file)

  if (options.topic) formData.append("topic", options.topic)
  if (options.level) formData.append("level", options.level)
  if (options.qtype) formData.append("qtype", options.qtype)
  if (options.model) formData.append("model", options.model)

  const res = await fetch(`${API}/admin/generate-from-pdf`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "PDF'ten soru üretilemedi" }))
    throw new Error(error.detail || "PDF'ten soru üretilemedi")
  }

  const data = await res.json()
  return (data as any).question ?? data
}

export interface UpdateQuestionPayload {
  topic?: string
  question_type?: string
  difficulty?: string
  stem?: string
}

export async function updateQuestion(
  id: string | number,
  data: {
    topic?: string
    question_type?: string
    difficulty?: string
    stem?: string
    options?: string[]
    correct_option_indexes?: number[]
  },
  token: string,
) {
  const res = await fetch(`${API}/questions/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw new Error("Question update failed")
  }

  return res.json()
}

// 🔹 Yeni Chat Mode API’leri
export async function getChatModes(token: string): Promise<Record<string, ChatModeConfig>> {
  const res = await fetch(`${CHAT_API}/modes`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Chat modes failed")
  return res.json()
}



export interface StudentStats {
  id: number
  username: string
  email: string
  level: number
  xp: number
  total_quizzes: number
  avg_score: number
}

export async function getStudents(token: string): Promise<StudentStats[]> {
  const res = await fetch(`${API}/admin/students`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Öğrenci listesi alınamadı")
  return res.json()
}


export interface StudentDetail {
  user: {
    id: number
    username: string
    email: string
    level: number
    xp: number
  }
  weak_topics: {
    topic: string
    accuracy: number
    total: number
  }[]
  recent_activity: {
    id: number
    topic: string
    difficulty: string
    score: number
    date: string
  }[]
  all_topics: {
    topic: string
    accuracy: number
    total: number
  }[]
}

export async function getStudentDetails(token: string, userId: number): Promise<StudentDetail> {
  const res = await fetch(`${API}/admin/students/${userId}/details`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Öğrenci detayı alınamadı")
  return res.json()
}

export interface LlmModelInfo {
  id: string
  name: string
  provider: string
}

export async function getAvailableModels(): Promise<LlmModelInfo[]> {
  const res = await fetch(`${CHAT_API}/models`)
  if (!res.ok) throw new Error("Model listesi alınamadı")
  return res.json()
}
