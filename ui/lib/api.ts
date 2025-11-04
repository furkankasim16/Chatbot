// API Service - Tüm backend çağrıları buradan yapılır

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API = `${API_BASE_URL}/api/v1`

export interface Question {
  id?: string
  type: "mcq" | "true_false" | "short_answer" | "scenario" | "open_ended" | "short" | "senaryo" | "open"
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

  // ⏱️ Quiz bazlı süreler (ms)
  total_quiz_duration_ms: number
  avg_quiz_duration_ms: number

  // ⏱️ Soru bazlı süreler
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
  // Yeni: soru bazlı detaylar (JSON string olarak)
  questions_attempted?: string
}

export interface QuizAttempt {
  id: number
  username: string
  quiz_date: string | null
  topic: string
  difficulty: string
  total_questions: number
  correct_answers: number
  score: number
  questions_attempted?: string | any[]
}


export interface EvaluateAnswerRequest {
  question: string
  expected: string
  user_answer: string
}

export interface EvaluateAnswerResponse {
  score: number // 1-5 arası
  is_correct: boolean // 4-5 puan ise true
  feedback?: string // Opsiyonel geri bildirim
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




const MOCK_QUESTIONS: Question[] = [
  {
    id: "1",
    type: "mcq",
    topic: "React",
    level: "beginner",
    stem: "What is the purpose of useState in React?",
    choices: ["To manage component state", "To fetch data", "To style components", "To route pages"],
    answer_index: 0,
    rationale: "useState is a React Hook that lets you add state to functional components.",
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
    rationale: "JavaScript is an interpreted language, not a compiled language.",
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
    rationale: "API stands for Application Programming Interface, which allows different software to communicate.",
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

// Get available topics
export async function getTopics() {
  const res = await fetch(`${API}/questions/topics`)
  if (!res.ok) throw new Error("Failed to fetch topics")
  return res.json() as Promise<{ topics: Record<string, number> }>
}

// Generate quiz for a topic
export async function generateQuiz(topic: string, level = "beginner", n = 5, useOllama = false, qtype: string = "mcq") {
  const res = await fetch(`${API}/quiz/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, level, n, use_ollama: useOllama, qtype }),
  });
  if (!res.ok) throw new Error(`Failed to generate quiz: ${res.status} ${res.statusText}`);
  return res.json() as Promise<{ items: Question[]; shuffle: boolean }>;
}

// Get random question (for Daily Question)
export async function getRandomQuestion(topic?: string, level?: string) {
  const params = new URLSearchParams()
  if (topic) params.append("topic", topic)
  if (level) params.append("level", level)
  const res = await fetch(`${API}/questions/random?${params}`)
  if (!res.ok) throw new Error(`Failed to fetch random question: ${res.status} ${res.statusText}`)
  return res.json() as Promise<Question>
}

// Generate a new question
export async function generateQuestion(topic: string, level = "beginner", qtype = "mcq"): Promise<Question> {
  const res = await fetch(
    `${API}/questions/generate?topic=${encodeURIComponent(topic)}&level=${level}&qtype=${qtype}`,
    { method: "POST" },
  )
  if (!res.ok) throw new Error("Failed to generate question")
  return res.json()
}

// Get all questions (for debugging)
export async function getAllQuestions() {
  const res = await fetch(`${API}/questions?limit=1000`)
  if (!res.ok) throw new Error("Failed to fetch questions")
  return res.json() as Promise<Question[]>
}

// Search in documents
export async function searchDocuments(query: string) {
  const res = await fetch(`${API}/search?q=${encodeURIComponent(query)}`)
  if (!res.ok) throw new Error("Failed to search documents")
  return res.json()
}

// Get questions from DB
export async function getQuestionsFromDB(topic: string, level: string, count: number) {
  const out: Question[] = []
  const exclude: string[] = []
  for (let i = 0; i < count; i++) {
    const params = new URLSearchParams({ topic, level })
    if (exclude.length) params.append("exclude", exclude.join(","))
    const res = await fetch(`${API}/questions/random?${params}`)
    if (!res.ok) throw new Error(`Failed to fetch question: ${res.status} ${res.statusText}`)
    const q = (await res.json()) as Question
    out.push(q)
    if (q.id) exclude.push(String(q.id))
    if (i < count - 1) await new Promise(r => setTimeout(r, 100)) // ritim
  }
  return out
}

// Login
export async function login(username: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"},
    body,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Giriş başarısız" }));
    throw new Error(error.detail || "Kullanıcı adı veya şifre hatalı");
  }

  return res.json();
}


// Register
export async function register(username: string, email: string, password: string) {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  })
  if (!res.ok) throw new Error("Bu kullanıcı adı veya e-posta zaten kullanılıyor")
  return res.json()
}

// Get user stats
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

// Submit quiz result
export async function submitQuizResult(token: string, result: QuizResult): Promise<void> {
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

// Generate random question (Admin only)
export async function generateRandomQuestion(token: string): Promise<Question> {
  const res = await fetch(`${API}/admin/generate-random-question`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Soru üretilemedi" }))
    throw new Error(error.detail || "Soru üretilemedi")
  }

  return res.json()
}

// Generate question with parameters (Admin only)
export async function generateQuestionWithParams(token: string, topic: string, level: string, qtype: string) {
  const res = await fetch(`${API}/admin/generate-question?topic=${encodeURIComponent(topic)}&level=${level}&qtype=${qtype}`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Soru üretilemedi")
  return res.json()
}


async function authPost<T>(url: string, token: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let info: any = null;
    try {
      info = await res.json();
    } catch {
      info = await res.text();
    }
    console.error("[API] POST failed", url, res.status, info);
    throw new Error("Quiz başlatılamadı");
  }

  return (await res.json()) as T;
}

// Delete question (Admin only)
export async function deleteQuestion(token: string, questionId: string): Promise<void> {
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

// Create first admin user (No auth required, only works if no admin exists)
export async function createFirstAdmin(username: string, email: string, password: string): Promise<void> {
  const res = await fetch(`${API}/admin/create-first-admin`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, email, password }),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "İlk admin oluşturulamadı" }))
    throw new Error(error.detail || "İlk admin oluşturulamadı")
  }
}

// Get all user activity (Admin only)
export async function getUserActivity(token: string): Promise<QuizAttempt[]> {
  const res = await fetch(`${API}/admin/user-activity`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Kullanıcı aktivitesi yüklenemedi")
  return res.json()
}

// Evaluate answer for open-ended and scenario questions
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

  const res = await fetch(`${API}/evaluate-answer`, {
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
    console.error("[v0] evaluateAnswer error response:", errorText)
    throw new Error("Cevap değerlendirilemedi")
  }

  const result = await res.json()
  console.log("[v0] evaluateAnswer response:", result)
  return result
}

// Send chat message
export async function sendChatMessage(token: string, message: string, context?: string): Promise<ChatResponse> {
  console.log("[v0] sendChatMessage called")
  console.log("[v0] API URL:", `${API}/chat`)
  console.log("[v0] Message:", message)
  console.log("[v0] Context:", context)

  // Request body'yi oluştur
  const requestBody = {
    message: message,
    ...(context && { context: context }),
  }

  console.log("[v0] Request body:", JSON.stringify(requestBody))

  // AbortController ile timeout kontrolü
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120000) // 120 saniye timeout

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
      throw new Error(`Mesaj gönderilemedi: ${res.status} ${errorText}`)
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
  payload: StartQuizAttemptPayload
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
  // 🔥 Yeni
  questions_attempted?: string
}

export async function endQuizTiming(
  token: string,
  body: EndQuizTimingPayload
) {
  const res = await fetch("http://localhost:8000/api/v1/quiz/attempt/end", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text()
    console.error("[v0] endQuizTiming failed:", res.status, text)
    throw new Error(`Failed to finalize quiz attempt: ${res.status} ${text}`)
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
  payload: StartQuestionTimingPayload
): Promise<{ timing_id: number }> {
  return authPost<{ timing_id: number }>(
    `${API_BASE_URL}/api/v1/quiz/question/start`,
    token,
    payload
  )
}

export async function endQuestionTiming(
  token: string,
  payload: EndQuestionTimingPayload
): Promise<{ success: boolean }> {
  return authPost<{ success: boolean }>(
    `${API_BASE_URL}/api/v1/quiz/question/end`,
    token,
    payload
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
  body: FinishQuizAttemptPayload
) {
  return authPost("/quiz/attempt/end", token, body)
}