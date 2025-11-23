import requests
import time
import config

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Waiting for server to start...")
    time.sleep(2)

    # 1. Create Account
    print("Testing Create Account...")
    payload = {
        "mail_id": "update_test",
        "email": "original@example.com",
        "password": "pass",
        "imap_server": "imap.orig.com",
        "access_token": "token1",
        "default_sender_filter": "sender1"
    }
    try:
        resp = requests.post(f"{BASE_URL}/admin/accounts", json=payload, timeout=config.HTTP_TIMEOUT)
        print(f"Create: {resp.status_code}")
        account_id = resp.json().get("id")
    except Exception as e:
        print(f"Create Failed: {e}")
        return

    if not account_id:
        print("Skipping update/delete tests due to create failure")
        return

    # 2. Update Account
    print("\nTesting Update Account...")
    update_payload = {
        "email": "updated@example.com",
        "default_sender_filter": "sender2"
    }
    resp = requests.put(f"{BASE_URL}/admin/accounts/{account_id}", json=update_payload, timeout=config.HTTP_TIMEOUT)
    print(f"Update: {resp.status_code}")
    print(f"Update Resp: {resp.json()}")

    # 3. Verify Update
    resp = requests.get(f"{BASE_URL}/admin/accounts", timeout=config.HTTP_TIMEOUT)
    accounts = resp.json()
    updated_acc = next((a for a in accounts if a["id"] == account_id), None)
    if updated_acc and updated_acc["email"] == "updated@example.com":
        print("Update Verified: SUCCESS")
    else:
        print("Update Verified: FAILED")

    # 4. Delete Account
    print("\nTesting Delete Account...")
    resp = requests.delete(f"{BASE_URL}/admin/accounts/{account_id}", timeout=config.HTTP_TIMEOUT)
    print(f"Delete: {resp.status_code}")

    # 5. Verify Delete
    resp = requests.get(f"{BASE_URL}/admin/accounts", timeout=config.HTTP_TIMEOUT)
    accounts = resp.json()
    deleted_acc = next((a for a in accounts if a["id"] == account_id), None)
    if not deleted_acc:
        print("Delete Verified: SUCCESS")
    else:
        print("Delete Verified: FAILED")

if __name__ == "__main__":
    test_api()
