
import requests

def search_zkill(term):
    url = "https://zkillboard.com/autocomplete/" + term + "/"
    headers = {"User-Agent": "AstrumMechanica-IntelDash/1.0"}
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        print(f"zKill Results for '{term}':")
        for item in data:
            if item.get('type') == 'alliance':
                print(f"  {item.get('name')} [ID: {item.get('id')}]")
    except Exception as e:
        print(f"Error: {e}")

search_zkill("The Rejected")
search_zkill("T.RD")
search_zkill("Put The Fries")
