import os

def fix_csv():
    path = "app/data/intent_dataset.csv"
    try:
        with open(path, "rb") as f:
            content = f.read()
            
        # Remove null bytes (common artifact of cat >> from utf16 to utf8 in powershell)
        fixed = content.replace(b"\x00", b"")
        
        # Decode and re-encode to ensure validity
        text = fixed.decode("utf-8", errors="ignore")
        
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            
        print(f"Fixed CSV. New size: {len(text)} chars.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_csv()
