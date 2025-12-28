
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.domain.services.rag_service import rag_service
from app.core.config import settings

def main():
    print("Re-indexing intents from CSV...")
    csv_path = os.path.join("app", "data", "intent_dataset.csv")
    count = rag_service.index_csv_intents(csv_path)
    print(f"Done. Indexed {count} intents.")

if __name__ == "__main__":
    main()
