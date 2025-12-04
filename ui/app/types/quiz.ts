export type QuestionType =
  | "mcq"
  | "true_false"
  | "short_answer"
  | "open_ended"
  | "scenario"

export interface QuestionSource {
  documentName?: string
  page?: number
  passageId?: string
  snippet?: string
  [key: string]: any
}

export interface Question {
  rationale: string
  id?: string | number
  topic?: string | null
  level?: string | null

  type: QuestionType
  stem: string
  options?: string[]

  // backend’ten gelen ham cevap (string / boolean vs.)
  answer?: string | boolean | null

  // ✅ UI’nin kullandığı normalize cevap
  correctAnswer?: string | string[]

  // 🔹 Artık zorunlu değil + obje/string olabiliyor
  source?: QuestionSource | string | null

  scenario?: string
  steps?: any[]
  meta?: Record<string, any>
}
