import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.repositories.audit_repo import get_audit_logs

def main():
    print("Fetching Audit Logs...")
    logs = get_audit_logs(limit=5)
    
    for log in logs:
        print(f"Log ID: {log.id}, User ID: {log.user_id}, Username: {log.username}, Action: {log.action}")
        
    if logs and logs[0].username is not None:
        print("\n✅ Username field is populated (at least for some logs).")
    else:
        print("\n⚠️ Username field might still be None (check if users exist for these logs).")

if __name__ == "__main__":
    main()
