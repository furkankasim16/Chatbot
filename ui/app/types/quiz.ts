// ui/types/quiz.ts
export type QuestionType = "scenario" | "mcq" | "true_false" | "short_answer" | "open_ended";

export interface Question {
  id: string;
  type: QuestionType;
  stem: string;
  options?: string[];
  steps?: { prompt: string }[];
  // Backend’e uyum için geniş tuttuk:
  correctAnswer?: string | string[];  // ← senin kullanımına göre genişletildi
  rationale?: string;
  source?: string;
}
