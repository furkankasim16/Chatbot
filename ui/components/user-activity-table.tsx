"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChevronDown, ChevronRight, Search, Filter } from "lucide-react"
import { getUserActivity, type QuizAttempt } from "@/lib/api"

interface UserActivityTableProps {
  token: string
}

export function UserActivityTable({ token }: UserActivityTableProps) {
  const [attempts, setAttempts] = useState<QuizAttempt[]>([])
  const [filteredAttempts, setFilteredAttempts] = useState<QuizAttempt[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  // Filters
  const [searchQuery, setSearchQuery] = useState("")
  const [topicFilter, setTopicFilter] = useState<string>("all")
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all")

  useEffect(() => {
    loadActivity()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [attempts, searchQuery, topicFilter, difficultyFilter])

  const loadActivity = async () => {
    console.log("[v0] Loading user activity...")
    setIsLoading(true)
    setError(null)
    try {
      const data = await getUserActivity(token)
      console.log("[v0] User activity data received:", data)
      console.log("[v0] Number of attempts:", data.length)
      setAttempts(data)
    } catch (error) {
      console.error("[v0] Failed to load user activity:", error)
      setError(error instanceof Error ? error.message : "Veri yüklenirken hata oluştu")
    } finally {
      setIsLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...attempts]

    // Search by username
    if (searchQuery) {
      filtered = filtered.filter((attempt) => attempt.username.toLowerCase().includes(searchQuery.toLowerCase()))
    }

    // Filter by topic
    if (topicFilter !== "all") {
      filtered = filtered.filter((attempt) => attempt.topic === topicFilter)
    }

    // Filter by difficulty
    if (difficultyFilter !== "all") {
      filtered = filtered.filter((attempt) => attempt.difficulty === difficultyFilter)
    }

    setFilteredAttempts(filtered)
  }

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedRows(newExpanded)
  }

  const getUniqueTopics = () => {
    return Array.from(new Set(attempts.map((a) => a.topic)))
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("tr-TR", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const getScoreColor = (percentage: number) => {
    if (percentage >= 80) return "text-green-600 dark:text-green-400"
    if (percentage >= 60) return "text-yellow-600 dark:text-yellow-400"
    return "text-red-600 dark:text-red-400"
  }

  if (isLoading) {
    return (
      <Card className="p-6">
        <p className="text-center text-muted-foreground">Yükleniyor...</p>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center space-y-2">
          <p className="text-red-600 dark:text-red-400">Hata: {error}</p>
          <Button onClick={loadActivity} variant="outline" size="sm">
            Tekrar Dene
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Kullanıcı ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={topicFilter} onValueChange={setTopicFilter}>
            <SelectTrigger className="w-full md:w-[180px]">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Konu" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tüm Konular</SelectItem>
              {getUniqueTopics().map((topic) => (
                <SelectItem key={topic} value={topic}>
                  {topic}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={difficultyFilter} onValueChange={setDifficultyFilter}>
            <SelectTrigger className="w-full md:w-[180px]">
              <SelectValue placeholder="Zorluk" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tüm Zorluklar</SelectItem>
              <SelectItem value="beginner">Başlangıç</SelectItem>
              <SelectItem value="intermediate">Orta</SelectItem>
              <SelectItem value="advanced">İleri</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]"></TableHead>
              <TableHead>Kullanıcı</TableHead>
              <TableHead>Tarih</TableHead>
              <TableHead>Konu</TableHead>
              <TableHead>Zorluk</TableHead>
              <TableHead>Skor</TableHead>
              <TableHead className="text-right">Yüzde</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAttempts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  {attempts.length === 0 ? (
                    <div className="space-y-2">
                      <p>Henüz quiz çözülmemiş</p>
                      <p className="text-xs">Kullanıcılar quiz çözdükçe burada görünecek</p>
                    </div>
                  ) : (
                    "Filtrelere uygun sonuç bulunamadı"
                  )}
                </TableCell>
              </TableRow>
            ) : (
              filteredAttempts.map((attempt) => (
                <>
                  <TableRow key={attempt.id} className="cursor-pointer" onClick={() => toggleRow(attempt.id)}>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="w-8 h-8">
                        {expandedRows.has(attempt.id) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-medium">{attempt.username}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(attempt.quiz_date)}</TableCell>
                    <TableCell>{attempt.topic}</TableCell>
                    <TableCell className="capitalize">{attempt.difficulty}</TableCell>
                    <TableCell>
                      {attempt.correct_answers}/{attempt.total_questions}
                    </TableCell>
                    <TableCell className={`text-right font-semibold ${getScoreColor(attempt.score)}`}>
                      {attempt.score.toFixed(0)}%
                    </TableCell>
                  </TableRow>

                  {expandedRows.has(attempt.id) && (
                    <TableRow>
                      <TableCell colSpan={7} className="bg-muted/50">
                        <div className="p-4 space-y-3">
                          <h4 className="font-semibold text-sm">Soru Detayları</h4>
                          <div className="space-y-2">
                            {attempt.questions_attempted.map((q, idx) => (
                              <div
                                key={idx}
                                className={`p-3 rounded-lg border ${
                                  q.is_correct
                                    ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900"
                                    : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900"
                                }`}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1">
                                    <p className="text-sm font-medium mb-1">Soru {idx + 1}</p>
                                    <p className="text-xs text-muted-foreground">
                                      Kullanıcı Cevabı: <span className="font-medium">{q.user_answer || "Boş"}</span>
                                    </p>
                                  </div>
                                  <div
                                    className={`text-xs font-semibold px-2 py-1 rounded ${
                                      q.is_correct
                                        ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300"
                                        : "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300"
                                    }`}
                                  >
                                    {q.is_correct ? "Doğru" : "Yanlış"}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      <div className="text-sm text-muted-foreground text-center">
        Toplam {filteredAttempts.length} sonuç gösteriliyor
      </div>
    </div>
  )
}
