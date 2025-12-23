"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Trophy,
  RotateCcw,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Sparkles,
} from "lucide-react"
import type { Question } from "@/app/types/quiz"

interface QuestionResultDetail {
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

interface ResultsScreenProps {
  questions: Question[]
  userAnswers: Record<string, string | string[]>
  onRestart: () => void
  detailedResults?: QuestionResultDetail[] | null
}

function normalizeAnswer(value: string | boolean | null | undefined): string {
  let str: string

  if (typeof value === "string") {
    str = value
  } else if (typeof value === "boolean") {
    str = value ? "true" : "false"
  } else {
    str = ""
  }

  return str
    .toLowerCase()
    .trim()
    .replace(/[.,!?;:]/g, "")
    .replace(/\s+/g, " ")
}

function calculateSimilarity(str1: string, str2: string): number {
  const s1 = normalizeAnswer(str1)
  const s2 = normalizeAnswer(str2)
  if (s1 === s2) return 100

  const longer = s1.length > s2.length ? s1 : s2
  const shorter = s1.length > s2.length ? s2 : s1
  if (longer.length === 0) return 100

  const editDistance = levenshteinDistance(longer, shorter)
  return ((longer.length - editDistance) / longer.length) * 100
}

function levenshteinDistance(str1: string, str2: string): number {
  const matrix: number[][] = []
  for (let i = 0; i <= str2.length; i++) matrix[i] = [i]
  for (let j = 0; j <= str1.length; j++) matrix[0][j] = j

  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      matrix[i][j] =
        str2[i - 1] === str1[j - 1]
          ? matrix[i - 1][j - 1]
          : Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1,
          )
    }
  }
  return matrix[str2.length][str1.length]
}

export function ResultsScreen({
  questions,
  userAnswers,
  onRestart,
  detailedResults,
}: ResultsScreenProps) {

  const getDetail = (qid: string) =>
    detailedResults?.find((d) => d.question_id === qid)

  const autoGraded = questions.filter(
    (q) => q.type === "mcq" || q.type === "true_false"
  )

  const manualReview = questions.filter(
    (q) => q.type === "open_ended" || q.type === "scenario" || q.type === "short_answer"
  )

  const correctCount = autoGraded.reduce((acc, q) => {
    const key = String(q.id)
    const detail = getDetail(key)
    if (detail) return detail.is_correct ? acc + 1 : acc

    const userAnswer = userAnswers[key]
    if (!userAnswer) return acc

    const rawCorrect =
      typeof q.correctAnswer === "string"
        ? q.correctAnswer
        : Array.isArray(q.correctAnswer)
          ? q.correctAnswer[0]
          : q.answer ?? ""

    if (!rawCorrect) return acc

    let isCorrect = false

    if (Array.isArray(userAnswer)) {
      isCorrect =
        JSON.stringify([...userAnswer].sort()) ===
        JSON.stringify([rawCorrect].sort())
    } else if (q.type === "mcq" || q.type === "true_false") {
      isCorrect = normalizeAnswer(userAnswer) === normalizeAnswer(rawCorrect)
    } else {
      isCorrect = calculateSimilarity(String(userAnswer), String(rawCorrect)) >= 85
    }

    return isCorrect ? acc + 1 : acc
  }, 0)

  const percentage = autoGraded.length
    ? Math.round((correctCount / autoGraded.length) * 100)
    : 0

  const status =
    percentage >= 80 ? "Mükemmel" : percentage >= 60 ? "İyi" : "Pratik Yapmaya Devam Et";

  return (
    <div className="animate-fade-in space-y-6">

      {/* ---------------- Summary Card ---------------- */}
      <Card className="p-8 space-y-6 text-center">
        <div className="flex justify-center">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center">
            <Trophy className="w-10 h-10 text-primary" />
          </div>
        </div>

        <h2 className="text-3xl font-bold">Quiz Tamamlandı!</h2>
        <p className="text-muted-foreground text-lg">İşte performansın</p>

        <div className="text-6xl font-bold text-primary">%{percentage}</div>
        <p className="text-xl font-semibold">{status}</p>
        <p className="text-muted-foreground">{correctCount} / {autoGraded.length} doğru</p>
      </Card>

      {/* ---------------- AI Evaluation Section ---------------- */}
      {manualReview.length > 0 && detailedResults && (
        <Card className="p-6 space-y-4 border-primary/30 bg-primary/5 mt-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-primary">
            <Sparkles className="w-5 h-5" />
            Yapay Zeka Değerlendirmesi
          </h3>

          {detailedResults
            .filter((d) => manualReview.some((q) => String(q.id) === d.question_id))
            .map((res) => {
              const detail = res;
              return (
                <div key={res.question_id} className="p-4 bg-card border rounded-lg space-y-2">
                  <p className="font-medium">{res.stem}</p>

                  <div className="flex items-center gap-2 text-sm">
                    <Badge className={res.is_correct ? "bg-emerald-500 hover:bg-emerald-600" : "bg-rose-500 hover:bg-rose-600"}>
                      {res.is_correct ? "YZ: Doğru" : "Geliştirilmeli"}
                    </Badge>

                    {res.eval_score !== undefined && (
                      <Badge variant="outline">Puan: {res.eval_score}/5</Badge>
                    )}
                  </div>

                  {/* Rubric Table Display */}
                  {detail.rubric && detail.rubric.length > 0 && (
                    <div className="mt-4 border rounded-md overflow-hidden">
                      <table className="w-full text-sm text-left">
                        <thead className="bg-muted text-muted-foreground uppercase text-xs">
                          <tr>
                            <th className="px-4 py-2">Kriter</th>
                            <th className="px-4 py-2">Puan</th>
                            <th className="px-4 py-2">Geri Bildirim</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {detail.rubric.map((r, idx) => (
                            <tr key={idx} className="bg-card">
                              <td className="px-4 py-2 font-medium">{r.criteria}</td>
                              <td className="px-4 py-2 w-24">
                                <span className={r.score === r.max_score ? "text-emerald-600" : "text-amber-600"}>
                                  {r.score}
                                </span>
                                <span className="text-muted-foreground"> / {r.max_score}</span>
                              </td>
                              <td className="px-4 py-2 text-muted-foreground">{r.feedback}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Old Feedback Display (Fallback) */}
                  {!detail.rubric && detail.eval_feedback && (
                    <div className="mt-3 bg-blue-50 dark:bg-blue-950/20 p-3 rounded text-sm text-blue-700 dark:text-blue-300">
                      <span className="font-semibold">Geri Bildirim: </span>
                      {detail.eval_feedback}
                    </div>
                  )}

                  {/* Source Context Display */}
                  {/* The original eval_feedback display was here, now replaced/moved */}
                  {/* {res.eval_feedback && (
                      <p className="text-xs text-muted-foreground border-l pl-3 italic">
                        {res.eval_feedback}
                      </p>
                    )} */}
                </div>
              )
            })}

          <Button onClick={onRestart} className="w-full mt-6">Yeni Quiz Başlat</Button>
        </Card>
      )}

      {/* ---------------- Answer Review (Auto-Graded) ---------------- */}
      {autoGraded.length > 0 && (
        <Card className="p-6 space-y-4">
          <h3 className="text-lg font-semibold">Cevap İncelemesi</h3>

          {autoGraded.map((q) => {
            const key = String(q.id)
            const userAnswer = userAnswers[key]
            const detail = getDetail(key)

            const rawCorrect =
              typeof q.correctAnswer === "string"
                ? q.correctAnswer
                : Array.isArray(q.correctAnswer)
                  ? q.correctAnswer[0]
                  : q.answer ?? ""

            const isCorrect = detail?.is_correct ?? (
              userAnswer &&
              normalizeAnswer(String(userAnswer)) === normalizeAnswer(String(rawCorrect))
            )

            return (
              <div key={key} className="p-4 rounded-lg border flex gap-3">
                {isCorrect ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-500" />
                )}

                <div className="flex-1">
                  <p className="font-medium">{q.stem}</p>
                  <p className="text-xs text-muted-foreground">
                    Cevabın: {String(userAnswer ?? "Cevap yok")}
                  </p>
                  {!isCorrect && (
                    <p className="text-xs text-muted-foreground">
                      Doğru Cevap: <span className="text-accent">{String(rawCorrect)}</span>
                    </p>
                  )}
                  {q.source_context && (
                    <div className="mt-2 text-xs text-muted-foreground bg-muted/50 p-2 rounded border-l-2 border-primary/20">
                      <span className="font-semibold text-primary/80">Kaynak Bağlamı:</span> {q.source_context}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </Card>
      )
      }
    </div >
  )
}
