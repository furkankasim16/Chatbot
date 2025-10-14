"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { ArrowLeft, Send, Loader2, Bot, User } from "lucide-react"
import { sendChatMessage } from "@/lib/api"

interface ChatScreenProps {
  onBack: () => void
  token: string
  context?: string
}

interface Message {
  role: "user" | "bot"
  content: string
  timestamp: Date
}

export function ChatScreen({ onBack, token, context }: ChatScreenProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "bot",
      content: context
        ? `Merhaba! ${context} konusunda size nasıl yardımcı olabilirim?`
        : "Merhaba! Size nasıl yardımcı olabilirim?",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const response = await sendChatMessage(token, input.trim(), context)

      const botMessage: Message = {
        role: "bot",
        content: response.response,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, botMessage])
    } catch (error) {
      console.error("[v0] Chat error:", error)

      let errorContent = "⚠️ Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."

      if (error instanceof Error) {
        if (error.message.includes("zaman aşımına")) {
          errorContent =
            "⏱️ İstek zaman aşımına uğradı. AI yanıt üretirken çok uzun sürdü. Lütfen daha kısa bir mesaj deneyin veya backend'in çalıştığından emin olun."
        } else if (error.message.includes("gönderilemedi")) {
          errorContent = "🔌 Backend'e bağlanılamadı. Lütfen backend sunucusunun çalıştığından emin olun."
        }
      }

      const errorMessage: Message = {
        role: "bot",
        content: errorContent,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="animate-fade-in space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Chat Modu</h2>
          <p className="text-sm text-muted-foreground">
            Yapay zeka ile sohbet edin (Yanıt süresi 30-60 saniye sürebilir)
          </p>
        </div>
      </div>

      <Card className="p-4 h-[500px] flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              {message.role === "bot" && (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-foreground" />
                </div>
              )}

              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                <p className="text-xs opacity-70 mt-1">
                  {message.timestamp.toLocaleTimeString("tr-TR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>

              {message.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-accent-foreground" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-primary-foreground" />
              </div>
              <div className="bg-muted rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Yanıt üretiliyor...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Mesajınızı yazın..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button onClick={handleSend} disabled={!input.trim() || isLoading} size="icon">
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </Card>
    </div>
  )
}
