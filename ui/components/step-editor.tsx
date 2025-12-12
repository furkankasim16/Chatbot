// components/admin/step-editor.tsx

import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Trash2 } from "lucide-react"
import type { ScenarioStep, QuestionType } from "@/app/types/quiz"

interface StepEditorProps {
  step: ScenarioStep
  index: number
  onChange: (step: ScenarioStep) => void
  onDelete: () => void
}

const STEP_TYPES: QuestionType[] = [
  "mcq",
  "true_false",
  "short_answer",
  "open_ended",
]

export function StepEditor({ step, index, onChange, onDelete }: StepEditorProps) {
  const update = (patch: Partial<ScenarioStep>) => {
    const merged: ScenarioStep = {
      ...step,
      ...patch,
    }

    // eğer DB'den gelen bir step ise ve daha önce action set edilmediyse → update
    if (merged.step_id && !merged._action) {
      merged._action = "update"
    }

    onChange(merged)
  }

  const updateMcqOption = (optIndex: number, value: string) => {
    const options = [...(step.options || [])]
    options[optIndex] = value
    update({ options })
  }

  const setCorrectIndex = (idx: number) => {
    update({ correct_option_indexes: [idx] }) // şimdilik tek doğru olacak şekilde
  }

  const handleTypeChange = (value: QuestionType) => {
    const base: ScenarioStep = {
      ...step,
      step_type: value,
    }

    if (value === "mcq") {
      base.options = step.options?.length ? step.options : ["", "", "", ""]
      base.correct_option_indexes = base.correct_option_indexes?.length
        ? base.correct_option_indexes
        : [0]
      delete base.correct_answer_bool
      delete base.accepted_answers
      delete base.rubric
    } else if (value === "true_false") {
      base.correct_answer_bool =
        typeof step.correct_answer_bool === "boolean" ? step.correct_answer_bool : true
      delete base.options
      delete base.correct_option_indexes
      delete base.accepted_answers
      delete base.rubric
    } else if (value === "short_answer") {
      base.accepted_answers = step.accepted_answers?.length
        ? step.accepted_answers
        : [""]
      delete base.options
      delete base.correct_option_indexes
      delete base.correct_answer_bool
      delete base.rubric
    } else if (value === "open_ended") {
      base.rubric = step.rubric ?? ""
      delete base.options
      delete base.correct_option_indexes
      delete base.correct_answer_bool
      delete base.accepted_answers
    }

    update(base)
  }

  const currentType =
    (step.step_type as QuestionType) && STEP_TYPES.includes(step.step_type as QuestionType)
      ? (step.step_type as QuestionType)
      : "mcq"

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground w-8">
              #{index}
            </span>

            <Input
              className="w-24"
              type="number"
              min={0}
              value={step.max_score ?? 1}
              onChange={(e) => update({ max_score: Number(e.target.value) })}
              placeholder="Puan"
            />

            <Select
              value={currentType}
              onValueChange={(v: QuestionType) => handleTypeChange(v)}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Step type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mcq">MCQ</SelectItem>
                <SelectItem value="true_false">True/False</SelectItem>
                <SelectItem value="short_answer">Short Answer</SelectItem>
                <SelectItem value="open_ended">Open Ended</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Input
            placeholder="Adım kısa başlığı (opsiyonel)"
            value={step.stem ?? ""}
            onChange={(e) => update({ stem: e.target.value })}
          />

          <Textarea
            placeholder="Adım prompt / soru metni"
            value={step.prompt ?? ""}
            onChange={(e) => update({ prompt: e.target.value })}
          />
        </div>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onDelete}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      {/* Tür bazlı alt alanlar */}
      {currentType === "mcq" && (
        <div className="space-y-2">
          {(step.options || ["", "", "", ""]).map((opt, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <Input
                value={opt}
                onChange={(e) => updateMcqOption(idx, e.target.value)}
                placeholder={`Seçenek ${idx + 1}`}
              />
              <input
                type="radio"
                checked={(step.correct_option_indexes || [0])[0] === idx}
                onChange={() => setCorrectIndex(idx)}
              />
            </div>
          ))}
        </div>
      )}

      {currentType === "true_false" && (
        <div className="flex gap-2">
          <Button
            type="button"
            variant={step.correct_answer_bool === true ? "default" : "outline"}
            onClick={() => update({ correct_answer_bool: true })}
          >
            Doğru
          </Button>
          <Button
            type="button"
            variant={step.correct_answer_bool === false ? "default" : "outline"}
            onClick={() => update({ correct_answer_bool: false })}
          >
            Yanlış
          </Button>
        </div>
      )}

      {currentType === "short_answer" && (
        <div className="space-y-2">
          {(step.accepted_answers || [""]).map((ans, idx) => (
            <Input
              key={idx}
              value={ans}
              onChange={(e) => {
                const arr = [...(step.accepted_answers || [""])]
                arr[idx] = e.target.value
                update({ accepted_answers: arr })
              }}
              placeholder={`Kabul edilen cevap ${idx + 1}`}
            />
          ))}
        </div>
      )}

      {currentType === "open_ended" && (
        <Textarea
          placeholder="Değerlendirme rubric'i / notu"
          value={step.rubric ?? ""}
          onChange={(e) => update({ rubric: e.target.value })}
        />
      )}
    </Card>
  )
}
