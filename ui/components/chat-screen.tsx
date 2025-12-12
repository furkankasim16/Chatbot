"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Loader2, Send } from "lucide-react"

import {
  getChatModes,
  sendChatTurn,
  type ChatMessage,
  type ChatModeConfig,
  type ChatTurnRequest,
} from "@/lib/api"

interface ChatScreenProps {
  token: string
  defaultTopic?: string
  defaultLevel?: string
  onBack?: () => void
}

export function ChatScreen({
  token,
  defaultTopic = "security_policy",
  defaultLevel = "beginner",
  onBack,
}: ChatScreenProps) {
  const [modes, setModes] = useState<Record<string, ChatModeConfig>>({})
  const [selectedMode, setSelectedMode] = useState("tutor")
  const [topic, setTopic] = useState(defaultTopic)
  const [level, setLevel] = useState(defaultLevel)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const endRef = useRef<HTMLDivElement>(null)
  const scrollToBottom = () => {
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
  }

  // Load chat modes
  useEffect(() => {
    let ok = true
    ;(async () => {
      try {
        const data = await getChatModes(token)
        if (!ok) return
        setModes(data)

        // selectedMode yoksa ilkini seç
        if (!data[selectedMode]) {
          const first = Object.keys(data)[0]
          if (first) setSelectedMode(first)
        }
      } catch (err) {
        console.error(err)
        setError("Chat modları yüklenemedi")
      }
    })()
    return () => {
      ok = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // defaultTopic/defaultLevel değişirse sync
  useEffect(() => {
    setTopic(defaultTopic)
  }, [defaultTopic])

  useEffect(() => {
    setLevel(defaultLevel)
  }, [defaultLevel])

  const handleSend = async () => {
    if (!input.trim()) return
    if (!modes[selectedMode]) return

    const userMsg: ChatMessage = {
      role: "user",
      content: input.trim(),
    }

    // UI'a hemen ekle
    const nextHistory = [...messages, userMsg]
    setMessages(nextHistory)
    setInput("")
    setIsLoading(true)
    scrollToBottom()

    try {
      const payload: ChatTurnRequest = {
        mode: selectedMode,
        topic,
        level,
        message: userMsg.content,
        history: messages, // backend history'yi system prompt ile birleştiriyor; istersek nextHistory de gönderebiliriz
      }

      const resp = await sendChatTurn(token, payload)

      const botMsg: ChatMessage = {
        role: "assistant",
        content: resp.reply,
      }

      setMessages((prev) => [...prev, botMsg])
      setSuggestions(resp.suggestions || [])
      setError(null)

      // ✅ Chat -> Quiz aksiyonu varsa yakala (backend response'da actions alanı varsa)
      const actions = (resp as any)?.actions
      if (Array.isArray(actions)) {
        const start = actions.find((a: any) => a?.type === "start_quiz")
        if (start?.payload) {
          localStorage.setItem("pending_quiz", JSON.stringify(start.payload))
          window.dispatchEvent(new Event("start-quiz-from-chat"))
        }
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || "Mesaj gönderilemedi")
    } finally {
      setIsLoading(false)
      scrollToBottom()
    }
  }

  return (
    <div className="flex gap-4">
      {/* Left Control Panel */}
      <aside className="w-64">
        <Card className="p-4 space-y-4">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              Geri
            </Button>
          )}

          <div>
            <p className="text-xs font-semibold mb-1">Chat Modu</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(modes).map(([key, m]) => (
                <button
                  key={key}
                 onClick={() => {
                      setSelectedMode(key)
                      setMessages([])        // ✅ mode değişince geçmişi temizle
                      setSuggestions([])
                      setError(null)
                    }}
                  className={`px-2 py-1 rounded border text-xs ${
                    selectedMode === key
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted hover:bg-muted/70"
                  }`}
                >
                  {m.title}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold mb-1">Topic</p>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          <div>
            <p className="text-xs font-semibold mb-1">Level</p>
            <Input
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          {modes[selectedMode] && (
            <p className="text-[11px] opacity-70">
              {modes[selectedMode].description}
            </p>
          )}
        </Card>
      </aside>

      {/* Right Chat Panel */}
      <div className="flex-1 flex flex-col">
        <Card className="flex-1 flex flex-col p-4">
          <div className="flex-1 overflow-y-auto space-y-2">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`max-w-[80%] px-3 py-2 rounded ${
                  msg.role === "user"
                    ? "ml-auto bg-primary text-primary-foreground"
                    : "mr-auto bg-muted"
                }`}
              >
                {msg.content}
              </div>
            ))}

            {isLoading && (
              <div className="mr-auto bg-muted px-3 py-2 rounded flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">Yanıt oluşturuluyor...</span>
              </div>
            )}

            <div ref={endRef} />
          </div>

          {error && <p className="text-xs text-destructive mt-2">{error}</p>}

          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(s)}
                  className="border rounded px-2 py-1 text-[11px] bg-muted hover:bg-muted/70"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <div className="mt-3 flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 min-h-[40px]"
              placeholder="Mesaj yaz..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />

            <Button onClick={handleSend} disabled={!input.trim() || isLoading}>
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send />
              )}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}
