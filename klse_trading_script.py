#!/usr/bin/env python3
"""
KLSE Trading Script - Malaysian adaptation of ChatGPT Micro-Cap Experiment
Processes Malaysian micro-cap portfolio with board lot constraints
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import numpy as np

# Malaysian market parameters
MYR_TO_USD = 4.5  # Approximate exchange rate
BOARD_LOT_SIZE = 100  # Standard Malaysian board lot
MICROCAP_THRESHOLD_MYR = 300_000_000  # 300M MYR threshold

def process_klse_portfolio(portfolio, starting_cash_myr):
    """
    Process KLSE portfolio with Malaysian market adaptations
    """
    today = datetime.now().strftime("%Y-%m-%d")
    results = []
    total_value = 0
    total_pnl = 0
    cash = starting_cash_myr
    
    print(f"Processing KLSE portfolio for {today}")
    print("=" * 50)
    
    for _, stock in portfolio.iterrows():
        ticker = stock["ticker"]
        shares = int(stock["shares"])
        cost = stock["buy_price"]
        stop = stock["stop_loss"]
        
        # Fetch Malaysian stock data
        data = yf.Ticker(ticker).history(period="1d")

        if data.empty:
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
            # Use 3 decimal places for Malaysian sen precision
            price = round(data["Close"].iloc[-1], 3)
            value = round(price * shares, 2)
            pnl = round((price - cost) * shares, 2)

            if price <= stop:
                action = "SELL - Stop Loss Triggered"
                cash += value
                log_klse_sell(ticker, shares, price, cost, pnl, action)
                print(f"🚨 STOP LOSS: {ticker} sold at {price:.3f} MYR")
            else:
                action = "HOLD"
                total_value += value
                total_pnl += pnl
                print(f"✅ HOLDING: {ticker} @ {price:.3f} MYR (PnL: {pnl:+.2f} MYR)")

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

    # Add TOTAL row with MYR values
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
    
    print("=" * 50)
    print(f"📊 Portfolio Summary:")
    print(f"   Total Value: {total_value:.2f} MYR")
    print(f"   Cash: {cash:.2f} MYR")
    print(f"   Total Equity: {total_value + cash:.2f} MYR")
    print(f"   Total PnL: {total_pnl:+.2f} MYR")

    # Save to CSV
    file = f"Scripts and CSV Files/klse_portfolio_update.csv"
    df = pd.DataFrame(results)

    if os.path.exists(file):
        existing = pd.read_csv(file)
        existing = existing[existing["Date"] != today]  # Remove today's rows
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(file, index=False)
    print(f"💾 Portfolio saved to {file}")
    
    return df

def log_klse_sell(ticker, shares, price, cost, pnl, action):
    """Log Malaysian stock sales"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Sold": shares,
        "Sell Price": price,
        "Cost Basis": cost,
        "PnL": pnl,
        "Action": action,
        "Currency": "MYR"
    }
    
    log_file = f"Scripts and CSV Files/klse_trade_log.csv"
    log_df = pd.DataFrame([log])
    
    if os.path.exists(log_file):
        existing = pd.read_csv(log_file)
        log_df = pd.concat([existing, log_df], ignore_index=True)
    
    log_df.to_csv(log_file, index=False)
    print(f"📝 Trade logged to {log_file}")

def calculate_board_lot_shares(cash_available, price_per_share, lot_size=BOARD_LOT_SIZE):
    """
    Calculate maximum shares buyable in board lots
    Malaysian stocks typically trade in multiples of 100 shares
    """
    max_lots = int(cash_available / (price_per_share * lot_size))
    total_shares = max_lots * lot_size
    total_cost = total_shares * price_per_share
    
    return total_shares, total_cost

def get_klse_microcaps():
    """
    Return a list of confirmed Malaysian micro-cap stocks for testing
    """
    microcaps = {
        "JAKS": {
            "ticker": "4723.KL",
            "name": "JAKS Resources Berhad",
            "market_cap_myr": 236_000_000,
            "sector": "Industrial"
        },
        "NETX": {
            "ticker": "0090.KL", 
            "name": "NetX Holdings Berhad",
            "market_cap_myr": 193_000_000,
            "sector": "Technology"
        },
        "FINTEC": {
            "ticker": "0176.KL",
            "name": "Fintec Global Berhad", 
            "market_cap_myr": 187_000_000,
            "sector": "Technology"
        },
        "SUNSURIA": {
            "ticker": "5305.KL",
            "name": "Sunsuria Berhad",
            "market_cap_myr": 248_000_000,
            "sector": "Property"
        }
    }
    
    return microcaps

def demo_klse_trading():
    """
    Demonstrate KLSE trading with sample portfolio
    """
    print("🇲🇾 KLSE Micro-Cap Trading Demo")
    print("=" * 60)
    
    # Sample portfolio with Malaysian micro-caps
    sample_portfolio = pd.DataFrame({
        'ticker': ['4723.KL', '0090.KL', '0176.KL'],
        'shares': [1000, 500, 800],  # Board lots
        'buy_price': [0.095, 0.290, 0.215],  # Entry prices in MYR
        'stop_loss': [0.080, 0.250, 0.180]   # Stop loss levels
    })
    
    print("📋 Sample Portfolio:")
    print(sample_portfolio)
    print()
    
    # Process the portfolio
    starting_cash = 100.0  # 100 MYR starting cash
    result = process_klse_portfolio(sample_portfolio, starting_cash)
    
    return result

if __name__ == "__main__":
    print("🚀 Starting KLSE Trading Script...")
    
    # Run demo
    demo_result = demo_klse_trading()
    
    print("\n✅ KLSE Trading Script Demo Complete!")
    print("\n📈 Available Malaysian Micro-Caps:")
    
    microcaps = get_klse_microcaps()
    for code, details in microcaps.items():
        market_cap_usd = details['market_cap_myr'] / MYR_TO_USD / 1_000_000
        print(f"   {code} ({details['ticker']}): ${market_cap_usd:.1f}M USD - {details['sector']}")
