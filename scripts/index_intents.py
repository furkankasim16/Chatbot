import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.domain.services.rag_service import rag_service

CSV_PATH = "app/data/intent_dataset.csv"

def main():
    print(f"🚀 Indexing intents from {CSV_PATH}...")
    count = rag_service.index_csv_intents(CSV_PATH)
    if count > 0:
        print(f"✅ Successfully indexed {count} intents into ChromaDB 'intents' collection.")
    else:
        print("❌ Indexing failed or no data found.")

if __name__ == "__main__":
    main()
