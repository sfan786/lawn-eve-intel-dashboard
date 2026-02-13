
import requests

def search_ticker(term):
    url = "https://esi.evetech.net/latest/search/"
    params = {
        "categories": "alliance",
        "datasource": "tranquility",
        "language": "en",
        "search": term,
        "strict": "false"  # allow partial match to find things
    }
    try:
        resp = requests.get(url, params=params)
        print(f"URL: {resp.url}")
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return

        data = resp.json()
        print(f"Search results for '{term}': {data}")
        
        if 'alliance' in data:
            for aid in data['alliance']:
                r = requests.get(f"https://esi.evetech.net/latest/alliances/{aid}/?datasource=tranquility")
                info = r.json()
                print(f"ID {aid}: {info.get('name')} [{info.get('ticker')}]")
    except Exception as e:
        print(f"Exception: {e}")

print("--- Searching 'The Rejected' ---")
search_ticker("The Rejected")
print("\n--- Searching 'T.RD' ---")
search_ticker("T.RD")
print("\n--- Searching 'PUT THE FRIES IN THE BAG' ---")
search_ticker("PUT THE FRIES IN THE BAG")
