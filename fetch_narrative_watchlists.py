import os
import requests
import time
from collections import deque, OrderedDict
import logging
from urllib.parse import urlparse, parse_qsl, urlunparse
import argparse
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
API_KEY = os.getenv('COINGECKO_API_KEY', '')
HEADERS = {'x-cg-demo-api-key': API_KEY}
BASE_URL = "https://api.coingecko.com/api/v3"

class RateLimiter:
    """Handles rate limiting for API requests."""
    def __init__(self, max_requests, period):
        self.requests = deque()
        self.max_requests = max_requests
        self.period = period

    def wait(self):
        """Ensures compliance with rate limit policies using a monotonic clock."""
        current_time = time.monotonic()
        while self.requests and self.requests[0] < current_time - self.period:
            self.requests.popleft()
        if len(self.requests) >= self.max_requests:
            time_to_wait = self.requests[0] + self.period - current_time
            time.sleep(time_to_wait)
        self.requests.append(time.monotonic())

def safe_request(url, params=None, rate_limiter=None):
    """Performs API requests with error handling and rate limiting."""
    rate_limiter.wait()
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json(), response.headers
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logging.warning("Rate limit exceeded, retrying...")
            time.sleep(10)
            return safe_request(url, params, rate_limiter)
        logging.error(f"HTTP request failed with status {e.response.status_code}: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None, None

def fetch_categories(rate_limiter, limit):
    """Fetches categories from the API."""
    logging.info("Fetching categories from CoinGecko")
    url = f"{BASE_URL}/coins/categories?order=market_cap_desc"
    categories, _ = safe_request(url, rate_limiter=rate_limiter)
    if categories:
        categories = categories[:limit]
        logging.info(f"Fetched {len(categories)} categories")
        return categories
    else:
        logging.warning("Failed to fetch categories")
        return []

def fetch_coins_by_category(category_id, category_name, rate_limiter, max_coins=1000):
    """Fetches coin data for a specific category, handling pagination manually."""
    logging.info(f"Fetching coins for category: {category_name}")
    url = f"{BASE_URL}/coins/markets"
    params = {
        'vs_currency': 'usd',
        'category': category_id,
        'order': 'market_cap_desc',
        'per_page': 250,
        'page': 1
    }
    coins = []
    has_more_data = True

    while has_more_data and len(coins) < max_coins:
        response, _ = safe_request(url, params=params, rate_limiter=rate_limiter)
        if response:
            new_coins = [coin['id'] for coin in response]
            coins.extend(new_coins[:max_coins - len(coins)])  # Ensure we do not exceed max_coins
            logging.debug(f"Fetched {len(new_coins)} coins for category {category_name} on page {params['page']}")
            # Check if we have reached the maximum coins or if there are no more coins to fetch
            if len(coins) >= max_coins or len(new_coins) < params['per_page']:
                has_more_data = False
            else:
                params['page'] += 1  # Increment page number for next iteration
        else:
            logging.warning(f"Failed to fetch more coins for category {category_name} on page {params['page']}")
            has_more_data = False

    logging.info(f"Fetched {len(coins)} total coins for category {category_name}")
    return coins


def fetch_tickers_for_exchange(exchange_id, exchange_name, target, rate_limiter):
    """Fetches ticker data for a specific exchange."""
    logging.info(f"Fetching tickers for exchange: {exchange_name}")
    url = f"{BASE_URL}/exchanges/{exchange_id}/tickers"
    params = {'coin_ids': target['id'], 'page': 1}
    tickers = []
    while True:
        response, headers = safe_request(url, params=params, rate_limiter=rate_limiter)
        if response:
            tickers.extend([t for t in response['tickers'] if t['target'] == target['symbol']])
            links = parse_link_header(headers.get('Link', ''))
            if 'next' in links:
                url, params = update_request_url(links['next'])
            else:
                break
        else:
            break
    logging.info(f"Collected {len(tickers)} tickers for {exchange_name}")
    return tickers

def parse_link_header(link_header):
    """Parses the 'Link' header used for pagination."""
    links = {}
    link_pattern = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')
    for link in link_header.split(','):
        match = link_pattern.search(link)
        if match:
            links[match.group(2)] = match.group(1)
    return links

def update_request_url(next_url):
    """Updates the request URL and parameters from 'Link' header."""
    url_parts = urlparse(next_url)
    new_params = dict(parse_qsl(url_parts.query))
    new_url = urlunparse(url_parts._replace(query=None))
    return new_url, new_params


def save_to_tradingview_watchlist(filename, categorized_data, is_index=False):
    """Saves ticker or index data to a file formatted for TradingView."""
    # Handle directory creation
    directory = os.path.dirname(filename)

    # Create the directory if it does not exist
    if not os.path.exists(directory) and directory != "":
        os.makedirs(directory)
        logging.info(f"Directory created: {directory}")

    logging.info(f"Saving data to file: {filename}")
    with open(filename, 'w') as file:
        for category_name, data in categorized_data.items():
            file.write(f"###{category_name}\n")
            if is_index:
                file.write(f"{data}\n\n")
            else:
                for ticker in data:
                    file.write(f"{ticker}\n")

    logging.info(f"Watchlist saved to {filename}")

def create_tradingview_index_string(categorized_tickers):
    """Creates index strings for TradingView."""
    return {category: '(' + '*'.join(tickers[:10]) + f")^(1/{len(tickers[:10])})" for category, tickers in categorized_tickers.items()}

def main(category_limit, coin_limit_per_category, combined_watchlist):
    """Main function to orchestrate data fetching and processing."""
    rate_limiter = RateLimiter(max_requests=1, period=2)
    categories = fetch_categories(rate_limiter, category_limit)
    
    category_coins = OrderedDict((cat['id'], fetch_coins_by_category(cat['id'], cat['name'], rate_limiter, coin_limit_per_category)) for cat in categories)

    exchanges = [
        {"api_id": "binance", "name": "Binance"},
        {"api_id": "bybit_spot", "name": "Bybit"}
    ]
    target_coin = {'id': 'tether', 'symbol': 'USDT'}

    for exchange in exchanges:
        tickers = fetch_tickers_for_exchange(exchange['api_id'], exchange['name'], target_coin, rate_limiter)
        ticker_dict = {ticker['coin_id']: f"{exchange['name'].upper()}:{ticker['base']}{ticker['target']}" for ticker in tickers}

        categorized_tickers = OrderedDict((cat['name'], []) for cat in categories)
        for cat in categories:
            for coin_id in category_coins[cat['id']]:
                if coin_id in ticker_dict:
                    categorized_tickers[cat['name']].append(ticker_dict[coin_id])

        tradingview_indexes = create_tradingview_index_string(categorized_tickers)
        
        if combined_watchlist:
            filename = f"Narratives - {exchange['name']} - Combined.txt"
            path = f"Watchlists/{filename}"
            save_to_tradingview_watchlist(path, categorized_tickers)
        else:
            for cat in categorized_tickers:
                filename = f"Narratives - {exchange['name']} - {cat}.txt"
                safe_filename = "".join(i for i in filename if i not in "\/:*?<>|")
                path = f"Watchlists/{safe_filename}"
                save_to_tradingview_watchlist(path, {cat: categorized_tickers[cat]})
        
        filename = f"Narratives - {exchange['name']} - Indicies.txt"
        save_to_tradingview_watchlist(filename, tradingview_indexes, is_index=True)

    logging.info("Data collection complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and process crypto data for TradingView.")
    parser.add_argument("-l", "--category_limit", type=int, default=500, help="Limit the number of categories to process.")
    parser.add_argument("-c", "--combined", type=bool, default=False, help="Combine all watchlists into one.")
    parser.add_argument("-m", "--max_coins", type=int, default=1000, help="Maximum number of coins to fetch per category.")
    args = parser.parse_args()
    main(args.category_limit, args.max_coins, args.combined)


