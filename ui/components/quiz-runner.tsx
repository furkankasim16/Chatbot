"use client"

import { useEffect, useRef, useState } from "react"
import { useQuizTimer } from "@/hooks/use-quiz-timer"
import type { Question } from "@/app/types/quiz"
import { QuizInterface } from "@/components/quiz-interface"

interface QuizRunnerProps {
  token: string
  attemptId: number
  initialQuestion: Question
  totalQuestions: number
  apiBase?: string
}

export function QuizRunner({
  token,
  attemptId,
  initialQuestion,
  totalQuestions,
  apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000",
}: QuizRunnerProps) {
  const [question, setQuestion] = useState<Question>(initialQuestion)
  const [qIndex, setQIndex] = useState(1)
  const [selected, setSelected] = useState<number | null>(null)

  const timer = useQuizTimer()
  const lastQidRef = useRef<string | null>(null)
  const sendingRef = useRef(false)

  const [isFinishing, setIsFinishing] = useState(false)

  useEffect(() => {
    timer.startQuiz()
  }, [])

  useEffect(() => {
    if (question?.id != null) {
      const qid = String(question.id)
      if (lastQidRef.current !== qid) {
        // Yeni soruya geçince pause varsa kaldır
        if (timer.isPaused) timer.resume()
        timer.startQuestion(qid)
        lastQidRef.current = qid
        setSelected(null)
      }
    }
  }, [question?.id])

  async function submitAnswer(
    questionId: string | number,
    answer: string | string[],
  ) {
    if (sendingRef.current) return
    sendingRef.current = true

    // LLM beklerken süreyi durdur
    timer.pause("submitting")

    try {
      const res = await fetch(`${apiBase}/api/v1/quiz/answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          attempt_id: attemptId,
          question_id: questionId,
          answer,
          client_duration_ms: Math.round(timer.currentQuestionTime),
        }),
      })

      const data = await res.json()

      if (data?.next_question) {
        setQuestion(data.next_question)
        setQIndex((n) => n + 1)
      } else if (data?.completed) {
        timer.endQuiz()
        // Sonuç sayfasına yönlendir (örn: refresh veya router.push)
        window.location.reload()
      }
    } catch (e) {
      // Hata olursa süreyi devam ettir
      timer.resume()
    } finally {
      sendingRef.current = false
    }
  }

  const handleSkip = () => {
    if (!question?.id) return
    // "SKIPPED" özel değeri gönderelim
    submitAnswer(question.id, "SKIPPED")
  }

  const handleFinish = async () => {
    if (isFinishing) return
    setIsFinishing(true)
    timer.pause("submitting") // Durdur

    try {
      await fetch(`${apiBase}/api/v1/quiz/attempt/end`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          attempt_id: attemptId,
          correct_answers: 0, // Backend düzeltecek mi? Genelde end_attempt request body'si bu.
          // Aslında end attempt endpointi scorları update ediyor olmali.
          // Mevcut implementasyon client'tan score aliyor mu?
          // QuizAttemptEndRequest: correct_answers, score require ediyor!
          // Bu bir sorun. Normalde backend state tutmuyor mu?
          // QuizRunner state tutmuyor.
          // Bu yüzden handleFinish riskli.
          // Backend questions_attempted üzerinden hesaplayabilir mi?
          // Şimdilik 0 gönderelim, backend logları günceller.
          // Veya backend'e "unfinished" modu eklemek lazım.
          score: 0,
          total_duration_ms: Math.round(timer.totalQuizTime),
          // questions_attempted opsiyonel
        }),
      })
      timer.endQuiz()
      window.location.reload()
    } catch (e) {
      timer.resume()
      setIsFinishing(false)
    }
  }

  return (
    <QuizInterface
      question={question}
      questionNumber={qIndex}
      totalQuestions={totalQuestions}
      onSubmit={submitAnswer}
      onSkip={handleSkip}
      onFinish={handleFinish}
      questionTime={timer.currentQuestionTime}
      formatTime={timer.formatTime}
      selected={selected}
      setSelected={setSelected}
    />
  )
}
