"use client"

import { useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Loader2, Send, Bot, User } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import type { ChatMessage } from "@/lib/api"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export function DefaultChatWorkspace({
  messages,
  isLoading,
  error,
  suggestions,
  input,
  setInput,
  onSend,
}: {
  messages: ChatMessage[]
  isLoading: boolean
  error: string | null
  suggestions: string[]
  input: string
  setInput: (v: string) => void
  onSend: () => void
}) {
  const endRef = useRef<HTMLDivElement>(null)

  // Auto-scroll on new messages
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoading])

  const send = () => {
    onSend()
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <Card className="flex-1 flex flex-col p-4 bg-muted/10 h-full overflow-hidden border-none shadow-none">

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 scrollbar-thin scrollbar-thumb-muted-foreground/20">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-50 p-4">
              <Bot className="w-12 h-12 mb-2" />
              <p className="text-sm">Nasıl yardımcı olabilirim?</p>
            </div>
          )}

          {messages.map((msg, i) => {
            const isUser = msg.role === "user"
            return (
              <div key={i} className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                {/* Avatar */}
                <Avatar className="w-8 h-8 border">
                  <AvatarFallback className={isUser ? "bg-primary text-primary-foreground" : "bg-muted"}>
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </AvatarFallback>
                </Avatar>

                {/* Bubble */}
                <div
                  className={`relative max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm ${isUser
                      ? "bg-primary text-primary-foreground rounded-tr-sm"
                      : "bg-background border rounded-tl-sm"
                    }`}
                >
                  <div className="prose prose-sm dark:prose-invert break-words max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: ({ node, ...props }) => <a target="_blank" rel="noopener noreferrer" className="underline font-medium hover:text-blue-500" {...props} />,
                        code: ({ node, inline, className, children, ...props }: any) => {
                          return inline ? (
                            <code className="bg-muted-foreground/20 px-1 py-0.5 rounded font-mono" {...props}>
                              {children}
                            </code>
                          ) : (
                            <code className="block bg-muted-foreground/10 p-2 rounded font-mono overflow-x-auto my-1" {...props}>
                              {children}
                            </code>
                          )
                        }
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )
          })}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex gap-3">
              <Avatar className="w-8 h-8 border">
                <AvatarFallback className="bg-muted">
                  <Bot className="w-4 h-4" />
                </AvatarFallback>
              </Avatar>
              <div className="bg-background border px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 bg-foreground/40 rounded-full animate-bounce"></span>
              </div>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* Action Area */}
        <div className="mt-4 space-y-3">
          {error && (
            <div className="text-xs text-destructive bg-destructive/10 p-2 rounded flex items-center gap-2">
              <span>⚠️</span> {error}
            </div>
          )}

          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2 animate-in fade-in slide-in-from-bottom-2">
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(s)}
                  className="border rounded-full px-3 py-1.5 text-xs bg-background hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <div className="flex gap-2 relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 min-h-[50px] max-h-[150px] resize-none pr-12 rounded-xl border-muted-foreground/20 focus-visible:ring-offset-0 focus-visible:ring-1"
              placeholder="Bir şeyler sor..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
            />

            <Button
              onClick={send}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="absolute right-2 bottom-2 h-8 w-8 rounded-full"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
