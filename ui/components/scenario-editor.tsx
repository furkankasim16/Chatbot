// components/admin/scenario-editor.tsx

"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import type { Question, ScenarioStep } from "@/app/types/quiz"
import { StepEditor } from "./step-editor"
import { nanoid } from "nanoid"

interface ScenarioEditorProps {
  question: Question          // type: "scenario"
  onChange: (q: Question) => void
}

export function ScenarioEditor({ question, onChange }: ScenarioEditorProps) {
  const [local, setLocal] = useState<Question>(question)

  useEffect(() => {
    setLocal(question)
  }, [question.id])

  const updateField = (key: keyof Question, value: any) => {
    const updated = { ...local, [key]: value }
    setLocal(updated)
    onChange(updated)
  }

  const updateSteps = (steps: ScenarioStep[]) => {
    const updated = { ...local, steps }
    setLocal(updated)
    onChange(updated)
  }

  const handleStepChange = (index: number, step: ScenarioStep) => {
    const steps = [...(local.steps || [])]
    steps[index] = step
    updateSteps(steps)
  }

  const handleAddStep = () => {
    const steps = [...(local.steps || [])]
    const nextOrder = steps.length + 1

    const newStep: ScenarioStep = {
      _clientId: nanoid(),
      _action: "create",
      step_type: "mcq",
      stem: "",
      prompt: "",
      max_score: 1,
      options: ["", "", "", ""],
      correct_option_indexes: [0],
    }

    updateSteps([...steps, newStep])
  }

  const handleDeleteStep = (index: number) => {
    const steps = [...(local.steps || [])]
    const step = steps[index]

    if (step.step_id) {
      // DB'deki step → _action: delete (backend bunu silsin)
      steps[index] = {
        ...step,
        _action: "delete",
      }
    } else {
      // Henüz create edilmemiş lokal step → tamamen kaldır
      steps.splice(index, 1)
    }

    updateSteps(steps)
  }

  const visibleSteps = (local.steps || []).filter(s => s._action !== "delete")

  return (
    <div className="space-y-4">
      {/* Senaryo genel alanları */}
      <Card className="p-4 space-y-3">
        <Input
          placeholder="Senaryo başlığı / kısa açıklama"
          value={local.scenario ?? ""}
          onChange={(e) => updateField("scenario", e.target.value)}
        />

        <Textarea
          placeholder="Genel senaryo bağlamı (öğrenciye gösterilecek uzun açıklama)"
          value={local.stem}
          onChange={(e) => updateField("stem", e.target.value)}
        />
      </Card>

      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">Steps</h3>
        <Button size="sm" type="button" onClick={handleAddStep}>
          Adım Ekle
        </Button>
      </div>

      <div className="space-y-3">
        {visibleSteps.map((step, index) => (
          <StepEditor
            key={step.step_id ?? step._clientId ?? index}
            step={step}
            index={index + 1}
            onChange={(updated) => handleStepChange(index, updated)}
            onDelete={() => handleDeleteStep(index)}
          />
        ))}
      </div>
    </div>
  )
}
