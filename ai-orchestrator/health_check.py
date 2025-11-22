# Health check script for deployment platforms
import sys
import requests

def check_health():
    try:
        # Check orchestrator health
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✓ Orchestrator healthy")
            return 0
        else:
            print("✗ Orchestrator unhealthy")
            return 1
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())
