import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Waiting for server to start...")
    time.sleep(3)

    # 1. Create Account
    print("Testing Create Account...")
    payload = {
        "mail_id": "test_001",
        "email": "test@example.com",
        "password": "password123",
        "imap_server": "imap.example.com",
        "access_token": "secret_token",
        "default_sender_filter": "sender@example.com"
    }
    try:
        response = requests.post(f"{BASE_URL}/admin/accounts", json=payload)
        print(f"Create Status: {response.status_code}")
        print(f"Create Response: {response.json()}")
    except Exception as e:
        print(f"Create Failed: {e}")
        return

    # 2. List Accounts
    print("\nTesting List Accounts...")
    response = requests.get(f"{BASE_URL}/admin/accounts")
    print(f"List Status: {response.status_code}")
    print(f"List Response: {response.json()}")

    # 3. Fetch Mail (Expected to fail connection, but pass auth)
    print("\nTesting Fetch Mail...")
    response = requests.get(f"{BASE_URL}/mail", params={"mail_id": "test_001", "token": "secret_token"})
    print(f"Fetch Status: {response.status_code}")
    print(f"Fetch Response: {response.json()}")

    # 4. Fetch Mail (Invalid Token)
    print("\nTesting Fetch Mail (Invalid Token)...")
    response = requests.get(f"{BASE_URL}/mail", params={"mail_id": "test_001", "token": "wrong_token"})
    print(f"Fetch Invalid Status: {response.status_code}")
    print(f"Fetch Invalid Response: {response.json()}")

if __name__ == "__main__":
    test_api()
