
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user

# Mock user
def mock_get_current_user():
    return {"id": 1, "username": "testadmin", "email": "test@admin.com", "is_admin": True}

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_rag_flow():
    # 1. Test Index
    with open("test_rag.pdf", "rb") as f:
        response = client.post(
            "/api/v1/rag/index",
            files={"file": ("test_rag.pdf", f, "application/pdf")},
            data={"topic": "general"}
        )
    
    print(f"Index Status: {response.status_code}")
    print(f"Index Response: {response.json()}")
    assert response.status_code == 200

    # 2. Test Query
    response = client.post(
        "/api/v1/rag/query",
        json={"query": "capital of France", "n_results": 1}
    )
    
    print(f"Query Status: {response.status_code}")
    print(f"Query Response: {response.json()}")
    assert response.status_code == 200
    assert "Paris" in str(response.json())
    
    print("RAG Verification Successful!")

if __name__ == "__main__":
    try:
        test_rag_flow()
    except Exception as e:
        print(f"Test Failed: {e}")
