import sys
import os
import asyncio
sys.path.append(os.getcwd())

from app.domain.schemas.chat import ChatTurnRequest, ChatMode
from app.domain.services.chat_service import handle_fast_turn
from app.domain.services.chat_system_prompts import get_system_prompt

async def run_tests():
    print("--- Test 1: Explicit Topic Match 'support_flow' ---")
    req = ChatTurnRequest(
        message="support_flow",
        mode=ChatMode.TUTOR,
        topic=None,
        level="beginner",
        history=[]
    )
    res = await handle_fast_turn(req)
    if res and res.actions and res.actions[0]["type"] == "start_quiz" and res.actions[0]["payload"]["topic"] == "support_flow":
        print("✅ PASS: Correctly identified topic 'support_flow' and started quiz.")
    else:
        print(f"❌ FAIL: Expected start_quiz for 'support_flow', got: {res}")

    print("\n--- Test 2: Intent 'Bana hikaye anlat' (Should NOT be quiz) ---")
    req2 = ChatTurnRequest(
        message="Bana bir hikaye anlat",
        mode=ChatMode.TUTOR,
        topic="security_policy",
        level="beginner",
        history=[]
    )
    res2 = await handle_fast_turn(req2)
    if res2 is None:
        print("✅ PASS: 'Bana hikaye anlat' correctly bypassed fast logic (will go to LLM).")
    else:
        # If it returns a response, it likely caught it as a quiz intent
        if res2.raw_model.startswith("rag:classifier-quiz") or "Quiz hazır" in res2.reply:
             print(f"❌ FAIL: 'Bana hikaye anlat' was falsely identified as QUIZ.")
        else:
             print(f"⚠️ NOTE: Handled by something else: {res2.raw_model}")

    print("\n--- Test 3: System Prompt Language Enforcement ---")
    prompt = get_system_prompt(ChatMode.TUTOR, language="tr")
    if "ÖNEMLİ: Cevapların istisnasız SADECE TÜRKÇE olmalıdır" in prompt:
        print("✅ PASS: Turkish enforcement string present in prompt.")
    else:
        print("❌ FAIL: Turkish enforcement string MISSING.")

if __name__ == "__main__":
    asyncio.run(run_tests())
