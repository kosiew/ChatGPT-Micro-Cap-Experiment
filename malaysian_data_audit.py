#!/usr/bin/env python3
"""
Malaysian Stock Data Audit Script
Tests various data sources for KLSE (Bursa Malaysia) stock data accessibility
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# Sample Malaysian stocks to test (various market caps and sectors)
test_stocks = {
    # Large caps
    "MAYBANK": "1155.KL",     # Malayan Banking
    "CIMB": "1023.KL",        # CIMB Group
    "GENTING": "3182.KL",     # Genting Berhad
    
    # Mid caps  
    "HARTALEGA": "5168.KL",   # Hartalega Holdings
    "TOPGLOV": "7113.KL",     # Top Glove
    
    # Small/micro caps
    "KFIMA": "6491.KL",       # Kumpulan Fima
    "JAKS": "4723.KL",        # JAKS Resources
    "NETX": "0090.KL",        # NetX Holdings
}

def test_yfinance_coverage():
    """Test yfinance data quality for Malaysian stocks"""
    print("=" * 60)
    print("TESTING YFINANCE DATA COVERAGE")
    print("=" * 60)
    
    results = []
    
    for name, ticker in test_stocks.items():
        print(f"\nTesting {name} ({ticker})...")
        
        try:
            # Get stock info
            stock = yf.Ticker(ticker)
            
            # Test recent price data
            hist = stock.history(period="5d")
            info = stock.info
            
            result = {
                "name": name,
                "ticker": ticker,
                "has_recent_data": not hist.empty,
                "data_points": len(hist),
                "latest_price": hist['Close'][-1] if not hist.empty else None,
                "currency": info.get('currency', 'Unknown'),
                "market_cap": info.get('marketCap', 'Unknown'),
                "sector": info.get('sector', 'Unknown'),
                "status": "✅ Good" if not hist.empty and len(hist) >= 3 else "❌ Poor"
            }
            
            print(f"  Latest Price: {result['latest_price']:.2f} {result['currency']}" if result['latest_price'] else "  No price data")
            print(f"  Data Points (5d): {result['data_points']}")
            print(f"  Market Cap: {result['market_cap']}")
            print(f"  Status: {result['status']}")
            
        except Exception as e:
            result = {
                "name": name,
                "ticker": ticker,
                "has_recent_data": False,
                "error": str(e),
                "status": "❌ Error"
            }
            print(f"  Error: {e}")
        
        results.append(result)
        time.sleep(0.5)  # Be nice to the API
    
    return results

def test_investing_com_scraping():
    """Test if we can scrape data from investing.com"""
    print("\n" + "=" * 60)
    print("TESTING INVESTING.COM ACCESSIBILITY")
    print("=" * 60)
    
    try:
        # Test basic accessibility to investing.com Malaysia page
        url = "https://www.investing.com/equities/malaysia"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ Investing.com Malaysia page accessible")
            print(f"   Response size: {len(response.content)} bytes")
            
            # Check if we can find stock data patterns
            content = response.text.lower()
            if 'maybank' in content or 'cimb' in content:
                print("✅ Found Malaysian stock references in content")
            else:
                print("⚠️  No obvious Malaysian stock references found")
                
        else:
            print(f"❌ HTTP {response.status_code} - Cannot access investing.com")
            
    except Exception as e:
        print(f"❌ Error accessing investing.com: {e}")

def test_alternative_apis():
    """Test other potential data sources"""
    print("\n" + "=" * 60)
    print("TESTING ALTERNATIVE DATA SOURCES")
    print("=" * 60)
    
    # Test Alpha Vantage (if they have Malaysian data)
    print("Alpha Vantage API:")
    print("  📝 Requires API key - would need manual testing")
    print("  📝 Check if they support .KL suffix stocks")
    
    # Test Yahoo Finance direct API
    print("\nYahoo Finance Direct API:")
    try:
        # Test direct Yahoo Finance API call
        ticker = "1155.KL"  # Maybank
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and data['chart']['result']:
                print("✅ Yahoo Finance direct API accessible for Malaysian stocks")
                price_data = data['chart']['result'][0]
                if 'meta' in price_data:
                    current_price = price_data['meta'].get('regularMarketPrice', 'N/A')
                    currency = price_data['meta'].get('currency', 'N/A')
                    print(f"   Sample: {ticker} = {current_price} {currency}")
            else:
                print("❌ No data in Yahoo Finance API response")
        else:
            print(f"❌ Yahoo Finance API returned {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing Yahoo Finance API: {e}")

def generate_report(yf_results):
    """Generate summary report"""
    print("\n" + "=" * 60)
    print("DATA AUDIT SUMMARY REPORT")
    print("=" * 60)
    
    # YFinance summary
    good_stocks = [r for r in yf_results if r.get('has_recent_data', False)]
    total_stocks = len(yf_results)
    
    print(f"\nYFinance Coverage:")
    print(f"  Stocks with data: {len(good_stocks)}/{total_stocks} ({len(good_stocks)/total_stocks*100:.1f}%)")
    
    if good_stocks:
        print(f"  ✅ Working stocks:")
        for stock in good_stocks:
            price = stock.get('latest_price', 'N/A')
            currency = stock.get('currency', 'Unknown')
            print(f"     {stock['name']} ({stock['ticker']}): {price:.2f} {currency}" if isinstance(price, (int, float)) else f"     {stock['name']} ({stock['ticker']}): {price} {currency}")
    
    bad_stocks = [r for r in yf_results if not r.get('has_recent_data', False)]
    if bad_stocks:
        print(f"  ❌ Problematic stocks:")
        for stock in bad_stocks:
            print(f"     {stock['name']} ({stock['ticker']})")
    
    # Recommendations
    print(f"\n📋 RECOMMENDATIONS:")
    
    if len(good_stocks) >= total_stocks * 0.7:
        print("✅ YFinance appears viable for Malaysian stocks")
        print("   - Proceed with YFinance as primary data source")
        print("   - Consider backup sources for any missing stocks")
    elif len(good_stocks) >= total_stocks * 0.3:
        print("⚠️  YFinance has mixed coverage")
        print("   - Use YFinance for covered stocks")
        print("   - Implement alternative sources for missing data")
    else:
        print("❌ YFinance coverage insufficient")
        print("   - Consider web scraping or paid API services")
        print("   - Test local Malaysian financial data providers")
    
    print(f"\n🔧 NEXT STEPS:")
    print("1. Test additional Malaysian tickers beyond this sample")
    print("2. Evaluate data latency (real-time vs 15-20 min delay)")
    print("3. Test data reliability during Malaysian market hours")
    print("4. Consider backup data sources for redundancy")

if __name__ == "__main__":
    print("Starting Malaysian Stock Data Audit...")
    print(f"Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    yf_results = test_yfinance_coverage()
    test_investing_com_scraping()
    test_alternative_apis()
    
    # Generate final report
    generate_report(yf_results)
    
    print(f"\n✅ Audit Complete!")
