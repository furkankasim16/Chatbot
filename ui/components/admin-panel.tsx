"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Loader2, Sparkles, Check, X, ArrowLeft, Users } from "lucide-react"
import { generateRandomQuestion, generateQuestionWithParams, deleteQuestion, type Question } from "@/lib/api"
import { UserActivityTable } from "@/components/user-activity-table"

interface AdminPanelProps {
  token: string
  onBack: () => void
}

export function AdminPanel({ token, onBack }: AdminPanelProps) {
  const [currentView, setCurrentView] = useState<"generate" | "activity">("generate")
  const [isGenerating, setIsGenerating] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [generatedQuestion, setGeneratedQuestion] = useState<Question | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [questionType, setQuestionType] = useState<string>("mcq")
  const [topic, setTopic] = useState<string>("")
  const [difficulty, setDifficulty] = useState<string>("beginner")

  const handleGenerateRandom = async () => {
    setIsGenerating(true)
    setError(null)
    setGeneratedQuestion(null)

    try {
      const response = await generateRandomQuestion(token)
      const question = (response as any).question || response

      if (!question.stem || question.stem.trim() === "") {
        setError("Soru üretildi ancak içerik boş. Lütfen tekrar deneyin.")
      }

      setGeneratedQuestion(question)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Soru üretilemedi")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateWithParams = async () => {
    if (!topic.trim()) {
      setError("Lütfen bir konu girin")
      return
    }

    setIsGenerating(true)
    setError(null)
    setGeneratedQuestion(null)

    try {
      const response = await generateQuestionWithParams(token, topic, difficulty, questionType)
      const question = (response as any).question || response

      if (!question.stem || question.stem.trim() === "") {
        setError("Soru üretildi ancak içerik boş. Lütfen tekrar deneyin.")
      }

      setGeneratedQuestion(question)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Soru üretilemedi")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleApprove = () => {
    setGeneratedQuestion(null)
    setError(null)
  }

  const handleReject = async () => {
    if (!generatedQuestion?.id) {
      setError("Soru ID'si bulunamadı")
      return
    }

    setIsDeleting(true)
    setError(null)

    try {
      await deleteQuestion(token, generatedQuestion.id)
      setGeneratedQuestion(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Soru silinemedi")
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <h2 className="text-2xl font-bold">Admin Panel</h2>
        </div>

        <div className="flex gap-2">
          <Button
            variant={currentView === "generate" ? "default" : "outline"}
            onClick={() => setCurrentView("generate")}
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Soru Üret
          </Button>
          <Button
            variant={currentView === "activity" ? "default" : "outline"}
            onClick={() => setCurrentView("activity")}
          >
            <Users className="w-4 h-4 mr-2" />
            Kullanıcı Aktivitesi
          </Button>
        </div>
      </div>

      {currentView === "activity" ? (
        <UserActivityTable token={token} />
      ) : (
        <>
          {error && (
            <Card className="p-4 border-destructive/50 bg-destructive/10">
              <p className="text-sm text-destructive">{error}</p>
            </Card>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            <Card className="p-6 space-y-4">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Rastgele Soru Üret</h3>
                <p className="text-sm text-muted-foreground">Ollama ile rastgele bir soru üretin</p>
              </div>
              <Button onClick={handleGenerateRandom} disabled={isGenerating} className="w-full">
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Üretiliyor...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Rastgele Soru Üret
                  </>
                )}
              </Button>
            </Card>

            <Card className="p-6 space-y-4">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Parametreli Soru Üret</h3>
                <p className="text-sm text-muted-foreground">Belirli parametrelerle soru üretin</p>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="topic">Konu</Label>
                  <Input
                    id="topic"
                    placeholder="Örn: React Hooks"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="difficulty">Zorluk</Label>
                  <Select value={difficulty} onValueChange={setDifficulty}>
                    <SelectTrigger id="difficulty">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="beginner">Başlangıç</SelectItem>
                      <SelectItem value="intermediate">Orta</SelectItem>
                      <SelectItem value="advanced">İleri</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="type">Soru Tipi</Label>
                  <Select value={questionType} onValueChange={setQuestionType}>
                    <SelectTrigger id="type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mcq">Çoktan Seçmeli</SelectItem>
                      <SelectItem value="true_false">Doğru/Yanlış</SelectItem>
                      <SelectItem value="short_answer">Kısa Cevap</SelectItem>
                      <SelectItem value="open_ended">Açık Uçlu</SelectItem>
                      <SelectItem value="scenario">Senaryo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button onClick={handleGenerateWithParams} disabled={isGenerating} className="w-full">
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Üretiliyor...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Soru Üret
                    </>
                  )}
                </Button>
              </div>
            </Card>
          </div>

          {generatedQuestion && (
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold">Üretilen Soru</h3>

              <div className="space-y-4 p-4 bg-muted rounded-lg">
                {generatedQuestion.id && (
                  <div>
                    <p className="text-xs text-muted-foreground">ID: {generatedQuestion.id}</p>
                  </div>
                )}

                <div>
                  <p className="text-sm text-muted-foreground mb-1">Tip: {generatedQuestion.type}</p>
                  <p className="text-sm text-muted-foreground mb-1">Konu: {generatedQuestion.topic}</p>
                  <p className="text-sm text-muted-foreground">Zorluk: {generatedQuestion.level}</p>
                </div>

                {generatedQuestion.stem && (
                  <div>
                    <p className="font-medium mb-2">Soru:</p>
                    <p className="text-sm">{generatedQuestion.stem}</p>
                  </div>
                )}

                {generatedQuestion.choices && generatedQuestion.choices.length > 0 && (
                  <div>
                    <p className="font-medium mb-2">Seçenekler:</p>
                    <ul className="space-y-1">
                      {generatedQuestion.choices.map((choice, idx) => (
                        <li key={idx} className="text-sm">
                          {idx + 1}. {choice}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <p className="font-medium mb-2">Doğru Cevap:</p>
                  <p className="text-sm text-primary">
                    {generatedQuestion.answer_index !== undefined && generatedQuestion.choices
                      ? generatedQuestion.choices[generatedQuestion.answer_index]
                      : generatedQuestion.answer !== undefined
                        ? String(generatedQuestion.answer)
                        : generatedQuestion.expected || "Belirtilmemiş"}
                  </p>
                </div>

                {generatedQuestion.rationale && (
                  <div>
                    <p className="font-medium mb-2">Açıklama:</p>
                    <p className="text-sm">{generatedQuestion.rationale}</p>
                  </div>
                )}
              </div>

              <div className="flex gap-4">
                <Button onClick={handleApprove} className="flex-1" variant="default" disabled={isDeleting}>
                  <Check className="w-4 h-4 mr-2" />
                  Onayla
                </Button>
                <Button onClick={handleReject} className="flex-1" variant="destructive" disabled={isDeleting}>
                  {isDeleting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Siliniyor...
                    </>
                  ) : (
                    <>
                      <X className="w-4 h-4 mr-2" />
                      Reddet
                    </>
                  )}
                </Button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
