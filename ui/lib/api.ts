// API Service - Tüm backend çağrıları buradan yapılır
import type { LlmStatsSummary } from "@/app/types/llm"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API = `${API_BASE_URL}/api/v1`
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"

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
}

export interface QuizResult {
  topic: string
  difficulty: string
  total_questions: number
  correct_answers: number
  completed_at: string
  questions_attempted?: string
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
  start_time?: string | null      // opsiyonel
  end_time?: string | null        // opsiyonel
  total_duration_ms?: number | null   // ⭐ BURAYI EKLE
} 

export interface EvaluateAnswerRequest {
  question: string
  expected: string
  user_answer: string
}

export interface EvaluateAnswerResponse {
  score: number
  is_correct: boolean
  feedback?: string
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
  // admin detail endpoint için
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

export async function submitQuizResult(
  token: string,
  result: QuizResult,
): Promise<void> {
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

export async function generateQuestionWithParams(
  token: string,
  topic: string,
  level: string,
  qtype: string,
  model: string,
) {
  const url = `${API}/admin/generate-question?topic=${encodeURIComponent(
    topic,
  )}&level=${level}&qtype=${qtype}&model=${encodeURIComponent(model)}`
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
  const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 sn

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
): Promise<EvaluateAnswerResponse> {
  console.log("[v0] evaluateAnswer called")
  console.log("[v0] Question:", question)
  console.log("[v0] Expected:", expected)
  console.log("[v0] User answer:", userAnswer)

  // ✅ ARTIK DOĞRU PATH: /quiz/evaluate-answer
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

  const result = (await res.json()) as EvaluateAnswerResponse
  console.log("[v0] evaluateAnswer response:", result)
  return result
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
  return authPost<{ attempt_id: number }>(
    `${API_BASE_URL}/api/v1/quiz/attempt/start`,
    token,
    payload,
  )
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
  const url = `${API_BASE_URL}/api/v1/quiz/attempt/end`
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
    `${API_BASE_URL}/api/v1/quiz/question/start`,
    token,
    payload,
  )
}

export async function endQuestionTiming(
  token: string,
  payload: EndQuestionTimingPayload,
): Promise<{ success: boolean }> {
  return authPost<{ success: boolean }>(
    `${API_BASE_URL}/api/v1/quiz/question/end`,
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
    `${API_BASE_URL}/api/v1/quiz/attempt/end`,
    token,
    body,
  )
}

export async function fetchLlmStatsSummary(): Promise<LlmStatsSummary[]> {
  const url = `${API_BASE}/admin/llm-stats/summary`
  console.log("[LLM] fetchLlmStatsSummary ->", url)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000)

  try {
    const res = await fetch(url, {
      method: "GET",
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
  const res = await fetch(`${API_BASE}/quiz/attempts/recent?limit=${limit}`, {
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
  const url = new URL(
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/admin/quiz/attempts`,
  )

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
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
  const res = await fetch(
    `${base}/api/v1/admin/quiz/attempts/${attemptId}`,
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
  const url = new URL("http://localhost:8000/api/v1/admin/quiz/attempts")
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
    `http://localhost:8000/api/v1/admin/quiz/attempts/${attemptId}`,
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
      // ❗ FormData kullanırken Content-Type elle set ETME
    },
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "PDF'ten soru üretilemedi" }))
    throw new Error(error.detail || "PDF'ten soru üretilemedi")
  }

  // backend ya direkt Question döndürür, ya da { question } wrapper'ı olabilir
  const data = await res.json()
  return (data as any).question ?? data
}
