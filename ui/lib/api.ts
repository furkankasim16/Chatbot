// API Service - Tüm backend çağrıları buradan yapılır

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

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

export interface UserStats {
  total_quizzes: number
  total_questions: number
  correct_answers: number
  last_quiz_date: string | null
  topic_stats: Record<string, { correct: number; total: number }>
}

export interface QuizResult {
  quiz_id?: string
  topic: string
  difficulty: string
  total_questions: number
  correct_answers: number
  completed_at: string
  questions_attempted?: Array<{
    question_id: string
    user_answer: string
    is_correct: boolean
  }>
}

export interface QuizAttempt {
  id: number
  user_id: number
  username: string
  quiz_date: string
  topic: string
  difficulty: string
  total_questions: number
  correct_answers: number
  score: number
  questions_attempted: Array<{
    question_id: string
    user_answer: string
    is_correct: boolean
  }>
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
  if (USE_MOCK_DATA) {
    return { status: "ok (mock)" }
  }

  const res = await fetch(`${API_BASE_URL}/health`)
  if (!res.ok) throw new Error("API is not available")
  return res.json()
}

// Get available topics
export async function getTopics(): Promise<TopicsResponse> {
  if (USE_MOCK_DATA) {
    return {
      topics: {
        React: 5,
        JavaScript: 8,
        "Web Development": 3,
        TypeScript: 4,
      },
    }
  }

  const res = await fetch(`${API_BASE_URL}/topics`)
  if (!res.ok) throw new Error("Failed to fetch topics")
  return res.json()
}

// Generate quiz for a topic
export async function generateQuiz(topic: string, level = "beginner", n = 5): Promise<QuizResponse> {
  if (USE_MOCK_DATA) {
    console.log("[v0] Using mock data for quiz generation")
    return {
      items: MOCK_QUESTIONS.slice(0, n),
      shuffle: true,
    }
  }

  console.log(
    "[v0] Fetching quiz from:",
    `${API_BASE_URL}/quiz?topic=${encodeURIComponent(topic)}&level=${level}&n=${n}`,
  )

  const controller = new AbortController()

  try {
    const res = await fetch(`${API_BASE_URL}/quiz?topic=${encodeURIComponent(topic)}&level=${level}&n=${n}`, {
      method: "POST",
      signal: controller.signal,
    })

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unknown error")
      console.error("[v0] API Error:", errorText)
      throw new Error(`Failed to generate quiz: ${res.status} ${res.statusText}`)
    }

    return res.json()
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Soru üretimi iptal edildi.")
    }
    throw error
  }
}

// Get random question (for Daily Question)
export async function getRandomQuestion(topic?: string, level?: string): Promise<Question> {
  if (USE_MOCK_DATA) {
    console.log("[v0] Using mock data for random question")
    return MOCK_QUESTIONS[0]
  }

  const params = new URLSearchParams()
  if (topic) params.append("topic", topic)
  if (level) params.append("level", level)

  console.log("[v0] Fetching random question from:", `${API_BASE_URL}/questions/random?${params}`)

  const res = await fetch(`${API_BASE_URL}/questions/random?${params}`)

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error")
    console.error("[v0] API Error:", errorText)
    throw new Error(`Failed to fetch random question: ${res.status} ${res.statusText}`)
  }

  return res.json()
}

// Generate a new question
export async function generateQuestion(topic: string, level = "beginner", qtype = "mcq"): Promise<Question> {
  const res = await fetch(
    `${API_BASE_URL}/questions/generate?topic=${encodeURIComponent(topic)}&level=${level}&qtype=${qtype}`,
    { method: "POST" },
  )
  if (!res.ok) throw new Error("Failed to generate question")
  return res.json()
}

// Get all questions (for debugging)
export async function getAllQuestions(): Promise<Question[]> {
  const res = await fetch(`${API_BASE_URL}/questions/all`)
  if (!res.ok) throw new Error("Failed to fetch questions")
  return res.json()
}

// Search in documents
export async function searchDocuments(query: string) {
  const res = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`)
  if (!res.ok) throw new Error("Failed to search documents")
  return res.json()
}

// Get questions from DB
export async function getQuestionsFromDB(topic: string, level: string, count: number): Promise<Question[]> {
  if (USE_MOCK_DATA) {
    console.log("[v0] Using mock data for questions")
    return MOCK_QUESTIONS.slice(0, count)
  }

  console.log("[v0] Fetching questions from DB:", `${API_BASE_URL}/questions/random?topic=${topic}&level=${level}`)

  // Birden fazla soru çekmek için random endpoint'i birden çok kez çağırıyoruz
  const questionPromises = Array.from({ length: count }, () =>
    fetch(`${API_BASE_URL}/questions/random?topic=${encodeURIComponent(topic)}&level=${level}`).then((res) => {
      if (!res.ok) {
        throw new Error(`Failed to fetch question: ${res.status} ${res.statusText}`)
      }
      return res.json()
    }),
  )

  try {
    const questions = await Promise.all(questionPromises)
    return questions
  } catch (error) {
    console.error("[v0] Error fetching questions from DB:", error)
    throw error
  }
}

// Login
export async function login(username: string, password: string): Promise<LoginResponse> {
  const formData = new FormData()
  formData.append("username", username)
  formData.append("password", password)

  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Giriş başarısız" }))
    throw new Error(error.detail || "Kullanıcı adı veya şifre hatalı")
  }

  return res.json()
}

// Register
export async function register(username: string, email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Kayıt başarısız" }))
    throw new Error(error.detail || "Bu kullanıcı adı veya e-posta zaten kullanılıyor")
  }

  return res.json()
}

// Get user stats
export async function getUserStats(token: string): Promise<UserStats> {
  console.log("[v0] getUserStats called")
  console.log("[v0] API URL:", `${API_BASE_URL}/auth/stats`)

  const res = await fetch(`${API_BASE_URL}/auth/stats`, {
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
  console.log("[v0] API URL:", `${API_BASE_URL}/auth/submit-result`)
  console.log("[v0] Result data:", result)

  const res = await fetch(`${API_BASE_URL}/auth/submit-result`, {
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
  const res = await fetch(`${API_BASE_URL}/admin/generate-random-question`, {
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
export async function generateQuestionWithParams(
  token: string,
  topic: string,
  level: string,
  qtype: string,
): Promise<Question> {
  const res = await fetch(
    `${API_BASE_URL}/admin/generate-question?topic=${encodeURIComponent(topic)}&level=${level}&qtype=${qtype}`,
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

// Delete question (Admin only)
export async function deleteQuestion(token: string, questionId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/admin/questions/${questionId}`, {
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
  const res = await fetch(`${API_BASE_URL}/admin/create-first-admin`, {
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
  const res = await fetch(`${API_BASE_URL}/admin/user-activity`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Kullanıcı aktivitesi yüklenemedi" }))
    throw new Error(error.detail || "Kullanıcı aktivitesi yüklenemedi")
  }

  return res.json()
}
