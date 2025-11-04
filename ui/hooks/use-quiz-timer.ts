"use client"

import { useState, useEffect, useRef, useCallback } from "react"

export interface UseQuizTimerReturn {
  totalQuizTime: number
  currentQuestionTime: number
  isQuizActive: boolean
  isPaused: boolean
  pauseReason: "hidden" | "idle" | null
  quizStartTime: number | null
  questionStartTime: number | null
  isQuestionActive: boolean
  startQuiz: () => void
  endQuiz: () => void
  startQuestion: (questionId: string) => void
  endQuestion: () => void
  pause: (reason: "hidden" | "idle") => void
  resume: () => void
  formatTime: (ms: number) => string
  reset: () => void
}

export function useQuizTimer(): UseQuizTimerReturn {
  const [isQuizActive, setIsQuizActive] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [pauseReason, setPauseReason] = useState<"hidden" | "idle" | null>(null)
  const [totalQuizTime, setTotalQuizTime] = useState(0)
  const [currentQuestionTime, setCurrentQuestionTime] = useState(0)

  // Başlangıç timestamp’larını tutuyoruz (ms)
  const quizStartTimeRef = useRef<number | null>(null)
  const questionStartTimeRef = useRef<number | null>(null)

  // rAF kontrolü
  const rafIdRef = useRef<number | null>(null)

  // Idle takibi
  const lastActiveTimeRef = useRef<number>(Date.now())
  const pauseStartTimeRef = useRef<number | null>(null)

  // === TIMER CORE (requestAnimationFrame) ===
  const tick = useCallback((nowHrTime: number) => {
    // nowHrTime: performance.now() (yüksek çözünürlüklü)
    // absolute now gerekli olduğunda Date.now() kullanıyoruz
    if (isQuizActive && !isPaused) {
      const now = Date.now()

      if (quizStartTimeRef.current != null) {
        setTotalQuizTime(now - quizStartTimeRef.current)
      }
      if (questionStartTimeRef.current != null) {
        setCurrentQuestionTime(now - questionStartTimeRef.current)
      }

      lastActiveTimeRef.current = now
      rafIdRef.current = window.requestAnimationFrame(tick)
    } else {
      // Durduğunda rAF’ı temizle
      if (rafIdRef.current != null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
    }
  }, [isQuizActive, isPaused])

  useEffect(() => {
    // Aktif ve pause değilken rAF başlat
    if (isQuizActive && !isPaused && rafIdRef.current == null) {
      rafIdRef.current = window.requestAnimationFrame(tick)
    }
    // Cleanup
    return () => {
      if (rafIdRef.current != null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
    }
  }, [isQuizActive, isPaused, tick])

  // === GÖRÜNÜRLÜK (TAB) OLAYI ===
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && isQuizActive && !isPaused) {
        pause("hidden")
      } else if (!document.hidden && isPaused && pauseReason === "hidden") {
        resume()
      }
    }
    document.addEventListener("visibilitychange", handleVisibilityChange)
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange)
  }, [isQuizActive, isPaused, pauseReason]) // pause/resume referansları aşağıda

  // === IDLE TESPİTİ ===
  useEffect(() => {
    if (!isQuizActive) return

    const handleActivity = () => {
      lastActiveTimeRef.current = Date.now()
      if (isPaused && pauseReason === "idle") {
        resume()
      }
    }

    const checkIdle = window.setInterval(() => {
      const diff = Date.now() - lastActiveTimeRef.current
      if (diff > 60_000 && !isPaused) {
        pause("idle")
      }
    }, 5_000)

    const events = ["mousedown", "mousemove", "keypress", "scroll", "touchstart", "click"]
    events.forEach((e) => document.addEventListener(e, handleActivity))

    return () => {
      window.clearInterval(checkIdle)
      events.forEach((e) => document.removeEventListener(e, handleActivity))
    }
  }, [isQuizActive, isPaused, pauseReason]) // pause/resume referansları aşağıda

  // === KAMU API ===
  const startQuiz = useCallback(() => {
    const now = Date.now()
    quizStartTimeRef.current = now
    setIsQuizActive(true)
    setIsPaused(false)
    setPauseReason(null)
    setTotalQuizTime(0)
    lastActiveTimeRef.current = now
  }, [])

  const endQuiz = useCallback(() => {
    setIsQuizActive(false)
    // Quiz bitince soru da otomatik biter
    questionStartTimeRef.current = null
    if (rafIdRef.current != null) {
      cancelAnimationFrame(rafIdRef.current)
      rafIdRef.current = null
    }
  }, [])

  const startQuestion = useCallback((questionId: string) => {
    // Quiz aktif değilken soru başlatma
    if (!isQuizActive) return
    const now = Date.now()
    questionStartTimeRef.current = now
    setCurrentQuestionTime(0)
    lastActiveTimeRef.current = now
  }, [isQuizActive])

  const endQuestion = useCallback(() => {
    questionStartTimeRef.current = null
  }, [])

  const pause = useCallback((reason: "hidden" | "idle") => {
    if (!isQuizActive || isPaused) return
    pauseStartTimeRef.current = Date.now()
    setIsPaused(true)
    setPauseReason(reason)
  }, [isQuizActive, isPaused])

  const resume = useCallback(() => {
    if (!isQuizActive || !isPaused) return
    const pausedAt = pauseStartTimeRef.current
    if (pausedAt) {
      const pauseDuration = Date.now() - pausedAt
      // Başlangıçları öteleyerek sürelerde boşluk yaratmıyoruz
      if (quizStartTimeRef.current != null) {
        quizStartTimeRef.current += pauseDuration
      }
      if (questionStartTimeRef.current != null) {
        questionStartTimeRef.current += pauseDuration
      }
      pauseStartTimeRef.current = null
    }
    setIsPaused(false)
    setPauseReason(null)
    lastActiveTimeRef.current = Date.now()
  }, [isQuizActive, isPaused])

  const formatTime = useCallback((ms: number): string => {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000))
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
  }, [])

  const reset = useCallback(() => {
    setIsQuizActive(false)
    setIsPaused(false)
    setPauseReason(null)
    setTotalQuizTime(0)
    setCurrentQuestionTime(0)

    quizStartTimeRef.current = null
    questionStartTimeRef.current = null
    pauseStartTimeRef.current = null
    lastActiveTimeRef.current = Date.now()

    if (rafIdRef.current != null) {
      cancelAnimationFrame(rafIdRef.current)
      rafIdRef.current = null
    }
  }, [])

  return {
    totalQuizTime,
    currentQuestionTime,
    isQuizActive,
    isPaused,
    pauseReason,
    quizStartTime: quizStartTimeRef.current,
    questionStartTime: questionStartTimeRef.current,
    isQuestionActive: questionStartTimeRef.current !== null,
    startQuiz,
    endQuiz,
    startQuestion,
    endQuestion,
    pause,
    resume,
    formatTime,
    reset,
  }
}
