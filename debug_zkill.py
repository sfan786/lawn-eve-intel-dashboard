import requests
import json

ZKILL_BASE = "https://zkillboard.com/api"
ALLIANCE_ID = 99009927  # Deepwater Hooligans

def test_zkill():
    # Try getting the last 24 hours (86400 seconds)
    url = f"{ZKILL_BASE}/kills/allianceID/{ALLIANCE_ID}/pastSeconds/86400/"
    headers = {
        "Accept": "application/json",
        "User-Agent": "AstrumMechanica-IntelDash/Debug"
    }
    
    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Received {len(data)} records")
            if len(data) > 0:
                print("First record sample:")
                print(json.dumps(data[0], indent=2))
        else:
            print(f"Error: {resp.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_zkill()
