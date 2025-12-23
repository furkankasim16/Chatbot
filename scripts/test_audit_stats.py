import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.repositories.audit_repo import get_audit_stats, add_audit_log
from app.domain.schemas.audit import AuditLog

def main():
    print("Testing Audit Stats...")
    
    # 1. Add some dummy logs to ensure we have data
    print("Adding dummy logs...")
    try:
        add_audit_log(AuditLog(user_id=1, action="TEST_LOGIN", created_at="2025-12-18T10:00:00", details={}))
        add_audit_log(AuditLog(user_id=1, action="TEST_LOGIN", created_at="2025-12-18T11:00:00", details={}))
        add_audit_log(AuditLog(user_id=1, action="TEST_GENERATE", created_at="2025-12-18T12:00:00", details={}))
    except Exception as e:
        print(f"Warning: Could not add dummy logs (maybe DB locked?): {e}")

    # 2. Fetch stats
    stats = get_audit_stats()
    
    print("\nDaily Activity:")
    print(json.dumps(stats.get("daily_activity", []), indent=2))
    
    print("\nAction Distribution:")
    print(json.dumps(stats.get("action_distribution", []), indent=2))
    
    # Assertions
    if "daily_activity" in stats and "action_distribution" in stats:
        print("\n✅ Audit Stats structure is correct.")
    else:
        print("\n❌ Audit Stats structure is MISSING keys.")

if __name__ == "__main__":
    main()
