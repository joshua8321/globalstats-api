from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
import json

api_url = "https://api.coingecko.com/api/v3/coins/markets"

cache_file = "marketcap_cache.json"
json_file = "all_symbols.json"
mapping_json_file = "coingecko_coins.json"
x_cg_demo_api_key="CG-CwBppKStMC73hsdZzfobBG7f"

app = FastAPI()

def load_tokens_from_json():
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        symbols = [symbol["symbol"] for symbol in data["symbols"]]
        
    with open(mapping_json_file, "r", encoding="utf-8") as file:
        mapping_data = json.load(file)
        token_id_list = []

        for symbol in symbols:
            matching_entries = [item for item in mapping_data if item["symbol"].upper() == symbol]

            if matching_entries:
                entry_with_no_platforms = next((item for item in matching_entries if not item["platforms"]), None)
                if entry_with_no_platforms:
                    token_id_list.append(entry_with_no_platforms["id"])
                else:
                    token_id_list.append(matching_entries[0]["id"])
            else:
                token_id_list.append(symbol)
                    
    return symbols, token_id_list
        
def fetch_marketcap_data(based_symbols, coingecko_symbols):

    # Define the number of tokens per request
    tokens_per_request = 100

    total_tokens = len(coingecko_symbols)
    total_requests = (total_tokens + tokens_per_request - 1) // tokens_per_request
    
    # Initialize an empty list to store the data
    data = []

    # Make multiple requests
    for i in range(total_requests):
        # Calculate the start and end indices for each request
        start_index = i * tokens_per_request
        end_index = (i + 1) * tokens_per_request

        # Get the tokens for the current request
        tokens = coingecko_symbols[start_index:end_index]

        # Create the request parameters
        params = {
            "ids": ",".join(tokens),
            "vs_currency": "usd",
            "x_cg_demo_api_key": x_cg_demo_api_key
        }

        # Send the request and append the data to the result list
        response = requests.get(api_url, params=params)
        data.extend(response.json())
    
    result = {}
    for based_symbol, coingecko_symbol in zip(based_symbols, coingecko_symbols):
        matching_entry = next((entry for entry in data if entry["id"] == coingecko_symbol), {})
        result[based_symbol] = matching_entry
    return result

def save_to_cache(data):
    with open(cache_file, "w") as file:
        json.dump(data, file)

def load_from_cache():
    try:
        with open(cache_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def update_marketcap_data():

    print("api call start")
    based_symbols, coingecko_symbols = load_tokens_from_json()
    marketcap_data = fetch_marketcap_data(based_symbols, coingecko_symbols)
    save_to_cache(marketcap_data)
    print("api call end")



scheduler = BackgroundScheduler()
scheduler.add_job(update_marketcap_data, "interval", minutes=10)
scheduler.start()

#update_marketcap_data()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/market-data")
def get_market_data(token: str):
    cached_data = load_from_cache()
    if cached_data:
        if token in cached_data:
            return cached_data[token]
        else:
            return {"message": f"No market cap data available for token '{token}'."}
    else:
        return {"message": "No market cap data available."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)