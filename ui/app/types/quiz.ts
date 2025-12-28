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
  // ek meta alanları için esnek bırakıyoruz
  [key: string]: any
}

export type ScenarioStepAction = "create" | "update" | "delete"

export interface ScenarioStep {
  step_id?: number
  step_type?: QuestionType | string
  stem?: string
  prompt?: string
  max_score?: number

  options?: string[]
  correct_option_indexes?: number[]
  correct_answer_bool?: boolean

  accepted_answers?: string[]
  matching_type?: string
  rubric?: string

  // 🔹 UI-only alanlar
  _clientId?: string            // frontend'de geçici id
  _action?: ScenarioStepAction  // create / update / delete

  [key: string]: any
  source_context?: string;
}

export interface ScenarioQuestionPatch {
  stem?: string
  topic?: string | null
  level?: string | null
  difficulty?: string | null
  scenario?: string          // senaryo açıklaması
  steps?: ScenarioStep[]     // _action alanlı step'ler
  meta?: Record<string, any>
}


export interface Question {
  // backend id
  id?: string | number

  topic?: string | null
  level?: string | null              // UI tarafındaki seviye
  difficulty?: string | null         // backend'ten doğrudan gelebilir

  type: QuestionType                 // UI'nin kullandığı normalize tip
  stem: string                       // soru metni
  options?: string[]                 // mcq için

  rationale: string                  // LLM açıklaması / gerekçe

  // backend’ten gelen ham cevap (string / boolean vs.)
  answer?: string | boolean | null

  // UI’nin kullandığı normalize doğru cevap
  correctAnswer?: string | string[]

  // RAG / PDF kaynağı vs.
  source?: QuestionSource | string | null

  // Senaryo soruları için
  scenario?: string
  steps?: ScenarioStep[]

  meta?: Record<string, any>
  source_context?: string
}

// ✅ Moved from page.tsx to prevent circular deps
export type QuizMode = "quick" | "daily" | "scenario"
export type Difficulty = "beginner" | "intermediate" | "advanced" | "mixed"

export interface QuizConfig {
  mode: QuizMode
  topic: string
  difficulty: Difficulty
  useOllama?: boolean
}
