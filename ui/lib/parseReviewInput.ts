export type ParsedInput =
  | { kind: "qa"; question: string; answer: string }
  | { kind: "answerOnly"; answer: string }

export function parseReviewInput(text: string): ParsedInput | null {
  const t = text.trim()
  if (!t) return null

  const m = t.match(/SORU\s*:\s*([\s\S]+?)\s*CEVAP\s*:\s*([\s\S]+)/i)
  if (m?.[1] && m?.[2]) {
    return { kind: "qa", question: m[1].trim(), answer: m[2].trim() }
  }
  return { kind: "answerOnly", answer: t }
}
