#!/usr/bin/env python3
"""
Enhanced Trading Script with Redundant Data Sources
Drop-in replacement for original Trading_Script.py with improved reliability
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import numpy as np
import sys
import logging

# Add the current directory to path to import our redundant fetcher
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

try:
    from redundant_data_fetcher import KLSEDataFetcher
    REDUNDANT_FETCHER_AVAILABLE = True
except ImportError:
    print("⚠️  Redundant data fetcher not available, falling back to yfinance only")
    REDUNDANT_FETCHER_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize redundant data fetcher if available
data_fetcher = KLSEDataFetcher() if REDUNDANT_FETCHER_AVAILABLE else None

def get_stock_data_enhanced(ticker):
    """
    Enhanced stock data fetching with redundancy
    Falls back to original yfinance if redundant system unavailable
    """
    # Determine if this is a Malaysian stock (.KL suffix) or US stock
    is_malaysian_stock = ticker.endswith('.KL')
    
    if REDUNDANT_FETCHER_AVAILABLE and data_fetcher and is_malaysian_stock:
        # Use redundant data fetcher for Malaysian stocks only
        try:
            # Extract stock code (remove .KL suffix for data fetcher)
            stock_code = ticker.replace('.KL', '')
            result = data_fetcher.get_stock_price(stock_code)
            
            if result:
                logger.info(f"✅ Enhanced fetch successful for {ticker} via {result['source']}")
                return {
                    'price': result['price'],
                    'data_available': True,
                    'source': result['source'],
                    'currency': result.get('currency', 'MYR'),
                    'volume': result.get('volume'),
                    'timestamp': result.get('fetch_time')
                }
            else:
                logger.warning(f"⚠️  Enhanced fetch failed for {ticker}, trying fallback")
        except Exception as e:
            logger.warning(f"⚠️  Enhanced fetch error for {ticker}: {e}, trying fallback")
    
    # Fallback to original yfinance method (for US stocks or if Malaysian fetch fails)
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            price = round(data["Close"].iloc[-1], 2)
            logger.info(f"✅ Fallback fetch successful for {ticker}")
            return {
                'price': price,
                'data_available': True,
                'source': 'yfinance_direct',
                'currency': 'MYR' if is_malaysian_stock else 'USD',
                'volume': data['Volume'].iloc[-1] if 'Volume' in data else None,
                'timestamp': datetime.now().isoformat()
            }
        else:
            logger.error(f"❌ No data available for {ticker}")
            return {'data_available': False, 'source': 'none'}
    except Exception as e:
        logger.error(f"❌ Fallback fetch failed for {ticker}: {e}")
        return {'data_available': False, 'source': 'error', 'error': str(e)}

# === Enhanced portfolio processing with redundancy ===
def process_portfolio(portfolio, starting_cash):
    """
    Enhanced version of original process_portfolio with redundant data sources
    Maintains exact same output format for compatibility
    """
    today = datetime.now().strftime("%Y-%m-%d")
    results = []
    total_value = 0
    total_pnl = 0
    cash = starting_cash
    
    logger.info(f"Processing portfolio for {today} with {len(portfolio)} positions")
    print(f"📊 Processing Portfolio - {today}")
    if REDUNDANT_FETCHER_AVAILABLE:
        print("🔄 Enhanced redundant data fetching enabled")
    else:
        print("⚠️  Using standard yfinance (redundant system not available)")
    print("=" * 50)
    
    # Track data source usage for reporting
    source_usage = {}
    
    for _, stock in portfolio.iterrows():
        ticker = stock["ticker"]
        shares = int(stock["shares"])
        cost = stock["buy_price"]
        stop = stock["stop_loss"]
        
        # Get stock data using enhanced method
        stock_data = get_stock_data_enhanced(ticker)
        
        if not stock_data['data_available']:
            print(f"❌ No data for {ticker}")
            row = {
                "Date": today,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": cost,
                "Stop Loss": stop,
                "Current Price": "",
                "Total Value": "",
                "PnL": "",
                "Action": "NO DATA",
                "Cash Balance": "",
                "Total Equity": ""
            }
        else:
            price = stock_data['price']
            source = stock_data['source']
            
            # Track source usage
            source_usage[source] = source_usage.get(source, 0) + 1
            
            # Use appropriate precision based on currency
            if stock_data.get('currency') == 'MYR':
                price = round(price, 3)  # Malaysian sen precision
            else:
                price = round(price, 2)  # USD cents precision
            
            value = round(price * shares, 2)
            pnl = round((price - cost) * shares, 2)

            if price <= stop:
                action = "SELL - Stop Loss Triggered"
                cash += value
                log_sell_enhanced(ticker, shares, price, cost, pnl, action, source)
                print(f"🚨 STOP LOSS: {ticker} sold at {price:.3f} (via {source})")
            else:
                action = "HOLD"
                total_value += value
                total_pnl += pnl
                print(f"✅ HOLDING: {ticker} @ {price:.3f} | PnL: {pnl:+.2f} (via {source})")

            row = {
                "Date": today,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": cost,
                "Stop Loss": stop,
                "Current Price": price,
                "Total Value": value,
                "PnL": pnl,
                "Action": action,
                "Cash Balance": "",
                "Total Equity": ""
            }

        results.append(row)

    # === Add TOTAL row (maintaining original format) ===
    total_row = {
        "Date": today,
        "Ticker": "TOTAL",
        "Shares": "",
        "Cost Basis": "",
        "Stop Loss": "",
        "Current Price": "",
        "Total Value": round(total_value, 2),
        "PnL": round(total_pnl, 2),
        "Action": "",
        "Cash Balance": round(cash, 2),
        "Total Equity": round(total_value + cash, 2)
    }
    results.append(total_row)

    # === Display summary with data source info ===
    print("=" * 50)
    print(f"📊 Portfolio Summary:")
    print(f"   Total Value: {total_value:.2f}")
    print(f"   Cash: {cash:.2f}")
    print(f"   Total Equity: {total_value + cash:.2f}")
    print(f"   Total PnL: {total_pnl:+.2f}")
    
    if source_usage:
        print(f"📡 Data Sources Used:")
        for source, count in source_usage.items():
            print(f"   {source}: {count} stocks")
    
    # Get system health if redundant fetcher available
    if REDUNDANT_FETCHER_AVAILABLE and data_fetcher:
        try:
            health = data_fetcher.get_source_performance()
            if health:
                print(f"🏥 Data Source Health:")
                for source, stats in health.items():
                    print(f"   {source}: {stats['success_rate']}% success")
        except Exception as e:
            logger.warning(f"Could not get system health: {e}")

    # === Save to CSV (original format maintained) ===
    file = f"chatgpt_portfolio_update.csv"  # Use relative path in Scripts folder
    df = pd.DataFrame(results)

    if os.path.exists(file):
        existing = pd.read_csv(file)
        existing = existing[existing["Date"] != today]  # Remove today's rows
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(file, index=False)
    print(f"💾 Portfolio saved to {file}")
    
    return portfolio  # Return original portfolio for compatibility

# === Enhanced trade logging ===
def log_sell_enhanced(ticker, shares, price, cost, pnl, action, source):
    """
    Enhanced version of log_sell with data source tracking
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Sold": shares,
        "Sell Price": price,
        "Cost Basis": cost,
        "PnL": pnl,
        "Action": action,
        "Data Source": source,
        "Timestamp": datetime.now().isoformat()
    }
    
    # Save to enhanced trade log
    log_file = f"chatgpt_trade_log.csv"  # Use relative path in Scripts folder
    log_df = pd.DataFrame([log])
    
    if os.path.exists(log_file):
        existing = pd.read_csv(log_file)
        log_df = pd.concat([existing, log_df], ignore_index=True)
    
    log_df.to_csv(log_file, index=False)
    logger.info(f"Trade logged: {ticker} sold {shares} shares at {price}")

# === Original log_sell function for backward compatibility ===
def log_sell(ticker, shares, price, cost, pnl, action):
    """
    Original log_sell function maintained for backward compatibility
    """
    log_sell_enhanced(ticker, shares, price, cost, pnl, action, 'legacy')

# === Test/Demo function ===
def test_enhanced_system():
    """
    Test the enhanced system with sample data
    """
    print("🧪 Testing Enhanced Trading System")
    print("=" * 50)
    
    # Sample portfolio for testing
    test_portfolio = pd.DataFrame({
        'ticker': ['AAPL', 'MSFT'],  # Use US stocks for initial test
        'shares': [10, 5],
        'buy_price': [150.0, 300.0],
        'stop_loss': [140.0, 280.0]
    })
    
    print("📋 Test Portfolio:")
    print(test_portfolio)
    print()
    
    # Process test portfolio
    result = process_portfolio(test_portfolio, 100.0)
    
    return result

# === Main execution ===
if __name__ == "__main__":
    print("🚀 Enhanced Trading Script with Redundant Data Sources")
    print("=" * 60)
    
    # Check if we should run a test or process real data
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_enhanced_system()
    else:
        print("💡 Integration complete! Enhanced trading script ready.")
        print("   - Drop-in replacement for original Trading_Script.py")
        print("   - Maintains exact same CSV output format")
        print("   - Adds redundant data source capabilities")
        print("   - Enhanced error handling and logging")
        print()
        print("🔧 Usage:")
        print("   - Replace calls to original process_portfolio() function")
        print("   - All existing code will work with enhanced version")
        print("   - Additional data source info available in logs")
        print()
        print("🧪 To test: python Trading_Script_Enhanced.py test")
