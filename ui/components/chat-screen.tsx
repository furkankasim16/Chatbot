"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

import {
  getChatModes,
  sendChatTurn,
  getChatJobResult,
  type ChatMessage,
  type ChatModeConfig,
  type ChatTurnRequest,
  type ChatTurnResponse,
  type ChatJobResponse,
} from "@/lib/api"

import { handleChatActions } from "@/lib/chatActions"

import { DefaultChatWorkspace } from "@/components/DefaultChatWorkspace"
import { ReviewWorkspace } from "@/components/ReviewWorkspace"

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
  const [useRag, setUseRag] = useState(false) // 🆕 RAG State

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  // Load chat modes
  useEffect(() => {
    let ok = true
      ; (async () => {
        try {
          const data = await getChatModes(token)
          if (!ok) return
          setModes(data)

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

    const userMsg: ChatMessage = { role: "user", content: input.trim() }

    // UI'a hemen ekle
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setIsLoading(true)

    try {
      const payload: ChatTurnRequest = {
        mode: selectedMode,
        topic,
        level,
        message: userMsg.content,
        history: messages,
        use_rag: useRag, // 🆕 Pass RAG flag
      }

      let resp = await sendChatTurn(token, payload)

      // 🔄 POLLING LOGIC
      if ("job_id" in resp && resp.status === "queued") {
        const jobId = (resp as ChatJobResponse).job_id

        // Polling loop
        while (true) {
          await new Promise(r => setTimeout(r, 750)) // 750ms wait
          const jobStatus = await getChatJobResult(token, jobId)

          if (jobStatus.status === "completed" && jobStatus.result) {
            resp = jobStatus.result
            break
          } else if (jobStatus.status === "failed" || jobStatus.status === "expired") {
            throw new Error(jobStatus.error || "Job failed or expired")
          }
          // else: still queued/started, continue waiting
        }
      }

      // Şimdi elimizde kesinlikle ChatTurnResponse var (veya hata fırlatıldı)
      const finalResp = resp as ChatTurnResponse

      const botMsg: ChatMessage = { role: "assistant", content: finalResp.reply }

      setMessages((prev) => [...prev, botMsg])
      setSuggestions(finalResp.suggestions || [])
      setError(null)

      // ✅ ortak action handler (start_quiz vb.)
      handleChatActions(finalResp)
    } catch (err: any) {
      console.error(err)
      setError(err.message || "Mesaj gönderilemedi")
    } finally {
      setIsLoading(false)
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

                    // ✅ Review modunda history korunur
                    if (key !== "review") {
                      setMessages([])
                    }

                    setSuggestions([])
                    setError(null)
                  }}
                  className={`px-2 py-1 rounded border text-xs ${selectedMode === key
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
            <p className="text-xs font-semibold mb-1">Konu</p>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          <div>
            <p className="text-xs font-semibold mb-1">Seviye</p>
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

          <div className="pt-2 border-t border-border">
            <div className="flex items-center space-x-2">
              <Switch id="rag-mode" checked={useRag} onCheckedChange={setUseRag} />
              <Label htmlFor="rag-mode" className="text-xs font-semibold">Bilgi Bankası (RAG)</Label>
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">
              Aktif edilirse, cevaplar yüklediğiniz dokümanlardan üretilir.
            </p>
          </div>
        </Card>
      </aside>

      {/* Right Panel */}
      {selectedMode === "review" ? (
        <ReviewWorkspace
          token={token}
          topic={topic}
          level={level}
          history={messages}
          setHistory={setMessages}
        />
      ) : (
        <DefaultChatWorkspace
          messages={messages}
          isLoading={isLoading}
          error={error}
          suggestions={suggestions}
          input={input}
          setInput={setInput}
          onSend={handleSend}
        />
      )}
    </div>
  )
}
