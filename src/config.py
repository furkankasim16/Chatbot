import os
AI_PROVIDERS = [
  {"name":"openrouter-mistral","url":"https://openrouter.ai/api/v1/chat/completions","model":"mistralai/mistral-7b-instruct:free","keys":[os.getenv("OPENROUTER_API_KEY"), os.getenv("OPENROUTER_KEY_2")]},
  {"name":"hf-inference","url":"https://api-inference.huggingface.co/models","model":"mistralai/Mistral-7B-Instruct-v0.2","keys":[os.getenv("HF_API_KEY1")]},
  {"name":"hf-inference","url":"https://api-inference.huggingface.co/models","model":"mistralai/Mistral-7B-Instruct-v0.2","keys":[os.getenv("HF_API_KEY2")]}
]