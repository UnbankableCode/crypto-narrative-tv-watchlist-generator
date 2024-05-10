# Crypto Narrative Watchlist Generator

## Purpose
This script aids in crypto narrative hunting by creating [TradingView](https://www.tradingview.com/) watchlists for each category sourced from [CoinGecko](https://www.coingecko.com/en/categories). It also generates synthetic indices for each category, allowing users to chart narratives as a whole or individual assets within a category comprehensively. These indices can be incorporated into TradingView indicators, such as [Cole Garner](https://twitter.com/ColeGarnersTake/)'s [Asset Rotation Aperture](https://www.tradingview.com/script/I9yPY5x6-Asset-Rotation-Aperture/), for enhanced market analysis.

## Features
- **Narrative-Based Watchlists**: Automatically creates importable watchlists for each category and exchange.
- **Synthetic Indices Generation**: Generates watchlists for each exchange that contain synthetic indices, providing a consolidated view of each category's performance.

## Setup
### Get an API Key
1. Obtain an API key from CoinGecko by registering on their [API page](https://www.coingecko.com/en/api). 
2. Click "Get Your API Key Now", then click "Create Demo Account" for a free key.


## How to Use
1. **Setting the API Key**:
Make sure to set your API key in the terminal:

   ```bash
   export COINGECKO_API_KEY='your_api_key_here'
   ```

2. **Run the Script**:
Execute the script with the desired options:

   ```
   python fetch_narrative_watchlists.py --category_limit 500 --max_coins 1000 --combined False
   ```
   - `--category_limit`: Restricts the top number of categories to fetch from CoinGecko. Categories are sorted by market cap.
   - `--max_coins`: Restricts the top number of coins to fetch per category from CoinGecko. Coins are sorted by market cap.
   - `--combined`: Whether to create a combined watchlist or individual lists for each category (default is False for individual lists).

## Known Issues
- **Processing Time**: With the free API key rate limit, fetching all categories and coin pairs with default settings takes approximately 15 minutes.
- **TradingView Limitations**: Due to TradingView's restrictions on duplicate entries in a single watchlist, the script defaults to creating individual watchlists to prevent missing entries. Additionally, when creating the synthetic indicies, TradingView only allows 10 assets per index.

## Todo
- [ ] **Expand Asset Types**: Introduce the ability to fetch perpetual contracts.
- [ ] **Rate Limit Options**: Create different rate limit pre-sets based on CoinGecko's limits.


## Contributing
We appreciate contributions that improve the functionality and usability of this project. Please fork the repository, make your changes, and submit a pull request for review.