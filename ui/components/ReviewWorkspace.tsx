"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Loader2 } from "lucide-react"
import { sendChatTurn, type ChatMessage } from "@/lib/api"
import { parseReviewInput, type ParsedInput } from "@/lib/parseReviewInput"
import { handleChatActions } from "@/lib/chatActions"

type ReviewCardModel = {
  pass: boolean
  score: number
  strengths: string[]
  gaps: string[]
  betterAnswer?: string
  shortReply?: string
}

function ReviewResultCard({
  review,
  onQuizFromGaps,
  onQuizFromTopic,
}: {
  review: ReviewCardModel
  onQuizFromGaps: () => void
  onQuizFromTopic: () => void
}) {
  const label =
    review.score >= 8
      ? "Çok iyi"
      : review.score >= 6
      ? "Geçer"
      : review.score >= 4
      ? "Geliştirilmeli"
      : "Yetersiz"

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-lg flex items-center gap-2">
            <span>{review.pass ? "✅" : "❌"}</span>
            <span className="font-semibold">Review Sonucu</span>
          </div>
          {review.shortReply && (
            <p className="text-sm opacity-80 whitespace-pre-wrap mt-1">
              {review.shortReply}
            </p>
          )}
        </div>

        <div className="text-right">
          <div className="text-sm font-semibold">Puan: {review.score}/10</div>
          <div className="text-xs opacity-70">{label}</div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-xs font-semibold mb-1">Güçlü yönler</p>
          {review.strengths.length > 0 ? (
            <ul className="list-disc pl-5 text-sm space-y-1">
              {review.strengths.map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm opacity-60">—</p>
          )}
        </div>

        <div>
          <p className="text-xs font-semibold mb-1">Eksikler</p>
          {review.gaps.length > 0 ? (
            <ul className="list-disc pl-5 text-sm space-y-1">
              {review.gaps.map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm opacity-60">—</p>
          )}
        </div>
      </div>

      {review.betterAnswer && (
        <details className="rounded border p-3 bg-muted/30">
          <summary className="cursor-pointer text-sm font-semibold">
            Daha iyi örnek cevap
          </summary>
          <p className="text-sm whitespace-pre-wrap mt-2">{review.betterAnswer}</p>
        </details>
      )}

      <div className="flex flex-wrap gap-2 pt-2">
        <Button
          size="sm"
          variant="secondary"
          onClick={onQuizFromGaps}
          disabled={review.gaps.length === 0}
        >
          Eksiklerimden 5 soru sor
        </Button>
        <Button size="sm" variant="outline" onClick={onQuizFromTopic}>
          Bu konudan 5 soru sor
        </Button>
      </div>
    </Card>
  )
}

function ImprovedAnswerCard({
  answer,
  onApply,
  onClear,
}: {
  answer: string
  onApply: () => void
  onClear: () => void
}) {
  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">✨ Geliştirilmiş cevap</p>
          <p className="text-xs opacity-70">
            Tek tıkla input’a uygulayıp tekrar değerlendirebilirsin.
          </p>
        </div>

        <div className="flex gap-2">
          <Button size="sm" onClick={onApply}>
            Input’a uygula
          </Button>
          <Button size="sm" variant="outline" onClick={onClear}>
            Temizle
          </Button>
        </div>
      </div>

      <Card className="p-3 bg-muted/30">
        <p className="text-sm whitespace-pre-wrap">{answer}</p>
      </Card>
    </Card>
  )
}

function ClarifyingQuestionsCard({
  questions,
  selected,
  onToggle,
  onAppendToInput,
  onClear,
}: {
  questions: string[]
  selected: Record<string, boolean>
  onToggle: (q: string) => void
  onAppendToInput: (qs: string[]) => void
  onClear: () => void
}) {
  const selectedList = questions.filter((q) => selected[q])

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">🧩 Eksiklerini netleştirelim</p>
          <p className="text-xs opacity-70">
            Aşağıdaki soruları cevaplayıp input’a ekleyebilirsin.
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => onAppendToInput(selectedList)}
            disabled={selectedList.length === 0}
          >
            Seçilenleri input’a ekle
          </Button>
          <Button size="sm" variant="outline" onClick={onClear}>
            Temizle
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {questions.map((q) => (
          <label key={q} className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              className="mt-1"
              checked={!!selected[q]}
              onChange={() => onToggle(q)}
            />
            <span className="whitespace-pre-wrap">{q}</span>
          </label>
        ))}
      </div>

      {selectedList.length === 0 ? (
        <p className="text-[11px] opacity-60">İpucu: En belirsiz 1–3 soruyu seç.</p>
      ) : (
        <p className="text-[11px] opacity-60">Seçili: {selectedList.length}</p>
      )}
    </Card>
  )
}

export function ReviewWorkspace({
  token,
  topic,
  level,
  history,
  setHistory,
}: {
  token: string
  topic: string
  level: string
  history: ChatMessage[]
  setHistory: (v: ChatMessage[] | ((p: ChatMessage[]) => ChatMessage[])) => void
}) {
  const [draft, setDraft] = useState("")
  const [parsed, setParsed] = useState<ParsedInput | null>(null)

  const [review, setReview] = useState<ReviewCardModel | null>(null)
  const [improvedAnswer, setImprovedAnswer] = useState<string | null>(null)

  const [clarifyingQuestions, setClarifyingQuestions] = useState<string[] | null>(null)
  const [selectedQuestions, setSelectedQuestions] = useState<Record<string, boolean>>({})

  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasReview = !!review

  useEffect(() => {
    setParsed(parseReviewInput(draft))
  }, [draft])

  useEffect(() => {
    if (!clarifyingQuestions) {
      setSelectedQuestions({})
      return
    }
    const init: Record<string, boolean> = {}
    clarifyingQuestions.forEach((q) => (init[q] = true))
    setSelectedQuestions(init)
  }, [clarifyingQuestions])

  const runReview = async () => {
    const p = parseReviewInput(draft)
    if (!p) return

    setReview(null)
    setImprovedAnswer(null)
    setClarifyingQuestions(null)

    const userMsg: ChatMessage = { role: "user", content: draft.trim() }
    setHistory((prev) => [...prev, userMsg])
    setIsBusy(true)
    setError(null)

    try {
      const message =
        p.kind === "qa" ? `SORU: ${p.question}\nCEVAP: ${p.answer}` : p.answer

      const resp = await sendChatTurn(token, {
        mode: "review",
        topic,
        level,
        message,
        history,
      })

      setHistory((prev) => [...prev, { role: "assistant", content: resp.reply }])

      handleChatActions(resp)

      const actions = (resp as any)?.actions
      const reviewPayload = Array.isArray(actions)
        ? actions.find((a: any) => a?.type === "review_result")?.payload
        : null

      if (reviewPayload) {
        const score = Number(reviewPayload.score ?? 0)
        setReview({
          pass: score >= 6,
          score,
          strengths: reviewPayload.strengths ?? [],
          gaps: reviewPayload.gaps ?? [],
          betterAnswer: reviewPayload.better_answer,
          shortReply: resp.reply,
        })
      } else {
        setReview({
          pass: true,
          score: 0,
          strengths: [],
          gaps: [],
          betterAnswer: undefined,
          shortReply: resp.reply,
        })
      }
    } catch (e: any) {
      setError(e.message || "Review başarısız")
    } finally {
      setIsBusy(false)
    }
  }

  const runAction = async (
    type:
      | "improve"
      | "ask_gaps"
      | "new_question"
      | "quiz_from_gaps"
      | "quiz_topic"
  ) => {
    if (type !== "new_question" && type !== "quiz_from_gaps" && type !== "quiz_topic") {
      if (!draft.trim()) return
    }

    setIsBusy(true)
    setError(null)

    try {
      const message =
        type === "new_question"
          ? `ACTION:${type}\nINPUT:__EMPTY__`
          : type === "quiz_from_gaps"
          ? `ACTION:${type}\nINPUT:${JSON.stringify({ n: 5, gaps: review?.gaps ?? [] })}`
          : type === "quiz_topic"
          ? `ACTION:${type}\nINPUT:${JSON.stringify({ n: 5 })}`
          : `ACTION:${type}\nINPUT:${draft.trim()}`

      const resp = await sendChatTurn(token, {
        mode: "review",
        topic,
        level,
        message,
        history,
      })

      // improve/ask_gaps'ta chat'i kirletmeyelim (kartlar gösterecek)
      if (!["improve", "ask_gaps"].includes(type)) {
        setHistory((prev) => [...prev, { role: "assistant", content: resp.reply }])
      }

      handleChatActions(resp)

      const actions = (resp as any)?.actions

      if (type === "improve") {
        const improved = Array.isArray(actions)
          ? actions.find((a: any) => a?.type === "improved_answer")?.payload?.answer
          : null
        setImprovedAnswer((improved || resp.reply || "").trim())
      }

      if (type === "ask_gaps") {
        const qs = Array.isArray(actions)
          ? actions.find((a: any) => a?.type === "clarifying_questions")?.payload?.questions
          : null
        const list = Array.isArray(qs) ? qs : []
        setClarifyingQuestions(
          list.length ? list : ["Cevabının hangi kısmından emin değilsin?"]
        )
      }
      // new_question / quiz_* aksiyonları: handleChatActions start_quiz yakalar
    } catch (e: any) {
      setError(e.message || "Aksiyon başarısız")
    } finally {
      setIsBusy(false)
    }
  }

  const appendQuestionsToInput = (qs: string[]) => {
    if (qs.length === 0) return
    const block =
      "\n\n---\nEksikleri netleştirmek için yanıtlarım:\n" +
      qs.map((q) => `- ${q}\n  Cevap: `).join("\n")
    setDraft((prev) => (prev.trim() ? prev + block : block.trim()))
  }

  return (
    <div className="flex-1 flex flex-col">
      <Card className="flex-1 flex flex-col p-4 gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs opacity-70">
            <span className="font-semibold">Review</span>
            {parsed?.kind === "qa" ? (
              <span className="px-2 py-0.5 rounded border">Soru + Cevap algılandı ✅</span>
            ) : parsed?.kind === "answerOnly" ? (
              <span className="px-2 py-0.5 rounded border">
                Sadece cevap (son soru kullanılabilir)
              </span>
            ) : null}
          </div>

          <Card className="p-3 bg-muted/20 border-dashed opacity-80">
            <p className="text-[11px] opacity-70 mb-1">Örnek</p>
            <p className="text-xs whitespace-pre-wrap opacity-80">
              {
                "SORU: SQL Injection nedir?\nCEVAP: SQL Injection, kullanıcı girdileri filtrelenmeden sorguya eklendiğinde saldırganın veritabanını manipüle edebilmesidir..."
              }
            </p>
          </Card>

          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={`SORU: ...\nCEVAP: ...\n\nveya sadece cevabını yaz`}
            className="min-h-[130px]"
          />

          <div className="flex flex-wrap gap-2">
            <Button onClick={runReview} disabled={!draft.trim() || isBusy}>
              {isBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Değerlendir"}
            </Button>

            <Button
              variant="secondary"
              onClick={() => runAction("improve")}
              disabled={!draft.trim() || isBusy || !hasReview}
            >
              Cevabımı geliştir
            </Button>

            <Button
              variant="secondary"
              onClick={() => runAction("ask_gaps")}
              disabled={!draft.trim() || isBusy || !hasReview}
            >
              Eksiklerimi sor
            </Button>

            <Button
              variant="outline"
              onClick={() => runAction("new_question")}
              disabled={isBusy}
            >
              Bu konudan yeni soru sor
            </Button>
          </div>

          {!hasReview && (
            <p className="text-[11px] opacity-60">
              İpucu: “Cevabımı geliştir” ve “Eksiklerimi sor” için önce değerlendirme yap.
            </p>
          )}

          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>

        {improvedAnswer && (
          <ImprovedAnswerCard
            answer={improvedAnswer}
            onApply={() => setDraft(improvedAnswer)}
            onClear={() => setImprovedAnswer(null)}
          />
        )}

        {clarifyingQuestions && (
          <ClarifyingQuestionsCard
            questions={clarifyingQuestions}
            selected={selectedQuestions}
            onToggle={(q) =>
              setSelectedQuestions((prev) => ({ ...prev, [q]: !prev[q] }))
            }
            onAppendToInput={(qs) => appendQuestionsToInput(qs)}
            onClear={() => setClarifyingQuestions(null)}
          />
        )}

        {review && (
          <ReviewResultCard
            review={review}
            onQuizFromGaps={() => runAction("quiz_from_gaps")}
            onQuizFromTopic={() => runAction("quiz_topic")}
          />
        )}
      </Card>
    </div>
  )
}
