#!/usr/bin/env python3
"""
KLSE Visualization System
Generate performance charts comparing ChatGPT portfolio against Malaysian market indices
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import sys
import logging
from typing import Dict, List, Optional, Tuple
import argparse

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from redundant_data_fetcher import KLSEDataFetcher
    ENHANCED_DATA_AVAILABLE = True
except ImportError:
    print("⚠️  Enhanced data fetcher not available, using basic yfinance")
    ENHANCED_DATA_AVAILABLE = False

# Always import yfinance for benchmark data
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KLSEVisualizationEngine:
    """
    Malaysian stock market visualization and benchmarking system
    """
    
    def __init__(self, alpha_vantage_key: str = None):
        self.alpha_vantage_key = alpha_vantage_key
        
        # Initialize data fetcher
        if ENHANCED_DATA_AVAILABLE:
            self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
        else:
            self.data_fetcher = None
        
        # Malaysian benchmark indices
        self.BENCHMARKS = {
            '^KLSE': 'FTSE Bursa Malaysia KLCI',
            '^KLSECI': 'FTSE Bursa Malaysia EMAS',
            '^FBM70': 'FBM Mid 70',
            '^FBMSCAP': 'FBM Small Cap'  # Most relevant for micro-cap comparison
        }
        
        # File paths
        self.portfolio_file = "KLSE_System/klse_daily_updates.csv"
        self.performance_file = "KLSE_System/klse_performance_log.csv"
        self.benchmark_file = "KLSE_System/klse_benchmarks.csv"
        self.charts_dir = "KLSE_System/charts"
        
        # Create charts directory
        os.makedirs(self.charts_dir, exist_ok=True)
        
        # Chart styling
        plt.style.use('default')
        self.colors = {
            'portfolio': '#2E86AB',  # Blue for ChatGPT portfolio
            'klci': '#A23B72',       # Purple for KLCI
            'fbm_small': '#F18F01',  # Orange for FBM Small Cap
            'fbm_mid': '#C73E1D',    # Red for FBM Mid 70
            'emas': '#4A5D23'        # Green for EMAS
        }
        
        logger.info("KLSE Visualization Engine initialized")
    
    def _get_benchmark_data(self, ticker: str, start_date: str, end_date: str = None) -> Optional[pd.DataFrame]:
        """Get benchmark index data"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Use yfinance for index data (most reliable for Malaysian indices)
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"No data available for benchmark {ticker}")
                return None
            
            # Prepare DataFrame
            benchmark_data = hist['Close'].reset_index()
            benchmark_data.columns = ['date', 'close']
            benchmark_data['date'] = pd.to_datetime(benchmark_data['date']).dt.strftime('%Y-%m-%d')
            
            logger.info(f"Retrieved {len(benchmark_data)} days of data for {ticker}")
            return benchmark_data
            
        except Exception as e:
            logger.error(f"Error fetching benchmark data for {ticker}: {e}")
            return None
    
    def _normalize_to_base_value(self, data: pd.DataFrame, base_value: float = 10000.0) -> pd.DataFrame:
        """Normalize price series to start at base value (e.g., 10,000 MYR)"""
        if data.empty:
            return data
        
        # Calculate normalized values
        first_value = data.iloc[0]['close'] if 'close' in data.columns else data.iloc[0]['total_equity_myr']
        data_normalized = data.copy()
        
        if 'close' in data.columns:
            data_normalized['normalized'] = (data['close'] / first_value) * base_value
        elif 'total_equity_myr' in data.columns:
            data_normalized['normalized'] = (data['total_equity_myr'] / first_value) * base_value
        
        return data_normalized
    
    def update_benchmark_data(self, days_back: int = 30) -> bool:
        """Update benchmark data for recent period"""
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        all_benchmark_data = []
        
        for ticker, name in self.BENCHMARKS.items():
            logger.info(f"Updating benchmark data for {name} ({ticker})")
            
            benchmark_data = self._get_benchmark_data(ticker, start_date, end_date)
            
            if benchmark_data is not None:
                benchmark_data['ticker'] = ticker
                benchmark_data['name'] = name
                all_benchmark_data.append(benchmark_data)
        
        if all_benchmark_data:
            # Combine all benchmark data
            combined_data = pd.concat(all_benchmark_data, ignore_index=True)
            
            # Save to file
            combined_data.to_csv(self.benchmark_file, index=False)
            logger.info(f"Saved benchmark data for {len(self.BENCHMARKS)} indices")
            return True
        else:
            logger.error("No benchmark data retrieved")
            return False
    
    def load_portfolio_data(self) -> pd.DataFrame:
        """Load portfolio performance data"""
        if not os.path.exists(self.portfolio_file):
            logger.warning(f"Portfolio file not found: {self.portfolio_file}")
            return pd.DataFrame()
        
        portfolio_data = pd.read_csv(self.portfolio_file)
        portfolio_data['date'] = pd.to_datetime(portfolio_data['date']).dt.strftime('%Y-%m-%d')
        
        logger.info(f"Loaded {len(portfolio_data)} days of portfolio data")
        return portfolio_data
    
    def load_benchmark_data(self) -> pd.DataFrame:
        """Load benchmark data"""
        if not os.path.exists(self.benchmark_file):
            logger.warning(f"Benchmark file not found: {self.benchmark_file}")
            return pd.DataFrame()
        
        benchmark_data = pd.read_csv(self.benchmark_file)
        logger.info(f"Loaded benchmark data for analysis")
        return benchmark_data
    
    def create_performance_comparison_chart(self, save_path: str = None) -> str:
        """Create comprehensive performance comparison chart"""
        # Load data
        portfolio_data = self.load_portfolio_data()
        benchmark_data = self.load_benchmark_data()
        
        if portfolio_data.empty:
            logger.error("No portfolio data available for charting")
            return None
        
        # Update benchmarks if data is stale or missing
        if benchmark_data.empty or len(benchmark_data) < 10:
            logger.info("Updating benchmark data...")
            self.update_benchmark_data(days_back=60)
            benchmark_data = self.load_benchmark_data()
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle('🇲🇾 ChatGPT KLSE Portfolio vs Malaysian Market Indices', 
                    fontsize=16, fontweight='bold')
        
        # Normalize portfolio data
        portfolio_normalized = self._normalize_to_base_value(portfolio_data, 10000.0)
        portfolio_dates = pd.to_datetime(portfolio_normalized['date'])
        
        # Plot portfolio performance (top chart)
        ax1.plot(portfolio_dates, portfolio_normalized['normalized'], 
                color=self.colors['portfolio'], linewidth=2.5, 
                label='ChatGPT Portfolio', marker='o', markersize=4)
        
        # Add benchmark comparisons if available
        if not benchmark_data.empty:
            # Get date range for portfolio
            start_date = portfolio_dates.min().strftime('%Y-%m-%d')
            end_date = portfolio_dates.max().strftime('%Y-%m-%d')
            
            logger.info(f"Portfolio date range: {start_date} to {end_date}")
            
            for ticker, name in self.BENCHMARKS.items():
                ticker_data = benchmark_data[benchmark_data['ticker'] == ticker].copy()
                
                if not ticker_data.empty:
                    logger.info(f"Processing benchmark {ticker} ({name}): {len(ticker_data)} total days")
                    
                    # Filter to portfolio date range
                    ticker_data = ticker_data[
                        (ticker_data['date'] >= start_date) & 
                        (ticker_data['date'] <= end_date)
                    ]
                    
                    if not ticker_data.empty:
                        logger.info(f"  Filtered to {len(ticker_data)} days in portfolio range")
                        ticker_normalized = self._normalize_to_base_value(ticker_data, 10000.0)
                        ticker_dates = pd.to_datetime(ticker_normalized['date'])
                        
                        # Plot benchmark
                        color = self.colors.get(ticker.lower().replace('^', '').replace('klse', 'klci'), '#888888')
                        logger.info(f"  Plotting {ticker} with color {color}")
                        ax1.plot(ticker_dates, ticker_normalized['normalized'], 
                                color=color, linewidth=1.5, alpha=0.8,
                                label=name.replace('FTSE Bursa Malaysia ', ''))
                    else:
                        logger.warning(f"  No data for {ticker} in portfolio date range")
                else:
                    logger.warning(f"No data found for benchmark {ticker}")
        
        # Format top chart
        ax1.set_title('Performance Comparison (Normalized to 10,000 MYR)', fontsize=12)
        ax1.set_ylabel('Portfolio Value (MYR)', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        # Add value annotations
        if not portfolio_normalized.empty:
            final_value = portfolio_normalized['normalized'].iloc[-1]
            initial_value = portfolio_normalized['normalized'].iloc[0]
            total_return = ((final_value - initial_value) / initial_value) * 100
            
            ax1.annotate(f'Final: {final_value:,.0f} MYR\nReturn: {total_return:+.2f}%',
                        xy=(portfolio_dates.iloc[-1], final_value),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor=self.colors['portfolio'], alpha=0.7),
                        color='white', fontsize=9, fontweight='bold')
        
        # Daily returns chart (bottom)
        if len(portfolio_data) > 1:
            # Calculate actual daily returns (day-over-day percentage change)
            equity_values = portfolio_data['total_equity_myr'].values
            daily_returns = np.zeros(len(equity_values))
            
            for i in range(1, len(equity_values)):
                if equity_values[i-1] > 0:
                    daily_returns[i] = ((equity_values[i] - equity_values[i-1]) / equity_values[i-1]) * 100
            
            # Plot daily returns (skip first day since no previous day to compare)
            plot_dates = portfolio_dates[1:]
            plot_returns = daily_returns[1:]
            
            ax2.plot(plot_dates, plot_returns, 
                    color=self.colors['portfolio'], linewidth=2, 
                    label='Daily Return %', marker='o', markersize=3)
            
            # Add zero line
            ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            
            # Color positive/negative areas
            ax2.fill_between(plot_dates, plot_returns, 0, 
                           where=(plot_returns >= 0), color='green', alpha=0.3, interpolate=True)
            ax2.fill_between(plot_dates, plot_returns, 0, 
                           where=(plot_returns < 0), color='red', alpha=0.3, interpolate=True)
        
        # Format bottom chart
        ax2.set_title('Daily Portfolio Returns', fontsize=12)
        ax2.set_xlabel('Date', fontsize=10)
        ax2.set_ylabel('Return (%)', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        # Rotate x-axis labels
        for ax in [ax1, ax2]:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add summary statistics
        if not portfolio_data.empty:
            stats_text = self._generate_performance_stats(portfolio_data)
            fig.text(0.02, 0.02, stats_text, fontsize=8, 
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        
        # Save chart
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"{self.charts_dir}/klse_performance_{timestamp}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Performance chart saved to {save_path}")
        
        return save_path
    
    def _generate_performance_stats(self, portfolio_data: pd.DataFrame) -> str:
        """Generate performance statistics text"""
        if portfolio_data.empty:
            return "No data available"
        
        # Calculate statistics
        equity_values = portfolio_data['total_equity_myr'].values
        starting_equity = equity_values[0]
        current_equity = equity_values[-1]
        total_return = ((current_equity - starting_equity) / starting_equity) * 100
        
        max_equity = portfolio_data['total_equity_myr'].max()
        min_equity = portfolio_data['total_equity_myr'].min()
        max_drawdown = ((max_equity - min_equity) / max_equity) * 100 if max_equity > 0 else 0
        
        # Calculate actual daily returns for volatility and win rate
        if len(portfolio_data) > 1:
            daily_returns = np.zeros(len(equity_values))
            for i in range(1, len(equity_values)):
                if equity_values[i-1] > 0:
                    daily_returns[i] = ((equity_values[i] - equity_values[i-1]) / equity_values[i-1]) * 100
            
            # Volatility (std of daily returns, excluding first day)
            volatility = daily_returns[1:].std()
            
            # Win rate (days with positive returns, excluding first day)
            positive_days = np.sum(daily_returns[1:] > 0)
            total_trading_days = len(daily_returns) - 1
            win_rate = (positive_days / total_trading_days) * 100 if total_trading_days > 0 else 0
        else:
            volatility = 0
            positive_days = 0
            total_trading_days = 0
            win_rate = 0
        
        stats = [
            f"📊 PERFORMANCE STATISTICS",
            f"Current Value: {current_equity:,.2f} MYR",
            f"Total Return: {total_return:+.2f}%",
            f"Max Drawdown: {max_drawdown:.2f}%",
            f"Volatility: {volatility:.2f}%",
            f"Win Rate: {win_rate:.1f}% ({positive_days}/{total_trading_days} days)",
            f"Data Points: {len(portfolio_data)} days"
        ]
        
        return "\n".join(stats)
    
    def create_sector_allocation_chart(self, save_path: str = None) -> str:
        """Create sector allocation pie chart"""
        # Load detailed performance data
        if not os.path.exists(self.performance_file):
            logger.warning("No detailed performance data available for sector analysis")
            return None
        
        perf_data = pd.read_csv(self.performance_file)
        
        # Get latest position data
        latest_date = perf_data['date'].max()
        latest_positions = perf_data[
            (perf_data['date'] == latest_date) & 
            (perf_data['type'] == 'POSITION')
        ]
        
        if latest_positions.empty:
            logger.warning("No position data available for sector analysis")
            return None
        
        # Load portfolio file to get sector information
        portfolio_file = "KLSE_System/klse_portfolio.csv"
        if os.path.exists(portfolio_file):
            portfolio_df = pd.read_csv(portfolio_file)
            
            # Merge with sector information
            sector_data = []
            total_value = latest_positions['value_myr'].sum()
            
            for _, pos in latest_positions.iterrows():
                ticker = pos['ticker']
                value = pos['value_myr']
                
                # Find sector from portfolio
                portfolio_match = portfolio_df[portfolio_df['ticker'] == ticker]
                sector = portfolio_match['sector'].iloc[0] if not portfolio_match.empty else 'Unknown'
                
                sector_data.append({
                    'ticker': ticker,
                    'sector': sector,
                    'value': value,
                    'percentage': (value / total_value) * 100
                })
            
            sector_df = pd.DataFrame(sector_data)
            
            # Create pie chart
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
            fig.suptitle('🇲🇾 KLSE Portfolio Allocation Analysis', fontsize=16, fontweight='bold')
            
            # Sector allocation
            sector_summary = sector_df.groupby('sector')['percentage'].sum().sort_values(ascending=False)
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(sector_summary)))
            wedges, texts, autotexts = ax1.pie(sector_summary.values, labels=sector_summary.index, 
                                             autopct='%1.1f%%', colors=colors, startangle=90)
            
            ax1.set_title('Sector Allocation', fontsize=12)
            
            # Individual position allocation
            position_summary = sector_df.set_index('ticker')['percentage'].sort_values(ascending=False)
            
            colors2 = plt.cm.Pastel1(np.linspace(0, 1, len(position_summary)))
            wedges2, texts2, autotexts2 = ax2.pie(position_summary.values, labels=position_summary.index,
                                                 autopct='%1.1f%%', colors=colors2, startangle=90)
            
            ax2.set_title('Position Allocation', fontsize=12)
            
            # Add value information
            info_text = f"Total Portfolio Value: {total_value:,.2f} MYR\n"
            info_text += f"Number of Positions: {len(sector_df)}\n"
            info_text += f"Date: {latest_date}"
            
            fig.text(0.02, 0.02, info_text, fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
            
            plt.tight_layout()
            
            # Save chart
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"{self.charts_dir}/klse_allocation_{timestamp}.png"
            
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Allocation chart saved to {save_path}")
            
            return save_path
    
    def generate_comprehensive_report(self) -> Dict[str, str]:
        """Generate all visualization charts"""
        logger.info("Generating comprehensive KLSE visualization report")
        
        results = {}
        
        # Performance comparison chart
        try:
            perf_chart = self.create_performance_comparison_chart()
            if perf_chart:
                results['performance_chart'] = perf_chart
                logger.info("✅ Performance comparison chart generated")
        except Exception as e:
            logger.error(f"Error generating performance chart: {e}")
        
        # Sector allocation chart
        try:
            allocation_chart = self.create_sector_allocation_chart()
            if allocation_chart:
                results['allocation_chart'] = allocation_chart
                logger.info("✅ Sector allocation chart generated")
        except Exception as e:
            logger.error(f"Error generating allocation chart: {e}")
        
        return results

def main():
    """Main visualization script execution"""
    parser = argparse.ArgumentParser(description='KLSE Visualization Engine')
    parser.add_argument('--action', choices=['performance', 'allocation', 'benchmarks', 'all'], 
                       default='all', help='Chart type to generate')
    parser.add_argument('--alpha-vantage-key', help='Alpha Vantage API key')
    parser.add_argument('--update-benchmarks', action='store_true', 
                       help='Force update benchmark data')
    
    args = parser.parse_args()
    
    # Initialize visualization engine
    viz_engine = KLSEVisualizationEngine(alpha_vantage_key=args.alpha_vantage_key)
    
    if args.update_benchmarks:
        print("📈 Updating benchmark data...")
        viz_engine.update_benchmark_data(days_back=90)
    
    if args.action == 'performance':
        # Generate performance chart only
        chart_path = viz_engine.create_performance_comparison_chart()
        if chart_path:
            print(f"✅ Performance chart generated: {chart_path}")
        else:
            print("❌ Failed to generate performance chart")
    
    elif args.action == 'allocation':
        # Generate allocation chart only
        chart_path = viz_engine.create_sector_allocation_chart()
        if chart_path:
            print(f"✅ Allocation chart generated: {chart_path}")
        else:
            print("❌ Failed to generate allocation chart")
    
    elif args.action == 'benchmarks':
        # Update benchmarks only
        success = viz_engine.update_benchmark_data(days_back=90)
        if success:
            print("✅ Benchmark data updated successfully")
        else:
            print("❌ Failed to update benchmark data")
    
    elif args.action == 'all':
        # Generate comprehensive report
        print("🎯 Generating comprehensive KLSE visualization report")
        results = viz_engine.generate_comprehensive_report()
        
        print(f"\n📊 Generated {len(results)} charts:")
        for chart_type, path in results.items():
            print(f"   ✅ {chart_type}: {path}")
        
        if not results:
            print("❌ No charts generated - check data availability")

if __name__ == "__main__":
    main()
