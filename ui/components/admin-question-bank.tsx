"use client"

import { useEffect, useMemo, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Trash2,
  Search,
  ChevronDown,
  X,
  Filter,
  Pencil,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip"
import type { Question } from "@/lib/api"
import { getAllQuestions, deleteQuestion, updateQuestion } from "@/lib/api"
import { cn } from "@/lib/utils"
import { ScenarioStep } from "@/app/types/quiz"
import { nanoid } from "nanoid"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

type ActiveFilterKey = "topic" | "type" | "difficulty" | "stem" | null

interface QuestionBankProps {
  token: string
}

type UiScenarioStep = ScenarioStep & {
  _clientId: string
  _action?: "create" | "update" | "delete"
}

interface QuestionEditForm {
  topic: string
  question_type: string
  difficulty: string
  stem: string

  // MCQ
  options: string[]
  correct_index: number | null

  // TRUE/FALSE
  correct_answer_bool: boolean | null

  // SHORT ANSWER
  accepted_answers: string[]
  matching_type: string

  // OPEN ENDED
  rubric: string

  // SCENARIO
  scenario: string
  steps: UiScenarioStep[]
}

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: "Başlangıç",
  intermediate: "Orta",
  advanced: "İleri",
  easy: "Kolay",
  medium: "Orta",
  hard: "Zor",
}

const QUESTION_TYPE_LABEL: Record<string, string> = {
  mcq: "Çoktan Seçmeli",
  true_false: "Doğru / Yanlış",
  short_answer: "Kısa Yanıt",
  open_ended: "Açık Uçlu",
  scenario: "Senaryo",
}

export function AdminQuestionBank({ token }: QuestionBankProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [searchTerm, setSearchTerm] = useState("")
  const [activeFilterKey, setActiveFilterKey] = useState<ActiveFilterKey>(null)
  const [columnFilters, setColumnFilters] = useState({
    topic: "",
    type: "",
    difficulty: "",
    stem: "",
  })

  // Sol panel gelişmiş filtreler
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [selectedDifficulties, setSelectedDifficulties] = useState<string[]>([])

  // Kaynak bazlı filtreler
  const [showOnlyNoSource, setShowOnlyNoSource] = useState(false)
  const [showOnlyLLM, setShowOnlyLLM] = useState(false)

  // Satır seçimi (modal için)
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Çoklu seçim (checkbox)
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  // Edit state
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<QuestionEditForm | null>(null)

  // İlk yükleme
  useEffect(() => {
    let mounted = true
      ; (async () => {
        try {
          setIsLoading(true)
          const data = await getAllQuestions()
          if (!mounted) return
          setQuestions(data)
          setError(null)
        } catch (err: any) {
          console.error(err)
          if (!mounted) return
          setError("Sorular yüklenirken bir hata oluştu.")
        } finally {
          if (mounted) setIsLoading(false)
        }
      })()
    return () => {
      mounted = false
    }
  }, [token])

  const { topicOptions, typeOptions, difficultyOptions } = useMemo(() => {
    const topics = new Set<string>()
    const types = new Set<string>()
    const diffs = new Set<string>()

    for (const q of questions as any[]) {
      if (q.topic) topics.add(q.topic)

      const qt = q.question_type
      if (qt) types.add(qt)

      const lvl = q.difficulty ?? q.level
      if (lvl) diffs.add(lvl)
    }

    return {
      topicOptions: Array.from(topics).sort(),
      typeOptions: Array.from(types).sort(),
      difficultyOptions: Array.from(diffs).sort(),
    }
  }, [questions])

  const toggleFromArray = <T,>(arr: T[], value: T): T[] =>
    arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value]

  const handleMultiFilterToggle = (
    key: "topic" | "type" | "difficulty",
    value: string,
  ) => {
    if (key === "topic") {
      setSelectedTopics((prev) => toggleFromArray(prev, value))
    } else if (key === "type") {
      setSelectedTypes((prev) => toggleFromArray(prev, value))
    } else if (key === "difficulty") {
      setSelectedDifficulties((prev) => toggleFromArray(prev, value))
    }
  }

  const clearAllFilters = () => {
    setSearchTerm("")
    setColumnFilters({ topic: "", type: "", difficulty: "", stem: "" })
    setSelectedTopics([])
    setSelectedTypes([])
    setSelectedDifficulties([])
    setShowOnlyNoSource(false)
    setShowOnlyLLM(false)
    setActiveFilterKey(null)
  }

  const filteredQuestions = useMemo(() => {
    return (questions as any[]).filter((q) => {
      const topic: string = q.topic ?? ""
      const qt: string = q.question_type ?? ""
      const lvl: string = q.difficulty ?? q.level ?? ""
      const stem: string = q.stem ?? ""
      const source: string | undefined = q.source_model ?? undefined

      const search = searchTerm.trim().toLowerCase()
      if (search) {
        const haystack = `${stem} ${topic}`.toLowerCase()
        if (!haystack.includes(search)) return false
      }

      if (
        columnFilters.topic &&
        !topic.toLowerCase().includes(columnFilters.topic.toLowerCase())
      ) {
        return false
      }
      if (
        columnFilters.type &&
        !qt.toLowerCase().includes(columnFilters.type.toLowerCase())
      ) {
        return false
      }
      if (
        columnFilters.difficulty &&
        !lvl.toLowerCase().includes(columnFilters.difficulty.toLowerCase())
      ) {
        return false
      }
      if (
        columnFilters.stem &&
        !stem.toLowerCase().includes(columnFilters.stem.toLowerCase())
      ) {
        return false
      }

      if (selectedTopics.length > 0 && !selectedTopics.includes(topic)) {
        return false
      }
      if (selectedTypes.length > 0 && !selectedTypes.includes(qt)) {
        return false
      }
      if (
        selectedDifficulties.length > 0 &&
        !selectedDifficulties.includes(lvl)
      ) {
        return false
      }

      // Kaynaksız sorular (source boş veya unknown)
      if (showOnlyNoSource) {
        if (source && source.trim() !== "" && source !== "unknown") {
          return false
        }
      }

      // LLM üretilenler (manual olmayan her şey)
      if (showOnlyLLM) {
        if (!source || source === "manual") {
          return false
        }
      }

      return true
    })
  }, [
    questions,
    searchTerm,
    columnFilters,
    selectedTopics,
    selectedTypes,
    selectedDifficulties,
    showOnlyNoSource,
    showOnlyLLM,
  ])

  const handleRowClick = (q: Question | any) => {
    setSelectedQuestion(q)

    const qt = q.question_type ?? ""
    const lvl = q.difficulty ?? q.level ?? ""

    // MCQ options
    const options: string[] = q.options ?? []

    // MCQ correct index
    let correctIndex: number | null = null
    if (
      Array.isArray(q.correct_option_indexes) &&
      q.correct_option_indexes.length > 0
    ) {
      const idx0 = q.correct_option_indexes[0]
      if (typeof idx0 === "number") {
        correctIndex = idx0
      }
    }

    // TRUE/FALSE correct value
    const correctAnswerBool: boolean | null =
      typeof q.correct_answer === "boolean" ? q.correct_answer : null

    // SHORT ANSWER
    const acceptedAnswers: string[] = q.accepted_answers ?? []
    const matchingType: string = q.matching_type ?? "case_insensitive"

    // OPEN ENDED
    const rubric: string = q.rubric ?? ""

    // SCENARIO
    const scenarioText: string = q.scenario ?? ""
    const steps: UiScenarioStep[] = Array.isArray(q.steps)
      ? q.steps.map((s: any) => ({
        ...s,
        _clientId: s._clientId ?? nanoid(),
        _action: undefined, // ilk açılışta değişmemiş kabul
      }))
      : []

    setEditForm({
      topic: q.topic ?? "",
      question_type: qt,
      difficulty: lvl,
      stem: q.stem ?? "",
      options,
      correct_index: correctIndex,
      correct_answer_bool: correctAnswerBool,
      accepted_answers: acceptedAnswers,
      matching_type: matchingType,
      rubric,
      scenario: scenarioText,
      steps,
    })

    setIsEditing(false)
    setIsModalOpen(true)
  }

  const handleDelete = async (id: number | string) => {
    const idStr = String(id)

    try {
      await deleteQuestion(token, idStr)

      setQuestions((prev: any[]) =>
        prev.filter((q) => String(q.id) !== idStr),
      )

      setSelectedIds((prev) =>
        prev.filter((x) => String(x) !== idStr),
      )

      // Eğer açık olan modal bu soruya aitse, kapat
      if (selectedQuestion && String((selectedQuestion as any).id) === idStr) {
        setSelectedQuestion(null)
        setIsModalOpen(false)
      }
    } catch (err) {
      console.error(err)
      alert("Silme işlemi sırasında bir hata oluştu.")
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return
    if (!confirm(`Seçili ${selectedIds.length} soruyu silmek istediğine emin misin?`)) return

    for (const id of selectedIds) {
      await handleDelete(id)
    }
  }

  const handleEditClick = () => {
    if (!selectedQuestion || !editForm) return
    setIsEditing(true)
  }

  const handleSaveEdit = async () => {
    if (!selectedQuestion || !editForm) return
    const id = String((selectedQuestion as any).id)

    try {
      const payload: any = {
        topic: editForm.topic,
        question_type: editForm.question_type,
        difficulty: editForm.difficulty,
        stem: editForm.stem,
      }

      // MCQ
      if (editForm.question_type === "mcq") {
        payload.options = editForm.options
        payload.correct_option_indexes =
          editForm.correct_index != null ? [editForm.correct_index] : []
      }

      // TRUE / FALSE
      if (editForm.question_type === "true_false") {
        if (editForm.correct_answer_bool !== null) {
          payload.correct_answer_bool = editForm.correct_answer_bool
        }
      }

      // SHORT ANSWER
      if (editForm.question_type === "short_answer") {
        payload.accepted_answers = (editForm.accepted_answers || [])
          .map((a) => a.trim())
          .filter((a) => a.length > 0)

        payload.matching_type = editForm.matching_type || "case_insensitive"
      }

      // OPEN ENDED
      if (editForm.question_type === "open_ended") {
        payload.rubric = editForm.rubric
      }

      // SCENARIO
      if (editForm.question_type === "scenario") {
        payload.scenario = editForm.scenario

        payload.steps = (editForm.steps || []).map((s, index) => {
          const { _clientId, _action, ...rest } = s as UiScenarioStep

          return {
            ...rest,
            order: (rest as any).order ?? index + 1,
            step_type: rest.step_type || "mcq",
            max_score:
              typeof rest.max_score === "number" ? rest.max_score : null,
            options: rest.options ?? [],
            correct_option_indexes: rest.correct_option_indexes ?? [],
            correct_answer_bool: rest.correct_answer_bool ?? null,
            accepted_answers: rest.accepted_answers ?? [],
            rubric: rest.rubric ?? "",
            matching_type: rest.matching_type ?? "case_insensitive",
            _action:
              _action ??
              (rest.step_id ? ("update" as const) : ("create" as const)),
          }
        })
      }

      const updated = await updateQuestion(id, payload, token)

      setQuestions((prev: any[]) =>
        prev.map((q) => (q.id === (updated as any).id ? updated : q)),
      )
      setSelectedQuestion(updated as Question)
      setIsEditing(false)
    } catch (err) {
      console.error(err)
      alert("Güncelleme sırasında bir hata oluştu.")
    }
  }

  const isRowSelected = (id: number | string) =>
    selectedIds.includes(String(id))

  const isAllFilteredSelected =
    !isLoading &&
    filteredQuestions.length > 0 &&
    filteredQuestions.every((q: any) => selectedIds.includes(String(q.id)))

  const toggleSelectAllFiltered = () => {
    if (isAllFilteredSelected) {
      setSelectedIds((prev) =>
        prev.filter(
          (id) => !filteredQuestions.some((q: any) => String(q.id) === String(id)),
        ),
      )
    } else {
      const idsToAdd = filteredQuestions
        .map((q: any) => String(q.id))
        .filter((id) => !selectedIds.includes(id))

      setSelectedIds((prev) => [...prev, ...idsToAdd])
    }
  }

  const toggleSingleSelection = (id: number | string) => {
    const idStr = String(id)
    setSelectedIds((prev) =>
      prev.includes(idStr)
        ? prev.filter((x) => x !== idStr)
        : [...prev, idStr],
    )
  }

  return (
    <TooltipProvider>
      <div className="flex gap-4">
        {/* Sol Filtre Paneli */}
        <aside className="hidden md:block w-64 shrink-0">
          <Card className="p-4 sticky top-4 space-y-4">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                <span className="text-sm font-semibold">Filtreler</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={clearAllFilters}
                title="Tüm filtreleri temizle"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>

            {/* Topic */}
            <div className="space-y-2">
              <span className="text-xs font-medium text-muted-foreground">Topic</span>
              <div className="flex flex-wrap gap-1.5">
                {topicOptions.length === 0 && (
                  <span className="text-xs text-muted-foreground">Henüz topic yok</span>
                )}
                {topicOptions.map((topic) => {
                  const active = selectedTopics.includes(topic)
                  return (
                    <button
                      key={topic}
                      type="button"
                      onClick={() => handleMultiFilterToggle("topic", topic)}
                      className={cn(
                        "rounded-full border px-2 py-1 text-[11px] leading-none transition",
                        active
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background text-muted-foreground hover:bg-muted",
                      )}
                    >
                      {topic}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Question Type */}
            <div className="space-y-2">
              <span className="text-xs font-medium text-muted-foreground">Question Type</span>
              <div className="flex flex-wrap gap-1.5">
                {typeOptions.length === 0 && (
                  <span className="text-xs text-muted-foreground">Henüz type yok</span>
                )}
                {typeOptions.map((type) => {
                  const active = selectedTypes.includes(type)
                  const label = QUESTION_TYPE_LABEL[type] ?? type
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => handleMultiFilterToggle("type", type)}
                      className={cn(
                        "rounded-full border px-2 py-1 text-[11px] leading-none transition",
                        active
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background text-muted-foreground hover:bg-muted",
                      )}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Difficulty */}
            <div className="space-y-2">
              <span className="text-xs font-medium text-muted-foreground">Difficulty</span>
              <div className="flex flex-wrap gap-1.5">
                {difficultyOptions.length === 0 && (
                  <span className="text-xs text-muted-foreground">Henüz difficulty yok</span>
                )}
                {difficultyOptions.map((diff) => {
                  const active = selectedDifficulties.includes(diff)
                  const label = DIFFICULTY_LABEL[diff] ?? diff
                  return (
                    <button
                      key={diff}
                      type="button"
                      onClick={() => handleMultiFilterToggle("difficulty", diff)}
                      className={cn(
                        "rounded-full border px-2 py-1 text-[11px] leading-none transition",
                        active
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background text-muted-foreground hover:bg-muted",
                      )}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Kaynak filtresi */}
            <div className="space-y-2 pt-1 border-t">
              <span className="text-xs font-medium text-muted-foreground">
                Kaynak
              </span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setShowOnlyNoSource((prev) => !prev)}
                  className={cn(
                    "rounded-full border px-2 py-1 text-[11px] leading-none transition",
                    showOnlyNoSource
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background text-muted-foreground hover:bg-muted",
                  )}
                >
                  Kaynağı olmayanlar
                </button>

                <button
                  type="button"
                  onClick={() => setShowOnlyLLM((prev) => !prev)}
                  className={cn(
                    "rounded-full border px-2 py-1 text-[11px] leading-none transition",
                    showOnlyLLM
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background text-muted-foreground hover:bg-muted",
                  )}
                >
                  LLM üretilenler
                </button>
              </div>
            </div>
          </Card>
        </aside>

        {/* Ana Alan */}
        <div className="flex-1 space-y-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold">Soru Bankası</h2>

            <div className="flex items-center gap-2 w-full sm:w-80">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Soru metni veya topic ara..."
                  className="pl-7 h-8 text-xs"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={clearAllFilters}
                title="Filtreleri temizle"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <Card className="overflow-hidden">
            {/* Info bar + Toplu Silme */}
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b">
              <span className="text-[11px] text-muted-foreground">
                Toplam <span className="font-semibold">{questions.length}</span> soru ·{" "}
                Filtrelenmiş: <span className="font-semibold">{filteredQuestions.length}</span> ·{" "}
                Seçili: <span className="font-semibold">{selectedIds.length}</span>
              </span>

              <div className="flex items-center gap-2">
                {selectedIds.length > 0 && (
                  <Button
                    size="sm"
                    variant="destructive"
                    className="h-7 text-[11px] px-2"
                    onClick={handleBulkDelete}
                  >
                    <Trash2 className="h-3 w-3 mr-1" />
                    Seçili {selectedIds.length} soruyu sil
                  </Button>
                )}

                {activeFilterKey && (
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                    Aktif sütun filtresi:
                    <strong className="capitalize">{activeFilterKey}</strong>
                    <button
                      type="button"
                      onClick={() => setActiveFilterKey(null)}
                      className="ml-1 rounded-full border px-1 text-[10px] leading-none hover:bg-muted"
                    >
                      Kapat
                    </button>
                  </span>
                )}
              </div>
            </div>

            <div className="relative">
              <Table>
                <TableHeader>
                  <TableRow className="border-b">
                    {/* Checkbox Header */}
                    <TableHead className="w-[36px] py-2 px-3">
                      <input
                        type="checkbox"
                        className="h-3.5 w-3.5 cursor-pointer"
                        checked={isAllFilteredSelected}
                        onChange={toggleSelectAllFiltered}
                      />
                    </TableHead>
                    <TableHead className="w-[60px] py-2 px-3 text-[11px] font-semibold text-muted-foreground">
                      ID
                    </TableHead>
                    <TableHead
                      className="w-[120px] py-2 px-3 text-[11px] font-semibold text-muted-foreground cursor-pointer select-none"
                      onClick={() =>
                        setActiveFilterKey((prev) => (prev === "topic" ? null : "topic"))
                      }
                    >
                      Topic
                      <ChevronDown className="inline-block ml-1 h-3 w-3 align-middle" />
                    </TableHead>
                    <TableHead
                      className="w-[120px] py-2 px-3 text-[11px] font-semibold text-muted-foreground cursor-pointer select-none"
                      onClick={() =>
                        setActiveFilterKey((prev) => (prev === "type" ? null : "type"))
                      }
                    >
                      Type
                      <ChevronDown className="inline-block ml-1 h-3 w-3 align-middle" />
                    </TableHead>
                    <TableHead
                      className="w-[110px] py-2 px-3 text-[11px] font-semibold text-muted-foreground cursor-pointer select-none"
                      onClick={() =>
                        setActiveFilterKey((prev) =>
                          prev === "difficulty" ? null : "difficulty",
                        )
                      }
                    >
                      Difficulty
                      <ChevronDown className="inline-block ml-1 h-3 w-3 align-middle" />
                    </TableHead>
                    <TableHead
                      className="py-2 px-3 text-[11px] font-semibold text-muted-foreground cursor-pointer select-none"
                      onClick={() =>
                        setActiveFilterKey((prev) => (prev === "stem" ? null : "stem"))
                      }
                    >
                      Soru
                      <ChevronDown className="inline-block ml-1 h-3 w-3 align-middle" />
                    </TableHead>
                    <TableHead className="w-[60px] py-2 px-3 text-[11px]" />
                  </TableRow>

                  {activeFilterKey && (
                    <TableRow className="border-b bg-muted/40">
                      <TableHead />
                      <TableHead colSpan={5} className="py-1.5 px-3">
                        <div className="flex items-center gap-2">
                          <Input
                            autoFocus
                            placeholder={`${activeFilterKey} filtresi...`}
                            className="h-7 text-xs"
                            value={columnFilters[activeFilterKey]}
                            onChange={(e) =>
                              setColumnFilters((prev) => ({
                                ...prev,
                                [activeFilterKey]: e.target.value,
                              }))
                            }
                          />
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7"
                            onClick={() =>
                              setColumnFilters((prev) => ({
                                ...prev,
                                [activeFilterKey]: "",
                              }))
                            }
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableHead>
                      <TableHead />
                    </TableRow>
                  )}
                </TableHeader>

                <TableBody>
                  {isLoading && (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className="py-6 text-center text-xs text-muted-foreground"
                      >
                        Sorular yükleniyor...
                      </TableCell>
                    </TableRow>
                  )}

                  {!isLoading && filteredQuestions.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className="py-6 text-center text-xs text-muted-foreground"
                      >
                        Eşleşen soru bulunamadı.
                      </TableCell>
                    </TableRow>
                  )}

                  {!isLoading &&
                    filteredQuestions.map((q: any) => {
                      const qt: string | undefined = q.question_type
                      const lvl: string | undefined = q.difficulty ?? q.level
                      const stem: string = q.stem ?? ""
                      const topic: string = q.topic ?? ""
                      const checked = isRowSelected(q.id)
                      const isSelectedForModal =
                        selectedQuestion && (selectedQuestion as any).id === q.id

                      return (
                        <TableRow
                          key={q.id}
                          onClick={() => handleRowClick(q)}
                          className={cn(
                            "cursor-pointer border-b last:border-0 transition-colors",
                            isSelectedForModal
                              ? "bg-primary/10 hover:bg-primary/15"
                              : checked
                                ? "bg-muted/80 hover:bg-muted"
                                : "hover:bg-muted/60",
                          )}
                        >
                          <TableCell
                            className="py-1.5 px-3"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              className="h-3.5 w-3.5 cursor-pointer"
                              checked={checked}
                              onChange={() => toggleSingleSelection(q.id)}
                            />
                          </TableCell>
                          <TableCell className="py-1.5 px-3 text-[11px] text-muted-foreground">
                            {q.id}
                          </TableCell>
                          <TableCell className="py-1.5 px-3 text-[11px] font-medium max-w-[140px] truncate">
                            {topic || "-"}
                          </TableCell>
                          <TableCell className="py-1.5 px-3 text-[11px] max-w-[140px] truncate">
                            {qt ? QUESTION_TYPE_LABEL[qt] ?? qt : "-"}
                          </TableCell>
                          <TableCell className="py-1.5 px-3 text-[11px] max-w-[120px] truncate">
                            {lvl ? DIFFICULTY_LABEL[lvl] ?? lvl : "-"}
                          </TableCell>

                          <TableCell className="py-1.5 px-3 text-[11px] max-w-[360px]">
                            {stem ? (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="block truncate align-middle">
                                    {stem}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xl text-xs whitespace-pre-wrap">
                                  {stem}
                                </TooltipContent>
                              </Tooltip>
                            ) : (
                              "-"
                            )}
                          </TableCell>

                          <TableCell
                            className="py-1.5 px-3 text-right"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => handleDelete(q.id)}
                            >
                              <Trash2 className="h-3.5 w-3.5 text-destructive" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                </TableBody>
              </Table>
            </div>
          </Card>

          {error && (
            <p className="text-xs text-destructive mt-1">
              {error}
            </p>
          )}
        </div>

        {/* Soru Detay Modal + Edit Button */}
        <Dialog
          open={isModalOpen}
          onOpenChange={(open) => {
            setIsModalOpen(open)
            if (!open) {
              setIsEditing(false)
            }
          }}
        >
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {isEditing ? "Soruyu Düzenle" : "Soru Detayı"}
                {selectedQuestion && (
                  <span className="text-xs font-normal text-muted-foreground">
                    #{(selectedQuestion as any).id}
                  </span>
                )}
              </DialogTitle>
            </DialogHeader>
            <DialogDescription className="sr-only">
              Bu diyalog, soru detaylarını görüp düzenlemenizi sağlar.
            </DialogDescription>

            {selectedQuestion && editForm && (
              <>
                {isEditing ? (
                  // EDIT MODE
                  <div className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      {/* Topic */}
                      <div className="space-y-1">
                        <p className="text-[11px] text-muted-foreground">Topic</p>
                        <Input
                          value={editForm.topic}
                          onChange={(e) =>
                            setEditForm((prev) =>
                              prev ? { ...prev, topic: e.target.value } : prev,
                            )
                          }
                          className="h-8 text-xs"
                        />
                      </div>

                      {/* Question Type */}
                      <div className="space-y-1">
                        <p className="text-[11px] text-muted-foreground">Question Type</p>
                        <select
                          value={editForm.question_type}
                          onChange={(e) =>
                            setEditForm((prev) =>
                              prev
                                ? { ...prev, question_type: e.target.value }
                                : prev,
                            )
                          }
                          className="h-8 w-full rounded-md border bg-background px-2 text-xs"
                        >
                          <option value="">Seç...</option>
                          <option value="mcq">Çoktan Seçmeli</option>
                          <option value="true_false">Doğru / Yanlış</option>
                          <option value="short_answer">Kısa Yanıt</option>
                          <option value="open_ended">Açık Uçlu</option>
                          <option value="scenario">Senaryo</option>
                        </select>
                      </div>

                      {/* Difficulty */}
                      <div className="space-y-1">
                        <p className="text-[11px] text-muted-foreground">Difficulty</p>
                        <select
                          value={editForm.difficulty}
                          onChange={(e) =>
                            setEditForm((prev) =>
                              prev
                                ? { ...prev, difficulty: e.target.value }
                                : prev,
                            )
                          }
                          className="h-8 w-full rounded-md border bg-background px-2 text-xs"
                        >
                          <option value="">Seç...</option>
                          <option value="easy">Kolay</option>
                          <option value="medium">Orta</option>
                          <option value="hard">Zor</option>
                        </select>
                      </div>
                    </div>

                    {/* Stem */}
                    <div className="space-y-1">
                      <p className="text-[11px] text-muted-foreground">Soru Metni</p>
                      <textarea
                        value={editForm.stem}
                        onChange={(e) =>
                          setEditForm((prev) =>
                            prev ? { ...prev, stem: e.target.value } : prev,
                          )
                        }
                        className="min-h-[120px] w-full rounded-md border bg-background p-2 text-sm"
                      />
                    </div>

                    {/* Senaryo genel metni */}
                    {editForm.question_type === "scenario" && (
                      <div className="space-y-1">
                        <p className="text-[11px] text-muted-foreground">Senaryo</p>
                        <textarea
                          value={editForm.scenario}
                          onChange={(e) =>
                            setEditForm((prev) =>
                              prev ? { ...prev, scenario: e.target.value } : prev,
                            )
                          }
                          className="min-h-[80px] w-full rounded-md border bg-background p-2 text-sm"
                          placeholder="Senaryonun bağlamını / hikâyesini buraya yaz..."
                        />
                      </div>
                    )}

                    {/* MCQ options edit */}
                    {editForm.question_type === "mcq" && (
                      <div className="space-y-3 mt-4 border-t pt-4">
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] font-semibold text-muted-foreground">
                            MCQ Seçenekleri
                          </p>
                          <span className="text-[11px] text-muted-foreground">
                            Doğru şık:{" "}
                            {editForm.correct_index != null
                              ? editForm.correct_index + 1
                              : "-"}
                          </span>
                        </div>

                        {editForm.options.map((opt, index) => (
                          <div key={index} className="flex items-center gap-2">
                            <Input
                              value={opt}
                              onChange={(e) =>
                                setEditForm((prev) =>
                                  prev
                                    ? {
                                      ...prev,
                                      options: prev.options.map((o, i) =>
                                        i === index ? e.target.value : o,
                                      ),
                                    }
                                    : prev,
                                )
                              }
                              className="flex-1 h-8 text-xs"
                            />

                            <input
                              type="radio"
                              name="correctOption"
                              className="h-3.5 w-3.5"
                              checked={editForm.correct_index === index}
                              onChange={() =>
                                setEditForm((prev) =>
                                  prev
                                    ? { ...prev, correct_index: index }
                                    : prev,
                                )
                              }
                            />

                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() =>
                                setEditForm((prev) =>
                                  prev
                                    ? {
                                      ...prev,
                                      options: prev.options.filter(
                                        (_, i) => i !== index,
                                      ),
                                      correct_index:
                                        prev.correct_index === index
                                          ? null
                                          : prev.correct_index != null &&
                                            prev.correct_index > index
                                            ? prev.correct_index - 1
                                            : prev.correct_index,
                                    }
                                    : prev,
                                )
                              }
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}

                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="text-xs"
                          onClick={() =>
                            setEditForm((prev) =>
                              prev
                                ? {
                                  ...prev,
                                  options: [...prev.options, ""],
                                }
                                : prev,
                            )
                          }
                        >
                          + Yeni Şık
                        </Button>
                      </div>
                    )}

                    {/* OPEN ENDED edit */}
                    {editForm.question_type === "open_ended" && (
                      <div className="space-y-3 mt-4 border-t pt-4">
                        <p className="text-[11px] font-semibold text-muted-foreground">
                          Açık Uçlu - Değerlendirme Rubriği
                        </p>
                        <textarea
                          value={editForm.rubric}
                          onChange={(e) =>
                            setEditForm((prev) =>
                              prev ? { ...prev, rubric: e.target.value } : prev,
                            )
                          }
                          className="min-h-[140px] w-full rounded-md border bg-background p-2 text-sm"
                          placeholder="Öğrenci cevaplarını değerlendirirken kullanacağın kriterleri buraya yaz..."
                        />
                      </div>
                    )}

                    {/* SHORT ANSWER edit */}
                    {editForm.question_type === "short_answer" && (
                      <div className="space-y-3 mt-4 border-t pt-4">
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] font-semibold text-muted-foreground">
                            Kısa Yanıt - Kabul Edilen Cevaplar
                          </p>
                        </div>

                        {editForm.accepted_answers.map((ans, index) => (
                          <div key={index} className="flex items-center gap-2">
                            <Input
                              value={ans}
                              onChange={(e) =>
                                setEditForm((prev) =>
                                  prev
                                    ? {
                                      ...prev,
                                      accepted_answers:
                                        prev.accepted_answers.map((a, i) =>
                                          i === index ? e.target.value : a,
                                        ),
                                    }
                                    : prev,
                                )
                              }
                              className="flex-1 h-8 text-xs"
                            />

                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() =>
                                setEditForm((prev) =>
                                  prev
                                    ? {
                                      ...prev,
                                      accepted_answers:
                                        prev.accepted_answers.filter(
                                          (_, i) => i !== index,
                                        ),
                                    }
                                    : prev,
                                )
                              }
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}

                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="text-xs"
                          onClick={() =>
                            setEditForm((prev) =>
                              prev
                                ? {
                                  ...prev,
                                  accepted_answers: [
                                    ...prev.accepted_answers,
                                    "",
                                  ],
                                }
                                : prev,
                            )
                          }
                        >
                          + Yeni Kabul Edilen Cevap
                        </Button>

                        <div className="space-y-1">
                          <p className="text-[11px] text-muted-foreground">
                            Eşleştirme Türü
                          </p>
                          <select
                            value={editForm.matching_type}
                            onChange={(e) =>
                              setEditForm((prev) =>
                                prev
                                  ? { ...prev, matching_type: e.target.value }
                                  : prev,
                              )
                            }
                            className="h-8 w-full rounded-md border bg-background px-2 text-xs"
                          >
                            <option value="case_insensitive">
                              Büyük/küçük harf duyarsız
                            </option>
                            <option value="case_sensitive">
                              Büyük/küçük harf duyarlı
                            </option>
                            <option value="contains">İçeriyor</option>
                          </select>
                        </div>
                      </div>
                    )}

                    {/* TRUE/FALSE edit */}
                    {editForm.question_type === "true_false" && (
                      <div className="space-y-2 mt-4 border-t pt-4">
                        <p className="text-[11px] font-semibold text-muted-foreground">
                          Doğru / Yanlış Cevabı
                        </p>
                        <div className="flex items-center gap-4 text-xs">
                          <label className="inline-flex items-center gap-1 cursor-pointer">
                            <input
                              type="radio"
                              name="tfAnswer"
                              className="h-3.5 w-3.5"
                              checked={editForm.correct_answer_bool === true}
                              onChange={() =>
                                setEditForm((prev) =>
                                  prev
                                    ? { ...prev, correct_answer_bool: true }
                                    : prev,
                                )
                              }
                            />
                            <span>Doğru</span>
                          </label>

                          <label className="inline-flex items-center gap-1 cursor-pointer">
                            <input
                              type="radio"
                              name="tfAnswer"
                              className="h-3.5 w-3.5"
                              checked={editForm.correct_answer_bool === false}
                              onChange={() =>
                                setEditForm((prev) =>
                                  prev
                                    ? { ...prev, correct_answer_bool: false }
                                    : prev,
                                )
                              }
                            />
                            <span>Yanlış</span>
                          </label>
                        </div>
                      </div>
                    )}

                    {/* SCENARIO steps edit */}
                    {editForm.question_type === "scenario" && (
                      <ScenarioStepsEditor
                        steps={editForm.steps || []}
                        onChange={(nextSteps) =>
                          setEditForm((prev) =>
                            prev ? { ...prev, steps: nextSteps } : prev,
                          )
                        }
                      />
                    )}
                  </div>
                ) : (
                  // VIEW MODE
                  <div className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="space-y-0.5">
                        <p className="text-[11px] text-muted-foreground">Topic</p>
                        <p className="font-medium">
                          {(selectedQuestion as any).topic ?? "-"}
                        </p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-[11px] text-muted-foreground">
                          Question Type
                        </p>
                        <p className="font-medium">
                          {(() => {
                            const qt = (selectedQuestion as any).question_type
                            if (!qt) return "-"
                            return QUESTION_TYPE_LABEL[qt] ?? qt
                          })()}
                        </p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-[11px] text-muted-foreground">Difficulty</p>
                        <p className="font-medium">
                          {(() => {
                            const lvl =
                              (selectedQuestion as any).difficulty ??
                              (selectedQuestion as any).level
                            if (!lvl) return "-"
                            return DIFFICULTY_LABEL[lvl] ?? lvl
                          })()}
                        </p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-[11px] text-muted-foreground">Kaynak</p>
                        <p className="font-medium">
                          {(() => {
                            const src = (selectedQuestion as any).source_model
                            if (!src || src === "unknown") return "Bilinmiyor"
                            if (src === "manual") return "Manuel"
                            return src
                          })()}
                        </p>
                      </div>
                    </div>

                    {/* Stem */}
                    <div className="space-y-1">
                      <p className="text-[11px] text-muted-foreground">Soru Metni</p>
                      <p className="rounded-md border bg-muted/40 p-2 text-sm whitespace-pre-wrap">
                        {(selectedQuestion as any).stem ?? "-"}
                      </p>
                    </div>

                    {/* MCQ Detayları */}
                    {(selectedQuestion as any).question_type === "mcq" && (
                      <div className="space-y-2 mt-2 border-t pt-2">
                        <p className="text-[11px] text-muted-foreground font-semibold">
                          Seçenekler
                        </p>
                        <ul className="list-disc list-inside space-y-1 text-xs">
                          {Array.isArray((selectedQuestion as any).options) &&
                            (selectedQuestion as any).options.map(
                              (opt: string, idx: number) => {
                                const correctIndexes: number[] =
                                  (selectedQuestion as any).correct_option_indexes ?? []
                                const isCorrect = Array.isArray(correctIndexes)
                                  ? correctIndexes.includes(idx)
                                  : false
                                return (
                                  <li
                                    key={idx}
                                    className={cn(
                                      "flex items-center gap-1",
                                      isCorrect && "font-semibold text-emerald-700",
                                    )}
                                  >
                                    <span>{opt}</span>
                                    {isCorrect && (
                                      <span className="text-[10px]">
                                        (Doğru cevap)
                                      </span>
                                    )}
                                  </li>
                                )
                              },
                            )}
                        </ul>
                      </div>
                    )}

                    {/* TRUE / FALSE Detayları */}
                    {(selectedQuestion as any).question_type === "true_false" &&
                      typeof (selectedQuestion as any).correct_answer ===
                      "boolean" && (
                        <div className="space-y-1 mt-2 border-t pt-2">
                          <p className="text-[11px] text-muted-foreground font-semibold">
                            Doğru / Yanlış Cevabı
                          </p>
                          <p className="text-xs">
                            Doğru cevap:{" "}
                            <span className="font-semibold">
                              {(selectedQuestion as any).correct_answer
                                ? "Doğru"
                                : "Yanlış"}
                            </span>
                          </p>
                        </div>
                      )}

                    {/* SHORT ANSWER Detayları */}
                    {(selectedQuestion as any).question_type === "short_answer" && (
                      <div className="space-y-2 mt-2 border-t pt-2">
                        <p className="text-[11px] text-muted-foreground font-semibold">
                          Kabul Edilen Cevaplar
                        </p>
                        {Array.isArray((selectedQuestion as any).accepted_answers) &&
                          (selectedQuestion as any).accepted_answers.length > 0 ? (
                          <ul className="list-disc list-inside space-y-1 text-xs">
                            {(selectedQuestion as any).accepted_answers.map(
                              (ans: string, idx: number) => (
                                <li key={idx}>{ans}</li>
                              ),
                            )}
                          </ul>
                        ) : (
                          <p className="text-[11px] text-muted-foreground">
                            Tanımlı kabul edilen cevap yok.
                          </p>
                        )}

                        <p className="text-[10px] text-muted-foreground">
                          Eşleştirme türü:{" "}
                          <span className="font-semibold">
                            {(selectedQuestion as any).matching_type ??
                              "case_insensitive"}
                          </span>
                        </p>
                      </div>
                    )}

                    {/* OPEN ENDED Detayları */}
                    {(selectedQuestion as any).question_type === "open_ended" && (
                      <div className="space-y-2 mt-2 border-t pt-2">
                        <p className="text-[11px] text-muted-foreground font-semibold">
                          Değerlendirme Rubriği
                        </p>
                        <p className="rounded-md border bg-muted/40 p-2 text-xs whitespace-pre-wrap">
                          {(selectedQuestion as any).rubric ||
                            "Rubrik tanımlanmamış."}
                        </p>
                      </div>
                    )}

                    {/* SCENARIO Detayları */}
                    {(selectedQuestion as any).question_type === "scenario" && (
                      <div className="space-y-3 mt-3 border-t pt-3">
                        {/* Senaryo metni */}
                        <div className="space-y-1">
                          <p className="text-[11px] text-muted-foreground">Senaryo</p>
                          <p className="rounded-md border bg-muted/40 p-2 text-xs whitespace-pre-wrap">
                            {(selectedQuestion as any).scenario ||
                              "Senaryo metni yok."}
                          </p>
                        </div>

                        {/* Adımlar */}
                        <div className="space-y-2">
                          <p className="text-[11px] text-muted-foreground font-semibold">
                            Adımlar
                          </p>

                          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                            {Array.isArray((selectedQuestion as any).steps) &&
                              (selectedQuestion as any).steps.length > 0 ? (
                              (selectedQuestion as any).steps.map(
                                (step: any, idx: number) => {
                                  const rawType = String(step.step_type ?? "").toLowerCase()
                                  const stepTypeLabels: Record<string, string> = {
                                    mcq: "Çoktan Seçmeli",
                                    true_false: "Doğru / Yanlış",
                                    short_answer: "Kısa Yanıt",
                                    open_ended: "Açık Uçlu",
                                  }
                                  const typeLabel =
                                    stepTypeLabels[rawType] || rawType || "Adım"

                                  const options: string[] = step.options ?? []
                                  const correctIndexes: number[] =
                                    step.correct_option_indexes ?? []

                                  return (
                                    <div
                                      key={step.step_id ?? idx}
                                      className="rounded-md border bg-background p-2 text-xs space-y-1"
                                    >
                                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                                        <span>Step {idx + 1}</span>
                                        <span className="font-medium">
                                          {typeLabel}
                                        </span>
                                      </div>

                                      <p className="font-medium whitespace-pre-wrap">
                                        {step.stem ?? "(Metin yok)"}
                                      </p>

                                      {/* MCQ seçenekler */}
                                      {options.length > 0 && (
                                        <ul className="mt-1 list-disc list-inside space-y-0.5">
                                          {options.map((opt, i) => {
                                            const isCorrect = Array.isArray(
                                              correctIndexes,
                                            )
                                              ? correctIndexes.includes(i)
                                              : false
                                            return (
                                              <li
                                                key={i}
                                                className={cn(
                                                  "text-[11px]",
                                                  isCorrect && "font-semibold",
                                                )}
                                              >
                                                {opt}
                                                {isCorrect && (
                                                  <span className="ml-1 text-[10px] text-emerald-600">
                                                    ✓
                                                  </span>
                                                )}
                                              </li>
                                            )
                                          })}
                                        </ul>
                                      )}

                                      {/* True/False cevap */}
                                      {typeof step.correct_answer_bool ===
                                        "boolean" && (
                                          <p className="mt-1 text-[11px]">
                                            Doğru cevap:{" "}
                                            <span className="font-semibold">
                                              {step.correct_answer_bool
                                                ? "Doğru"
                                                : "Yanlış"}
                                            </span>
                                          </p>
                                        )}

                                      {/* Short answer kabul edilen cevaplar */}
                                      {Array.isArray(step.accepted_answers) &&
                                        step.accepted_answers.length > 0 && (
                                          <div className="mt-1">
                                            <p className="text-[10px] text-muted-foreground">
                                              Kabul edilen cevaplar:
                                            </p>
                                            <p className="text-[11px">
                                              {step.accepted_answers.join(", ")}
                                            </p>
                                          </div>
                                        )}

                                      {/* Rubrik */}
                                      {step.rubric && (
                                        <div className="mt-1">
                                          <p className="text-[10px] text-muted-foreground">
                                            Rubrik:
                                          </p>
                                          <p className="text-[11px] whitespace-pre-wrap">
                                            {step.rubric}
                                          </p>
                                        </div>
                                      )}

                                      {/* Puan */}
                                      {typeof step.max_score === "number" && (
                                        <p className="mt-1 text-[10px] text-muted-foreground">
                                          Maksimum puan:{" "}
                                          <span className="font-semibold">
                                            {step.max_score}
                                          </span>
                                        </p>
                                      )}
                                    </div>
                                  )
                                },
                              )
                            ) : (
                              <p className="text-[11px] text-muted-foreground">
                                Tanımlı adım yok.
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            <DialogFooter className="mt-4">
              {isEditing ? (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditing(false)}
                  >
                    Vazgeç
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSaveEdit}
                  >
                    Kaydet
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-1"
                    onClick={handleEditClick}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    <span className="text-xs">Edit Question</span>
                  </Button>

                  <Button
                    type="button"
                    size="sm"
                    onClick={() => setIsModalOpen(false)}
                  >
                    Kapat
                  </Button>
                </>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  )
}

/* ---------------------------
   Scenario Steps Editor
--------------------------- */

function ScenarioStepsEditor({
  steps,
  onChange,
}: {
  steps: UiScenarioStep[]
  onChange: (steps: UiScenarioStep[]) => void
}) {
  const addStep = () => {
    const newStep: UiScenarioStep = {
      _clientId: nanoid(),
      _action: "create",
      step_type: "mcq",
      stem: "",
      prompt: "",
      max_score: 1,
      options: ["", "", "", ""],
      correct_option_indexes: [0],
    }
    onChange([...(steps || []), newStep])
  }

  const updateStep = (clientId: string, patch: Partial<UiScenarioStep>) => {
    const next = (steps || []).map((s) => {
      if (s._clientId !== clientId) return s
      const merged: UiScenarioStep = {
        ...s,
        ...patch,
      }
      if (merged.step_id && !merged._action) {
        merged._action = "update"
      }
      return merged
    })
    onChange(next)
  }

  const deleteStep = (clientId: string) => {
    const next: UiScenarioStep[] = []
    for (const s of steps || []) {
      if (s._clientId !== clientId) {
        next.push(s)
        continue
      }

      if (s.step_id) {
        // DB'de var → delete flag’le, ama listede tut (backend’e gitsin)
        next.push({
          ...s,
          _action: "delete",
        })
      }
      // step_id yoksa (yeni oluşturulmuşsa) hiç eklemiyoruz → tamamen silinmiş olur
    }
    onChange(next)
  }

  const visibleSteps = (steps || []).filter((s) => s._action !== "delete")

  return (
    <div className="space-y-2 mt-4 border-t pt-4">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold text-muted-foreground">
          Senaryo Adımları
        </p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="text-xs"
          onClick={addStep}
        >
          + Adım Ekle
        </Button>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {visibleSteps.length === 0 && (
          <p className="text-[11px] text-muted-foreground">
            Henüz tanımlı adım yok.
          </p>
        )}

        {visibleSteps.map((step, idx) => (
          <ScenarioStepRow
            key={step.step_id ?? step._clientId ?? idx}
            index={idx}
            step={step}
            onChange={(patch) => updateStep(step._clientId, patch)}
            onDelete={() => deleteStep(step._clientId)}
          />
        ))}
      </div>
    </div>
  )
}

type StepQuestionType = "mcq" | "true_false" | "short_answer" | "open_ended"

function ScenarioStepRow({
  index,
  step,
  onChange,
  onDelete,
}: {
  index: number
  step: UiScenarioStep
  onChange: (patch: Partial<UiScenarioStep>) => void
  onDelete: () => void
}) {
  const currentType: StepQuestionType =
    (step.step_type as StepQuestionType) || "mcq"

  const update = (patch: Partial<UiScenarioStep>) => {
    onChange(patch)
  }

  const handleTypeChange = (value: StepQuestionType) => {
    const base: Partial<UiScenarioStep> = {
      step_type: value,
    }

    if (value === "mcq") {
      base.options = step.options?.length ? step.options : ["", "", "", ""]
      base.correct_option_indexes =
        step.correct_option_indexes?.length &&
          Array.isArray(step.correct_option_indexes)
          ? step.correct_option_indexes
          : [0]
      base.correct_answer_bool = undefined
      base.accepted_answers = undefined
      base.rubric = undefined
    } else if (value === "true_false") {
      base.correct_answer_bool =
        typeof step.correct_answer_bool === "boolean"
          ? step.correct_answer_bool
          : true
      base.options = undefined
      base.correct_option_indexes = undefined
      base.accepted_answers = undefined
      base.rubric = undefined
    } else if (value === "short_answer") {
      base.accepted_answers =
        step.accepted_answers && step.accepted_answers.length > 0
          ? step.accepted_answers
          : [""]
      base.options = undefined
      base.correct_option_indexes = undefined
      base.correct_answer_bool = undefined
      base.rubric = undefined
    } else if (value === "open_ended") {
      base.rubric = step.rubric ?? ""
      base.options = undefined
      base.correct_option_indexes = undefined
      base.correct_answer_bool = undefined
      base.accepted_answers = undefined
    }

    update(base)
  }

  const handleMcqOptionChange = (i: number, value: string) => {
    const options = [...(step.options || [])]
    options[i] = value
    update({ options })
  }

  const handleCorrectIndexChange = (i: number) => {
    update({ correct_option_indexes: [i] })
  }

  return (
    <Card className="p-2 text-xs space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted-foreground w-12">
              Step {index + 1}
            </span>

            <Input
              type="number"
              className="h-7 w-20 text-[11px]"
              value={step.max_score ?? 1}
              onChange={(e) =>
                update({ max_score: Number(e.target.value) || 0 })
              }
              placeholder="Puan"
            />

            <Select
              value={currentType}
              onValueChange={(v: StepQuestionType) =>
                handleTypeChange(v)
              }
            >
              <SelectTrigger className="h-7 w-32 text-[11px]">
                <SelectValue placeholder="Tür" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mcq">MCQ</SelectItem>
                <SelectItem value="true_false">Doğru/Yanlış</SelectItem>
                <SelectItem value="short_answer">Kısa Yanıt</SelectItem>
                <SelectItem value="open_ended">Açık Uçlu</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Input
            className="h-7 text-[11px]"
            placeholder="Adım başlığı / kısa stem"
            value={step.stem ?? ""}
            onChange={(e) => update({ stem: e.target.value })}
          />

          <Textarea
            className="min-h-[60px] text-[11px]"
            placeholder="Adım prompt / soru metni"
            value={step.prompt ?? ""}
            onChange={(e) => update({ prompt: e.target.value })}
          />
        </div>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onDelete}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Tür bazlı alanlar */}
      {currentType === "mcq" && (
        <div className="space-y-1">
          {(step.options || ["", "", "", ""]).map((opt, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <Input
                className="h-7 text-[11px]"
                value={opt}
                onChange={(e) => handleMcqOptionChange(idx, e.target.value)}
                placeholder={`Seçenek ${idx + 1}`}
              />
              <input
                type="radio"
                className="h-3.5 w-3.5"
                checked={
                  (step.correct_option_indexes || [0])[0] === idx
                }
                onChange={() => handleCorrectIndexChange(idx)}
              />
            </div>
          ))}
        </div>
      )}

      {currentType === "true_false" && (
        <div className="flex items-center gap-4">
          <label className="inline-flex items-center gap-1 cursor-pointer">
            <input
              type="radio"
              className="h-3.5 w-3.5"
              checked={step.correct_answer_bool === true}
              onChange={() => update({ correct_answer_bool: true })}
            />
            <span>Doğru</span>
          </label>
          <label className="inline-flex items-center gap-1 cursor-pointer">
            <input
              type="radio"
              className="h-3.5 w-3.5"
              checked={step.correct_answer_bool === false}
              onChange={() => update({ correct_answer_bool: false })}
            />
            <span>Yanlış</span>
          </label>
        </div>
      )}

      {currentType === "short_answer" && (
        <div className="space-y-1">
          {(step.accepted_answers || [""]).map((ans, i) => (
            <Input
              key={i}
              className="h-7 text-[11px]"
              value={ans}
              onChange={(e) => {
                const arr = [...(step.accepted_answers || [""])]
                arr[i] = e.target.value
                update({ accepted_answers: arr })
              }}
              placeholder={`Kabul edilen cevap ${i + 1}`}
            />
          ))}
        </div>
      )}

      {currentType === "open_ended" && (
        <Textarea
          className="min-h-[60px] text-[11px]"
          placeholder="Bu adım için değerlendirme rubriği..."
          value={step.rubric ?? ""}
          onChange={(e) => update({ rubric: e.target.value })}
        />
      )}
    </Card>
  )
}
