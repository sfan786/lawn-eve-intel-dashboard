
import requests

def search_ticker(ticker):
    url = "https://esi.evetech.net/latest/search/?categories=alliance&datasource=tranquility&language=en&search=" + ticker + "&strict=true"
    resp = requests.get(url)
    data = resp.json()
    print(f"Search for '{ticker}': {data}")
    
    if 'alliance' in data:
        for aid in data['alliance']:
            r = requests.get(f"https://esi.evetech.net/latest/alliances/{aid}/?datasource=tranquility")
            print(f"ID {aid}: {r.json()}")

search_ticker("The Rejected")
search_ticker("T.RD")
