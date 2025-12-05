"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Loader2,
  Sparkles,
  Check,
  X,
  ArrowLeft,
  Users,
  Brain,
  ListChecks,
} from "lucide-react"
import {
  generateRandomQuestion,
  generateQuestionWithParams,
  deleteQuestion,
  type Question,
  generateQuestionFromPdf,
} from "@/lib/api"
import { UserActivityTable } from "@/components/user-activity-table"
import { AuditLogsTable } from "@/components/audit-logs-table"
import { AdminLlmStats } from "@/components/admin-llm-stats"
import { LlmPerformanceChart } from "@/components/admin-llm-stats-chart"
import { AdminQuestionBank } from "@/components/admin-question-bank"

interface AdminPanelProps {
  token: string
  onBack: () => void
}

export function AdminPanel({ token, onBack }: AdminPanelProps) {
  const [currentView, setCurrentView] = useState<
    "generate" | "activity" | "audit" | "llmStats" | "questionBank"
  >("generate")

  const [isGenerating, setIsGenerating] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [generatedQuestion, setGeneratedQuestion] = useState<Question | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)

  const [questionType, setQuestionType] = useState<string>("mcq")
  const [topic, setTopic] = useState<string>("")
  const [difficulty, setDifficulty] = useState<string>("beginner")

  // ⭐ LLM MODEL SEÇİMİ
  const [llmModel, setLlmModel] = useState<string>("ollama:llama3")

  // ⭐ PDF'ten soru üretme durumları
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [isPdfGenerating, setIsPdfGenerating] = useState(false)

  const handleGenerateRandom = async () => {
    setIsGenerating(true)
    setError(null)
    setGeneratedQuestion(null)

    try {
      const response = await generateRandomQuestion(token, llmModel)
      const question = (response as any).question || response

      if (!question.stem?.trim()) setError("Soru üretildi ama içerik boş.")
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
      const response = await generateQuestionWithParams(
        token,
        topic,
        difficulty,
        questionType,
        llmModel,
      )
      const question = (response as any).question || response

      if (!question.stem?.trim())
        setError("Soru üretildi ancak içerik boş.")
      setGeneratedQuestion(question)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Soru üretilemedi")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateFromPdf = async () => {
    if (!pdfFile) {
      setError("Lütfen bir PDF dosyası seçin")
      return
    }
    if (!topic.trim()) {
      setError("PDF için bir konu girin (örn: product_basics)")
      return
    }

    setIsPdfGenerating(true)
    setError(null)
    setGeneratedQuestion(null)

    try {
      const question = await generateQuestionFromPdf(token, pdfFile, {
        topic,
        level: difficulty,
        qtype: questionType,
        model: llmModel,
      })

      if (!question.stem?.trim()) {
        setError("Soru üretildi ancak içerik boş görünüyor.")
      }

      setGeneratedQuestion(question)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "PDF'ten soru üretilemedi",
      )
    } finally {
      setIsPdfGenerating(false)
    }
  }

  const handleApprove = () => {
    setGeneratedQuestion(null)
    setError(null)
  }

  const handleReject = async () => {
    if (!generatedQuestion?.id) {
      setError("Soru ID bulunamadı")
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
      {/* ÜST BAR */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <h2 className="text-2xl font-bold">Admin Panel</h2>
        </div>

        <div className="flex gap-2 flex-wrap justify-end">
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

          <Button
            variant={currentView === "audit" ? "default" : "outline"}
            onClick={() => setCurrentView("audit")}
          >
            Loglar
          </Button>

          <Button
            variant={currentView === "llmStats" ? "default" : "outline"}
            onClick={() => setCurrentView("llmStats")}
          >
            <Brain className="w-4 h-4 mr-2" />
            LLM Performans
          </Button>
          
          <Button
          variant={currentView === "questionBank" ? "default" : "outline"}
          onClick={() => setCurrentView("questionBank")}
        >
          <ListChecks className="w-4 h-4 mr-2" />
          Soru Bankası
        </Button>
        </div>
      </div>

      {/* CONTENT */}
      {currentView === "activity" ? (
        <UserActivityTable token={token} />
      ) : currentView === "audit" ? (
        <AuditLogsTable token={token} />
      ) : currentView === "llmStats" ? (
        <div className="space-y-6">
          <AdminLlmStats />
          <LlmPerformanceChart />
        </div>
      ) : currentView === "questionBank" ? (
          <AdminQuestionBank token={token} />
        ) : (
        <>
          {error && (
            <Card className="p-4 border-destructive/50 bg-destructive/10">
              <p className="text-sm text-destructive">{error}</p>
            </Card>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            {/* ⭐ MODEL SEÇİMİ */}
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Brain className="w-5 h-5" />
                LLM Model Seçimi
              </h3>

              <p className="text-sm text-muted-foreground">
                Soru üretirken hangi modeli kullanmak istediğinizi seçin
              </p>

              <Select value={llmModel} onValueChange={setLlmModel}>
                <SelectTrigger>
                  <SelectValue placeholder="Model seçin" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ollama:llama3">Ollama (Local)</SelectItem>
                  <SelectItem value="llama-3.1-8b-instant">
                    Groq - LLaMA3 70B
                  </SelectItem>
                  <SelectItem value="openai_gpt4o">
                    OpenAI GPT-4o
                  </SelectItem>
                  <SelectItem value="gemini-2.0-flash">
                    Google - Gemini 2.0 Flash
                  </SelectItem>
                </SelectContent>
              </Select>
            </Card>

            {/* Rastgele soru üretme */}
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold">Rastgele Soru Üret</h3>

              <Button
                onClick={handleGenerateRandom}
                disabled={isGenerating}
                className="w-full"
              >
                {isGenerating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                Rastgele Soru Üret
              </Button>
            </Card>

            {/* Parametreli üretim */}
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold">Parametreli Soru Üret</h3>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Konu</Label>
                  <Input
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Zorluk</Label>
                  <Select value={difficulty} onValueChange={setDifficulty}>
                    <SelectTrigger>
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
                  <Label>Soru Tipi</Label>
                  <Select
                    value={questionType}
                    onValueChange={setQuestionType}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mcq">Çoktan Seçmeli</SelectItem>
                      <SelectItem value="true_false">
                        Doğru / Yanlış
                      </SelectItem>
                      <SelectItem value="short_answer">
                        Kısa Cevap
                      </SelectItem>
                      <SelectItem value="open_ended">
                        Açık Uçlu
                      </SelectItem>
                      <SelectItem value="scenario">Senaryo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  onClick={handleGenerateWithParams}
                  disabled={isGenerating}
                  className="w-full"
                >
                  {isGenerating ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  Soru Üret
                </Button>
              </div>
            </Card>

            {/* 📄 PDF'ten soru üretim */}
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold">PDF'ten Soru Üret</h3>

              <p className="text-sm text-muted-foreground">
                Yüklediğiniz PDF içeriğine göre, seçtiğiniz konu / zorlukta otomatik soru üretir.
              </p>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>PDF Dosyası</Label>
                  <Input
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => {
                      const file = e.target.files?.[0] ?? null
                      setPdfFile(file)
                    }}
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Örn: ders notları, ürün kataloğu, teknik doküman…
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>PDF Konu Etiketi</Label>
                  <Input
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Örn: product_basics"
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Zorluk</Label>
                    <Select value={difficulty} onValueChange={setDifficulty}>
                      <SelectTrigger>
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
                    <Label>Soru Tipi</Label>
                    <Select
                      value={questionType}
                      onValueChange={setQuestionType}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="mcq">Çoktan Seçmeli</SelectItem>
                        <SelectItem value="true_false">
                          Doğru / Yanlış
                        </SelectItem>
                        <SelectItem value="short_answer">
                          Kısa Cevap
                        </SelectItem>
                        <SelectItem value="open_ended">
                          Açık Uçlu
                        </SelectItem>
                        <SelectItem value="scenario">Senaryo</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button
                  onClick={handleGenerateFromPdf}
                  disabled={isPdfGenerating || !pdfFile}
                  className="w-full"
                >
                  {isPdfGenerating ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  PDF'ten Soru Üret
                </Button>
              </div>
            </Card>
          </div>

          {/* Output */}
          {generatedQuestion && (
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold">Üretilen Soru</h3>

              <div className="p-4 bg-muted rounded-lg space-y-4">
                <p className="text-xs text-muted-foreground">
                  Model:{" "}
                  {(generatedQuestion as any)?.source_model || llmModel}
                </p>

                <p>
                  <b>Soru:</b> {generatedQuestion.stem}
                </p>

                {(generatedQuestion as any).choices && (
                  <ul className="list-disc list-inside">
                    {(generatedQuestion as any).choices.map(
                      (c: string, i: number) => (
                        <li key={i}>{c}</li>
                      ),
                    )}
                  </ul>
                )}

                <p>
                  <b>Doğru Cevap:</b>{" "}
                  {(generatedQuestion as any).answer_index !== undefined
                    ? (generatedQuestion as any).choices?.[
                        (generatedQuestion as any).answer_index
                      ]
                    : "Belirtilmemiş"}
                </p>

                {(generatedQuestion as any).rationale && (
                  <p>
                    <b>Açıklama:</b>{" "}
                    {(generatedQuestion as any).rationale}
                  </p>
                )}
              </div>

              <div className="flex gap-4">
                <Button onClick={handleApprove} className="flex-1">
                  <Check className="w-4 h-4 mr-2" />
                  Onayla
                </Button>
                <Button
                  onClick={handleReject}
                  className="flex-1"
                  variant="destructive"
                >
                  {isDeleting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <X className="w-4 h-4 mr-2" />
                  )}
                  Reddet
                </Button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
