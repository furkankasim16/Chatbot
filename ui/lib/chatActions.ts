// src/lib/chatActions.ts
export function handleChatActions(resp: any) {
  const actions = resp?.actions
  if (!Array.isArray(actions)) return

  const start = actions.find((a: any) => a?.type === "start_quiz")
  if (start?.payload) {
    localStorage.setItem("pending_quiz", JSON.stringify(start.payload))
    window.dispatchEvent(new Event("start-quiz-from-chat"))
  }
}
