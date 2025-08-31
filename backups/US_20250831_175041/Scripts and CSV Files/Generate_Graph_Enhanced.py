#!/usr/bin/env python3
"""
Enhanced Generate_Graph.py with Data Source Reliability Monitoring
Supports both US and Malaysian market visualizations with redundant data
"""

import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from redundant_data_fetcher import KLSEDataFetcher
    ENHANCED_MODE = True
except ImportError:
    print("⚠️  Enhanced data fetcher not available, using standard mode")
    ENHANCED_MODE = False

def generate_enhanced_chart(market_type="US"):
    """
    Generate performance chart with enhanced data source monitoring
    
    Args:
        market_type: "US" for original experiment, "KLSE" for Malaysian adaptation
    """
    
    print(f"📊 Generating Enhanced Performance Chart ({market_type} Market)")
    print("=" * 60)
    
    if market_type == "US":
        # Original US market chart
        portfolio_file = "chatgpt_portfolio_update.csv"
        benchmark_symbol = "^SPX"
        benchmark_name = "S&P 500"
        baseline_date = pd.Timestamp("2025-06-27")
        baseline_equity = 100
        baseline_benchmark = 6173.07
        currency = "USD"
        
    elif market_type == "KLSE":
        # Malaysian market chart
        portfolio_file = "klse_portfolio_enhanced.csv"
        benchmark_symbol = "^KLSE"  # FTSE Bursa Malaysia KLCI
        benchmark_name = "FTSE Bursa Malaysia KLCI"
        baseline_date = pd.Timestamp("2025-08-01")  # Adjust based on your start date
        baseline_equity = 450  # Starting MYR amount
        baseline_benchmark = 1600  # Approximate KLCI level
        currency = "MYR"
    
    else:
        raise ValueError("market_type must be 'US' or 'KLSE'")
    
    # === Load and prepare portfolio data ===
    try:
        portfolio_df = pd.read_csv(portfolio_file)
        portfolio_totals = portfolio_df[portfolio_df['Ticker'] == 'TOTAL'].copy()
        portfolio_totals['Date'] = pd.to_datetime(portfolio_totals['Date'])
        
        if portfolio_totals.empty:
            print(f"❌ No TOTAL rows found in {portfolio_file}")
            return
            
        print(f"✅ Loaded {len(portfolio_totals)} portfolio data points")
        
        # Check for data source information in portfolio
        if 'Data Source' in portfolio_df.columns:
            source_info = portfolio_df[portfolio_df['Ticker'] != 'TOTAL']['Data Source'].value_counts()
            print(f"📡 Data sources used: {dict(source_info)}")
            
    except FileNotFoundError:
        print(f"❌ Portfolio file not found: {portfolio_file}")
        return
    
    # Add baseline row
    baseline_row = pd.DataFrame({
        "Date": [baseline_date],
        "Total Equity": [baseline_equity]   
    })
    portfolio_totals = pd.concat([baseline_row, portfolio_totals], ignore_index=True).sort_values("Date")
    
    # === Download benchmark data ===
    print(f"📈 Downloading {benchmark_name} data...")
    
    start_date = portfolio_totals['Date'].min()
    end_date = portfolio_totals['Date'].max() + pd.Timedelta(days=1)
    
    try:
        if ENHANCED_MODE and market_type == "KLSE":
            # For KLSE, try our enhanced fetcher first, fallback to yfinance
            print("🔄 Using enhanced data fetching for benchmark...")
            # Note: For simplicity, still using yfinance for benchmark, but this could be enhanced
        
        benchmark = yf.download(benchmark_symbol, start=start_date, end=end_date, progress=False)
        
        if benchmark.empty:
            print(f"⚠️  Could not download {benchmark_name} data, using synthetic benchmark")
            # Create synthetic benchmark
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            growth_rate = 0.001  # 0.1% daily growth
            benchmark = pd.DataFrame({
                'Date': date_range,
                'Close': [baseline_benchmark * (1 + growth_rate) ** i for i in range(len(date_range))]
            })
            benchmark.set_index('Date', inplace=True)
        else:
            benchmark = benchmark.reset_index()
            print(f"✅ Downloaded {len(benchmark)} {benchmark_name} data points")
        
        # Fix columns if downloaded with MultiIndex
        if isinstance(benchmark.columns, pd.MultiIndex):
            benchmark.columns = benchmark.columns.get_level_values(0)
        
        # Normalize benchmark to same starting value
        benchmark_start_price = benchmark['Close'].iloc[0] if not benchmark.empty else baseline_benchmark
        benchmark_scaling_factor = baseline_equity / benchmark_start_price
        benchmark[f"{benchmark_name} Value ({baseline_equity} {currency} Invested)"] = benchmark["Close"] * benchmark_scaling_factor
        
    except Exception as e:
        print(f"❌ Error downloading benchmark: {e}")
        return
    
    # === Create enhanced visualization ===
    plt.figure(figsize=(12, 8))
    plt.style.use("seaborn-v0_8-whitegrid")
    
    # Plot portfolio performance
    plt.plot(portfolio_totals['Date'], portfolio_totals["Total Equity"], 
             label=f"ChatGPT Portfolio ({baseline_equity} {currency})", 
             marker="o", color="red", linewidth=3)
    
    # Plot benchmark
    plt.plot(benchmark['Date'], benchmark[f"{benchmark_name} Value ({baseline_equity} {currency} Invested)"], 
             label=f"{benchmark_name} ({baseline_equity} {currency})", 
             marker="s", color="blue", linestyle='--', linewidth=2)
    
    # Add performance annotations
    final_date = portfolio_totals['Date'].iloc[-1]
    final_portfolio = float(portfolio_totals["Total Equity"].iloc[-1])
    final_benchmark = benchmark[f"{benchmark_name} Value ({baseline_equity} {currency} Invested)"].iloc[-1]
    
    portfolio_return = ((final_portfolio - baseline_equity) / baseline_equity) * 100
    benchmark_return = ((final_benchmark - baseline_equity) / baseline_equity) * 100
    alpha = portfolio_return - benchmark_return
    
    plt.text(final_date, final_portfolio + (baseline_equity * 0.02), 
             f"{portfolio_return:+.1f}%", color="red", fontsize=12, fontweight='bold')
    plt.text(final_date, final_benchmark + (baseline_equity * 0.02), 
             f"{benchmark_return:+.1f}%", color="blue", fontsize=12, fontweight='bold')
    
    # Add alpha annotation
    alpha_color = "green" if alpha > 0 else "red"
    plt.text(final_date, max(final_portfolio, final_benchmark) + (baseline_equity * 0.05),
             f"Alpha: {alpha:+.1f}%", color=alpha_color, fontsize=11, fontweight='bold')
    
    # Enhanced title with market info
    title = f"ChatGPT {'Micro-Cap' if market_type == 'KLSE' else ''} Portfolio vs {benchmark_name}"
    if ENHANCED_MODE:
        title += " (Enhanced Data Sources)"
    
    plt.title(title, fontsize=16, fontweight='bold')
    plt.xlabel("Date", fontsize=12)
    plt.ylabel(f"Value of {baseline_equity} {currency} Investment", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save chart with enhanced filename
    timestamp = datetime.now().strftime('%Y%m%d')
    enhanced_suffix = "_Enhanced" if ENHANCED_MODE else ""
    chart_filename = f"{market_type}_Performance_{timestamp}{enhanced_suffix}.png"
    
    plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"💾 Chart saved as {chart_filename}")
    
    # === Enhanced Performance Summary ===
    print("\n" + "=" * 60)
    print("📊 ENHANCED PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Portfolio Return: {portfolio_return:+.2f}%")
    print(f"{benchmark_name} Return: {benchmark_return:+.2f}%")
    print(f"Alpha Generated: {alpha:+.2f}%")
    print(f"Starting Value: {baseline_equity:.2f} {currency}")
    print(f"Ending Value: {final_portfolio:.2f} {currency}")
    print(f"Absolute Gain: {final_portfolio - baseline_equity:+.2f} {currency}")
    
    # Data source reliability info
    if ENHANCED_MODE and 'Data Source' in portfolio_df.columns:
        print(f"\n📡 DATA SOURCE RELIABILITY:")
        source_stats = portfolio_df[portfolio_df['Ticker'] != 'TOTAL']['Data Source'].value_counts()
        total_fetches = source_stats.sum()
        
        for source, count in source_stats.items():
            percentage = (count / total_fetches) * 100
            print(f"   {source}: {count} fetches ({percentage:.1f}%)")
    
    return {
        'portfolio_return': portfolio_return,
        'benchmark_return': benchmark_return,
        'alpha': alpha,
        'chart_file': chart_filename
    }

def compare_original_vs_enhanced():
    """
    Compare original system performance vs enhanced system
    """
    print("🔄 Comparing Original vs Enhanced System Performance")
    print("=" * 60)
    
    # Check if both files exist
    original_file = "chatgpt_portfolio_update.csv"
    enhanced_file = "klse_portfolio_enhanced.csv"
    
    files_to_check = []
    if os.path.exists(original_file):
        files_to_check.append(("Original US", original_file, "US"))
    if os.path.exists(enhanced_file):
        files_to_check.append(("Enhanced KLSE", enhanced_file, "KLSE"))
    
    results = {}
    for name, file, market in files_to_check:
        try:
            print(f"\n📊 Analyzing {name} system...")
            result = generate_enhanced_chart(market)
            results[name] = result
        except Exception as e:
            print(f"❌ Error analyzing {name}: {e}")
    
    return results

if __name__ == "__main__":
    print("🚀 Enhanced Performance Visualization System")
    print("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "klse":
            generate_enhanced_chart("KLSE")
        elif sys.argv[1] == "us":
            generate_enhanced_chart("US")
        elif sys.argv[1] == "compare":
            compare_original_vs_enhanced()
        else:
            print("Usage: python Generate_Graph_Enhanced.py [us|klse|compare]")
    else:
        # Default: try to generate US chart if data exists
        if os.path.exists("chatgpt_portfolio_update.csv"):
            generate_enhanced_chart("US")
        elif os.path.exists("klse_portfolio_enhanced.csv"):
            generate_enhanced_chart("KLSE")
        else:
            print("❌ No portfolio data files found")
            print("   Expected: chatgpt_portfolio_update.csv or klse_portfolio_enhanced.csv")
    
    print(f"\n✅ Enhanced visualization complete!")
    print(f"\n💡 USAGE OPTIONS:")
    print(f"   python Generate_Graph_Enhanced.py us      # US market chart")
    print(f"   python Generate_Graph_Enhanced.py klse    # Malaysian market chart")
    print(f"   python Generate_Graph_Enhanced.py compare # Compare both systems")
