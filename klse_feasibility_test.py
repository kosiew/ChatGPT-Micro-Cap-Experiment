#!/usr/bin/env python3
"""
KLSE Micro-Cap Trading Feasibility Test
Tests core trading functionality adapted for Malaysian stocks
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

# Malaysian micro-cap stocks (< 300M MYR market cap ≈ $67M USD)
microcap_stocks = {
    "JAKS": "4723.KL",        # JAKS Resources - 236M MYR
    "NETX": "0090.KL",        # NetX Holdings - 193M MYR
    "GENETEC": "0104.KL",     # Genetec Technology - Usually small cap
    "FINTEC": "0176.KL",      # Fintec Global - Technology
    "HIAP": "5072.KL",        # Hiap Teck Venture - Industrial
    "SUNSURIA": "5305.KL",    # Sunsuria Berhad - Property
    "KGROUP": "7204.KL",      # K-One Technology - Technology
}

def test_microcap_data_quality():
    """Test data quality specifically for micro-cap stocks"""
    print("=" * 60)
    print("TESTING MICRO-CAP STOCK DATA QUALITY")
    print("=" * 60)
    
    results = []
    
    for name, ticker in microcap_stocks.items():
        print(f"\nTesting {name} ({ticker})...")
        
        try:
            stock = yf.Ticker(ticker)
            
            # Test different time periods
            hist_1d = stock.history(period="1d")
            hist_5d = stock.history(period="5d") 
            hist_1m = stock.history(period="1mo")
            
            info = stock.info
            
            # Calculate market cap in USD (assuming ~4.5 MYR = 1 USD)
            market_cap_myr = info.get('marketCap', 0)
            market_cap_usd = market_cap_myr / 4.5 if market_cap_myr else 0
            
            result = {
                "name": name,
                "ticker": ticker,
                "current_price": hist_1d['Close'].iloc[-1] if not hist_1d.empty else None,
                "currency": info.get('currency', 'Unknown'),
                "market_cap_myr": market_cap_myr,
                "market_cap_usd": market_cap_usd,
                "is_microcap": market_cap_usd < 67_000_000,  # < $67M USD
                "data_1d": len(hist_1d),
                "data_5d": len(hist_5d),
                "data_1m": len(hist_1m),
                "sector": info.get('sector', 'Unknown'),
                "avg_volume": info.get('averageVolume', 'Unknown'),
                "status": "✅ Viable" if not hist_1d.empty and market_cap_usd < 67_000_000 else "❌ Not suitable"
            }
            
            print(f"  Price: {result['current_price']:.3f} MYR" if result['current_price'] else "  No price data")
            print(f"  Market Cap: {market_cap_usd/1_000_000:.1f}M USD ({market_cap_myr/1_000_000:.0f}M MYR)")
            print(f"  Micro-cap: {'✅ Yes' if result['is_microcap'] else '❌ No'}")
            print(f"  Data availability: 1d={result['data_1d']}, 5d={result['data_5d']}, 1m={result['data_1m']}")
            print(f"  Avg Volume: {result['avg_volume']}")
            print(f"  Status: {result['status']}")
            
        except Exception as e:
            result = {
                "name": name,
                "ticker": ticker,
                "error": str(e),
                "status": "❌ Error"
            }
            print(f"  Error: {e}")
        
        results.append(result)
        time.sleep(0.5)
    
    return results

def test_portfolio_processing_logic():
    """Test if we can adapt the core portfolio processing for Malaysian stocks"""
    print("\n" + "=" * 60)
    print("TESTING PORTFOLIO PROCESSING ADAPTATION")
    print("=" * 60)
    
    # Sample portfolio with Malaysian stocks
    sample_portfolio = pd.DataFrame({
        'ticker': ['4723.KL', '0090.KL'],
        'shares': [1000, 500],  # Board lots
        'buy_price': [0.10, 0.30],
        'stop_loss': [0.08, 0.25]
    })
    
    print("Sample Portfolio:")
    print(sample_portfolio)
    print(f"\nTesting portfolio processing...")
    
    total_value = 0
    total_pnl = 0
    
    for _, stock in sample_portfolio.iterrows():
        ticker = stock["ticker"]
        shares = int(stock["shares"])
        cost = stock["buy_price"]
        stop = stock["stop_loss"]
        
        try:
            data = yf.Ticker(ticker).history(period="1d")
            
            if not data.empty:
                price = round(data["Close"].iloc[-1], 3)  # 3 decimals for sen precision
                value = round(price * shares, 2)
                pnl = round((price - cost) * shares, 2)
                
                print(f"\n{ticker}:")
                print(f"  Current Price: {price:.3f} MYR")
                print(f"  Position Value: {value:.2f} MYR")
                print(f"  PnL: {pnl:+.2f} MYR")
                print(f"  Stop Loss: {'⚠️ TRIGGERED' if price <= stop else '✅ Safe'}")
                
                if price > stop:  # Only add to totals if not stopped out
                    total_value += value
                    total_pnl += pnl
                    
            else:
                print(f"\n{ticker}: ❌ No data available")
                
        except Exception as e:
            print(f"\n{ticker}: ❌ Error - {e}")
    
    print(f"\nPortfolio Summary:")
    print(f"  Total Value: {total_value:.2f} MYR")
    print(f"  Total PnL: {total_pnl:+.2f} MYR")
    print(f"  Return: {(total_pnl/100)*100:+.1f}%" if total_value > 0 else "  Return: N/A")

def test_market_hours_and_latency():
    """Test data latency during Malaysian market hours"""
    print("\n" + "=" * 60)
    print("TESTING MARKET HOURS & DATA LATENCY")
    print("=" * 60)
    
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} (Local)")
    
    # KLSE trading hours: 9:00 AM - 5:00 PM Malaysia Time (GMT+8)
    # Note: This is a simplified check - real implementation would need timezone handling
    
    print(f"\nKLSE Trading Hours: 9:00 AM - 5:00 PM (GMT+8)")
    print(f"Current status: Market analysis would require timezone conversion")
    
    # Test data freshness
    test_ticker = "4723.KL"  # JAKS
    stock = yf.Ticker(test_ticker)
    hist = stock.history(period="1d")
    
    if not hist.empty:
        latest_data_time = hist.index[-1]
        print(f"\nLatest data timestamp for {test_ticker}: {latest_data_time}")
        print(f"Data age: {now - latest_data_time.tz_localize(None)}")
    
def generate_klse_feasibility_report(microcap_results):
    """Generate final feasibility assessment"""
    print("\n" + "=" * 60)
    print("KLSE MICRO-CAP TRADING FEASIBILITY REPORT")
    print("=" * 60)
    
    viable_stocks = [r for r in microcap_results if r.get('status', '').startswith('✅')]
    total_tested = len(microcap_results)
    
    print(f"\nMicro-Cap Stock Analysis:")
    print(f"  Stocks tested: {total_tested}")
    print(f"  Viable micro-caps: {len(viable_stocks)}")
    print(f"  Success rate: {len(viable_stocks)/total_tested*100:.1f}%")
    
    if viable_stocks:
        print(f"\n✅ Confirmed Micro-Caps:")
        for stock in viable_stocks:
            if 'market_cap_usd' in stock:
                print(f"     {stock['name']} ({stock['ticker']}): ${stock['market_cap_usd']/1_000_000:.1f}M USD")
    
    print(f"\n🏛️ REGULATORY CONSIDERATIONS:")
    print("   - Bursa Malaysia board lot system (usually 100 shares minimum)")
    print("   - Different settlement cycle (T+2)")
    print("   - Malaysian ringgit (MYR) denomination")
    print("   - Potential foreign ownership restrictions")
    
    print(f"\n🔧 REQUIRED CODE MODIFICATIONS:")
    print("   1. Update share calculation for board lots")
    print("   2. Modify currency handling (MYR vs USD)")
    print("   3. Adjust market hours for GMT+8 timezone")
    print("   4. Update benchmark from S&P 500 to KLCI")
    print("   5. Modify micro-cap threshold (< 300M MYR)")
    
    print(f"\n🎯 OVERALL FEASIBILITY: {'✅ HIGHLY VIABLE' if len(viable_stocks) >= 3 else '⚠️ LIMITED OPTIONS' if len(viable_stocks) >= 1 else '❌ NOT RECOMMENDED'}")
    
    if len(viable_stocks) >= 3:
        print("     YFinance provides excellent coverage of Malaysian micro-caps")
        print("     Proceed with KLSE adaptation of the trading experiment")
    elif len(viable_stocks) >= 1:
        print("     Limited but workable micro-cap options available")
        print("     Consider expanding stock universe or relaxing market cap limits")
    else:
        print("     Insufficient micro-cap coverage for viable experiment")

if __name__ == "__main__":
    print("Starting KLSE Micro-Cap Trading Feasibility Test...")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run feasibility tests
    microcap_results = test_microcap_data_quality()
    test_portfolio_processing_logic()
    test_market_hours_and_latency()
    
    # Generate final assessment
    generate_klse_feasibility_report(microcap_results)
    
    print(f"\n✅ Feasibility Test Complete!")
