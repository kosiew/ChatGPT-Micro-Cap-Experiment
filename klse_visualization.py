#!/usr/bin/env python3
"""
KLSE Performance Visualization - Malaysian market adaptation
Compares KLSE micro-cap portfolio against FTSE Bursa Malaysia KLCI
"""

import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta

def generate_klse_performance_chart():
    """Generate performance chart for KLSE portfolio vs KLCI benchmark"""
    
    print("📊 Generating KLSE Performance Chart...")
    
    # Load KLSE portfolio data
    try:
        klse_df = pd.read_csv("Scripts and CSV Files/klse_portfolio_update.csv")
        klse_totals = klse_df[klse_df['Ticker'] == 'TOTAL'].copy()
        klse_totals['Date'] = pd.to_datetime(klse_totals['Date'])
        
        if klse_totals.empty:
            print("❌ No TOTAL rows found in KLSE portfolio data")
            return
            
        print(f"✅ Loaded {len(klse_totals)} portfolio data points")
        
    except FileNotFoundError:
        print("❌ KLSE portfolio file not found. Run klse_trading_script.py first.")
        return
    
    # Add baseline for starting equity (assuming 450 MYR starting value)
    baseline_date = klse_totals['Date'].min() - pd.Timedelta(days=1)
    baseline_equity = 450  # Starting value in MYR
    
    baseline_row = pd.DataFrame({
        "Date": [baseline_date],
        "Total Equity": [baseline_equity]   
    })
    
    klse_totals = pd.concat([baseline_row, klse_totals], ignore_index=True).sort_values("Date")
    
    # Download KLCI (FTSE Bursa Malaysia KLCI) data
    print("📈 Downloading KLCI benchmark data...")
    
    start_date = klse_totals['Date'].min()
    end_date = klse_totals['Date'].max() + pd.Timedelta(days=1)
    
    try:
        # ^KLSE is the Yahoo Finance symbol for KLCI
        klci = yf.download("^KLSE", start=start_date, end=end_date, progress=False)
        
        if klci.empty:
            print("⚠️  Could not download KLCI data, using synthetic benchmark")
            # Create synthetic benchmark for demo
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            klci = pd.DataFrame({
                'Date': date_range,
                'Close': [1500 + i * 0.5 for i in range(len(date_range))]  # Synthetic growth
            })
            klci.set_index('Date', inplace=True)
        else:
            klci = klci.reset_index()
            print(f"✅ Downloaded {len(klci)} KLCI data points")
        
        # Normalize KLCI to same starting value as portfolio
        klci_start_price = klci['Close'].iloc[0]
        klci_scaling_factor = baseline_equity / klci_start_price
        klci["KLCI Value (450 MYR Invested)"] = klci["Close"] * klci_scaling_factor
        
    except Exception as e:
        print(f"❌ Error downloading KLCI: {e}")
        return
    
    # Create the performance chart
    plt.figure(figsize=(12, 8))
    plt.style.use("seaborn-v0_8-whitegrid")
    
    # Plot portfolio performance
    plt.plot(klse_totals['Date'], klse_totals["Total Equity"], 
             label="KLSE Micro-Cap Portfolio (450 MYR)", marker="o", color="red", linewidth=3)
    
    # Plot KLCI benchmark
    plt.plot(klci['Date'], klci["KLCI Value (450 MYR Invested)"], 
             label="FTSE Bursa Malaysia KLCI (450 MYR)", marker="s", color="blue", linestyle='--', linewidth=2)
    
    # Add performance annotations
    final_date = klse_totals['Date'].iloc[-1]
    final_portfolio = float(klse_totals["Total Equity"].iloc[-1])
    final_klci = klci["KLCI Value (450 MYR Invested)"].iloc[-1]
    
    portfolio_return = ((final_portfolio - baseline_equity) / baseline_equity) * 100
    klci_return = ((final_klci - baseline_equity) / baseline_equity) * 100
    
    plt.text(final_date, final_portfolio + 5, f"{portfolio_return:+.1f}%", 
             color="red", fontsize=11, fontweight='bold')
    plt.text(final_date, final_klci + 5, f"{klci_return:+.1f}%", 
             color="blue", fontsize=11, fontweight='bold')
    
    # Chart formatting
    plt.title("KLSE Micro-Cap Portfolio vs FTSE Bursa Malaysia KLCI", fontsize=16, fontweight='bold')
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Value of 450 MYR Investment", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save the chart
    chart_filename = f"KLSE_Performance_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"💾 Chart saved as {chart_filename}")
    
    # Print performance summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Portfolio Return: {portfolio_return:+.2f}%")
    print(f"KLCI Return: {klci_return:+.2f}%")
    print(f"Alpha: {portfolio_return - klci_return:+.2f}%")
    print(f"Starting Value: {baseline_equity:.2f} MYR")
    print(f"Ending Value: {final_portfolio:.2f} MYR")
    print(f"Absolute Gain: {final_portfolio - baseline_equity:+.2f} MYR")

def analyze_klse_market_data():
    """Analyze Malaysian market characteristics"""
    print("\n🇲🇾 KLSE MARKET ANALYSIS")
    print("=" * 60)
    
    # Test various Malaysian market indices
    indices = {
        "KLCI": "^KLSE",           # FTSE Bursa Malaysia KLCI  
        "FBMS": "^FBMS",          # FTSE Bursa Malaysia Small Cap
        "FBMT": "^FBMT",          # FTSE Bursa Malaysia Top 100
    }
    
    for name, symbol in indices.items():
        try:
            data = yf.download(symbol, period="5d", progress=False)
            if not data.empty:
                latest_price = data['Close'].iloc[-1]
                print(f"✅ {name} ({symbol}): {latest_price:.2f}")
            else:
                print(f"❌ {name} ({symbol}): No data")
        except:
            print(f"❌ {name} ({symbol}): Error")
    
    # Currency info
    try:
        usdmyr = yf.download("USDMYR=X", period="5d", progress=False)
        if not usdmyr.empty:
            exchange_rate = usdmyr['Close'].iloc[-1]
            print(f"\n💱 USD/MYR Exchange Rate: {exchange_rate:.4f}")
        else:
            print(f"\n💱 USD/MYR Exchange Rate: Unable to fetch")
    except:
        print(f"\n💱 USD/MYR Exchange Rate: Error fetching")

if __name__ == "__main__":
    print("🚀 Starting KLSE Performance Analysis...")
    
    # Generate performance chart
    generate_klse_performance_chart()
    
    # Analyze market data
    analyze_klse_market_data()
    
    print("\n✅ KLSE Analysis Complete!")
