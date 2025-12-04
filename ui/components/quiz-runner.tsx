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

  useEffect(() => {
    timer.startQuiz()
  }, [])

  useEffect(() => {
    if (question?.id != null) {
      const qid = String(question.id)
      if (lastQidRef.current !== qid) {
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
        // burada sonuç sayfasına yönlendirebilirsin
      }
    } finally {
      sendingRef.current = false
    }
  }

  return (
    <QuizInterface
      question={question}
      questionNumber={qIndex}
      totalQuestions={totalQuestions}
      onSubmit={submitAnswer}
      questionTime={timer.currentQuestionTime}
      formatTime={timer.formatTime}
      selected={selected}
      setSelected={setSelected}
    />
  )
}
