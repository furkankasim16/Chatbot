import csv
import json
import random
import requests
import time
import os

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3:instruct"
OUTPUT_FILE = "app/data/intent_dataset.csv"
TOTAL_SAMPLES_PER_INTENT = 200  # 5 intents * 200 = 1000 samples

INTENTS = {
    "greeting": "Turkish greeting phrases. Examples: 'Merhaba', 'Selam', 'Günaydın', 'Selamlar', 'Hey'.",
    "farewell": "Turkish farewell phrases. Examples: 'Görüşürüz', 'Hoşçakal', 'Bay bay', 'İyi akşamlar', 'Çıkış yap'.",
    "quiz_start": "Turkish commands to start a quiz or ask for a question. Examples: 'Quiz başlat', 'Soru sor', 'Kendimi test etmek istiyorum', 'Bana bir soru sor', 'Sınav yap'.",
    "topic_ask": "Turkish questions asking about a specific topic or concept (like Scrum, Agile, Software). Examples: 'Scrum nedir?', 'Agile prensipleri nelerdir?', 'Database ne işe yarar?', 'API nasıl çalışır?'.",
    "other": "Random Turkish sentences that are NOT greetings, farewells, or quiz requests. Can be about weather, personal questions to bot, or random noise. Examples: 'Hava bugün nasıl?', 'Senin adın ne?', 'Bugün ne yedin?', 'Fenerbahçe maçı kaç kaç bitti?'."
}

def generate_batch(intent_name, intent_description, count=20):
    prompt = f"""
    You are a data generator. Generate {count} DIFFERENT and UNIQUE {intent_description}
    Return ONLY the list of sentences, one per line. Do not number them. Do not write explanations.
    Ensure they are in Turkish.
    """
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("response", "").strip()
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line[0].isdigit()] # Clean simple numbered lists if AI ignores instruction
        return lines
    except Exception as e:
        print(f"Error generating for {intent_name}: {e}")
        return []

def main():
    # Ensure data directory exists
    os.makedirs("app/data", exist_ok=True)
    
    all_data = []
    
    print(f"🚀 Starting data generation using {MODEL_NAME}...")
    print(f"Target: {TOTAL_SAMPLES_PER_INTENT} samples per intent. Total: {TOTAL_SAMPLES_PER_INTENT * len(INTENTS)}")

    for intent, desc in INTENTS.items():
        print(f"\n📂 Processing Intent: {intent}...")
        collected = set()
        
        while len(collected) < TOTAL_SAMPLES_PER_INTENT:
            batch_size = 50
            lines = generate_batch(intent, desc, batch_size)
            
            for line in lines:
                # Basic cleaning
                clean_line = line.replace('"', '').replace("'", "")
                if clean_line and clean_line not in collected:
                    collected.add(clean_line)
            
            print(f"   - Progress: {len(collected)}/{TOTAL_SAMPLES_PER_INTENT}")
            time.sleep(0.5) # Be nice to the API
            
        for text in list(collected)[:TOTAL_SAMPLES_PER_INTENT]:
            all_data.append([text, intent])

    # Shuffle data
    random.shuffle(all_data)
    
    # Write to CSV
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["text", "intent"])
        writer.writerows(all_data)
        
    print(f"\n✅ Dataset generated successfully saved to {OUTPUT_FILE}")
    print(f"Total rows: {len(all_data)}")

if __name__ == "__main__":
    main()
