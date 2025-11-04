"use client";
import { useEffect, useRef, useState } from "react";
import { useQuizTimer } from "@/hooks/use-quiz-timer"; // klasör adı düz
import type { Question } from "@/app/types/quiz";      
import { QuizInterface } from "@/components/quiz-interface";
// ortak tip

interface QuizRunnerProps {
  token: string;
  attemptId: number;
  initialQuestion: Question;
  totalQuestions: number;
  apiBase?: string;
}

export function QuizRunner({
  token,
  attemptId,
  initialQuestion,
  totalQuestions,
  apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000",
}: QuizRunnerProps) {
  const [question, setQuestion] = useState<Question>(initialQuestion);
  const [qIndex, setQIndex] = useState(1);

  const timer = useQuizTimer();
  const lastQidRef = useRef<string | null>(null);
  const sendingRef = useRef(false); // double-submit kilidi

  // quiz başlat
  useEffect(() => {
    timer.startQuiz();
    // ilk soru geldiğinde startQuestion otomatik tetiklensin
  }, []);

  // soru id değişince soru zamanını sıfırla
  useEffect(() => {
    if (question?.id && lastQidRef.current !== question.id) {
      timer.startQuestion(question.id);
      lastQidRef.current = question.id;
    }
  }, [question?.id]);

  async function submitAnswer(questionId: string, answer: string | string[]) {
    if (sendingRef.current) return;
    sendingRef.current = true;

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
          answer, // backend’e göre dönüştürmen gerekiyorsa burada yap
          client_duration_ms: Math.round(timer.currentQuestionTime),
        }),
      });
      const data = await res.json();

      if (data?.next_question) {
        setQuestion(data.next_question);
        setQIndex((n) => n + 1);
        // timer.startQuestion otomatik; yukarıdaki useEffect yeni id’yi görünce çalışacak
      } else if (data?.completed) {
        timer.endQuiz();
        // sonuç ekranı/redirect vb.
      }
    } finally {
      sendingRef.current = false;
    }
  }

  return (
    <QuizInterface
      question={question}
      questionNumber={qIndex}
      totalQuestions={totalQuestions}
      onSubmit={submitAnswer}
      questionTime={timer.currentQuestionTime} // ms
      formatTime={timer.formatTime}
    />
  );
}
