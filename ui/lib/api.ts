// API Service - Tüm backend çağrıları buradan yapılır

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface Question {
  id?: string
  type: "mcq" | "true_false" | "short_answer" | "scenario"
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

  const res = await fetch(`${API_BASE_URL}/quiz?topic=${encodeURIComponent(topic)}&level=${level}&n=${n}`, {
    method: "POST",
  })

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error")
    console.error("[v0] API Error:", errorText)
    throw new Error(`Failed to generate quiz: ${res.status} ${res.statusText}`)
  }

  return res.json()
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
