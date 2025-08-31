#!/usr/bin/env python3
"""
Enhanced KLSE Trading Script with Redundant Data Sources
Production-ready Malaysian stock trading with fallback data sources
"""

import pandas as pd
from datetime import datetime
import os
import logging
from redundant_data_fetcher import KLSEDataFetcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedKLSETrading:
    """
    Enhanced KLSE trading system with redundant data sources and robust error handling
    """
    
    def __init__(self, alpha_vantage_key: str = None):
        self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
        self.portfolio_file = "Scripts and CSV Files/klse_portfolio_enhanced.csv"
        self.trade_log_file = "Scripts and CSV Files/klse_trade_log_enhanced.csv"
        
        # Ensure directories exist
        os.makedirs("Scripts and CSV Files", exist_ok=True)
    
    def process_portfolio_enhanced(self, portfolio: pd.DataFrame, starting_cash_myr: float) -> pd.DataFrame:
        """
        Process KLSE portfolio with enhanced error handling and data validation
        """
        today = datetime.now().strftime("%Y-%m-%d")
        results = []
        total_value = 0
        total_pnl = 0
        cash = starting_cash_myr
        
        logger.info(f"Processing KLSE portfolio for {today} - {len(portfolio)} positions")
        print(f"🇲🇾 Processing KLSE Portfolio - {today}")
        print("=" * 60)
        
        # Get all stock codes for batch processing
        stock_codes = [ticker.replace('.KL', '') for ticker in portfolio['ticker']]
        
        # Fetch all data at once for efficiency
        print("📊 Fetching market data...")
        stock_data = self.data_fetcher.get_multiple_stocks(stock_codes)
        
        # Process each position
        for _, stock in portfolio.iterrows():
            ticker = stock["ticker"]
            shares = int(stock["shares"])
            cost = stock["buy_price"]
            stop = stock["stop_loss"]
            
            # Extract stock code (remove .KL suffix if present)
            stock_code = ticker.replace('.KL', '')
            
            # Get price data from our fetched batch
            price_data = stock_data.get(stock_code)
            
            if not price_data:
                logger.warning(f"No data available for {ticker}")
                print(f"❌ {ticker}: No data available")
                
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
                    "Data Source": "N/A",
                    "Cash Balance": "",
                    "Total Equity": ""
                }
            else:
                # Extract price with proper precision for Malaysian sen
                price = price_data['price']
                value = round(price * shares, 2)
                pnl = round((price - cost) * shares, 2)
                data_source = price_data.get('source', 'unknown')
                
                # Check stop loss
                if price <= stop:
                    action = "SELL - Stop Loss Triggered"
                    cash += value
                    self._log_enhanced_sell(ticker, shares, price, cost, pnl, action, data_source)
                    print(f"🚨 STOP LOSS: {ticker} sold at {price:.3f} MYR (via {data_source})")
                else:
                    action = "HOLD"
                    total_value += value
                    total_pnl += pnl
                    print(f"✅ HOLDING: {ticker} @ {price:.3f} MYR | PnL: {pnl:+.2f} MYR (via {data_source})")

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
                    "Data Source": data_source,
                    "Cash Balance": "",
                    "Total Equity": ""
                }

            results.append(row)

        # Add enhanced TOTAL row with data source statistics
        data_source_performance = self.data_fetcher.get_source_performance()
        performance_summary = ", ".join([f"{k}: {v['success_rate']}%" for k, v in data_source_performance.items()])
        
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
            "Data Source": performance_summary,
            "Cash Balance": round(cash, 2),
            "Total Equity": round(total_value + cash, 2)
        }
        results.append(total_row)
        
        # Display summary
        print("=" * 60)
        print(f"📊 Portfolio Summary:")
        print(f"   Total Value: {total_value:.2f} MYR")
        print(f"   Cash: {cash:.2f} MYR")
        print(f"   Total Equity: {total_value + cash:.2f} MYR")
        print(f"   Total PnL: {total_pnl:+.2f} MYR")
        print(f"   Data Sources: {performance_summary}")

        # Save to CSV with enhanced metadata
        df = pd.DataFrame(results)
        self._save_portfolio_data(df, today)
        
        return df
    
    def _log_enhanced_sell(self, ticker: str, shares: int, price: float, cost: float, 
                          pnl: float, action: str, data_source: str):
        """Log stock sales with enhanced metadata"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        log = {
            "Date": today,
            "Ticker": ticker,
            "Shares Sold": shares,
            "Sell Price": price,
            "Cost Basis": cost,
            "PnL": pnl,
            "Action": action,
            "Data Source": data_source,
            "Currency": "MYR",
            "Timestamp": datetime.now().isoformat()
        }
        
        self._save_trade_log(log)
        logger.info(f"Trade logged: {ticker} sold {shares} shares at {price:.3f} MYR")
    
    def _save_portfolio_data(self, df: pd.DataFrame, today: str):
        """Save portfolio data with deduplication"""
        if os.path.exists(self.portfolio_file):
            existing = pd.read_csv(self.portfolio_file)
            existing = existing[existing["Date"] != today]  # Remove today's rows
            df = pd.concat([existing, df], ignore_index=True)

        df.to_csv(self.portfolio_file, index=False)
        logger.info(f"Portfolio saved to {self.portfolio_file}")
        print(f"💾 Portfolio saved to {self.portfolio_file}")
    
    def _save_trade_log(self, log: dict):
        """Save trade log with enhanced metadata"""
        log_df = pd.DataFrame([log])
        
        if os.path.exists(self.trade_log_file):
            existing = pd.read_csv(self.trade_log_file)
            log_df = pd.concat([existing, log_df], ignore_index=True)
        
        log_df.to_csv(self.trade_log_file, index=False)
        logger.info(f"Trade logged to {self.trade_log_file}")
    
    def validate_portfolio_data(self, portfolio: pd.DataFrame) -> bool:
        """Validate portfolio data structure and constraints"""
        required_columns = ['ticker', 'shares', 'buy_price', 'stop_loss']
        
        for col in required_columns:
            if col not in portfolio.columns:
                logger.error(f"Missing required column: {col}")
                return False
        
        # Validate board lots (Malaysian stocks typically trade in multiples of 100)
        for _, stock in portfolio.iterrows():
            shares = stock['shares']
            if shares % 100 != 0:
                logger.warning(f"Warning: {stock['ticker']} has {shares} shares (not a board lot)")
        
        return True
    
    def get_system_health(self) -> dict:
        """Get overall system health and data source status"""
        performance = self.data_fetcher.get_source_performance()
        
        # Calculate overall health score
        total_attempts = sum(stats['attempts'] for stats in performance.values())
        total_successes = sum(stats['successes'] for stats in performance.values())
        
        overall_success_rate = (total_successes / total_attempts * 100) if total_attempts > 0 else 0
        
        health_status = "EXCELLENT" if overall_success_rate >= 95 else \
                       "GOOD" if overall_success_rate >= 80 else \
                       "FAIR" if overall_success_rate >= 60 else "POOR"
        
        return {
            'overall_success_rate': round(overall_success_rate, 1),
            'health_status': health_status,
            'data_sources': performance,
            'total_attempts': total_attempts,
            'total_successes': total_successes
        }

def demo_enhanced_trading():
    """Demonstrate the enhanced KLSE trading system"""
    print("🚀 Enhanced KLSE Trading System Demo")
    print("=" * 60)
    
    # Initialize enhanced trading system
    trading_system = EnhancedKLSETrading()
    
    # Create sample portfolio with Malaysian micro-caps
    sample_portfolio = pd.DataFrame({
        'ticker': ['1155.KL', '4723.KL', '0090.KL', '0176.KL'],
        'shares': [100, 1000, 500, 800],  # Board lots
        'buy_price': [9.95, 0.095, 0.290, 0.215],
        'stop_loss': [8.50, 0.080, 0.250, 0.180]
    })
    
    print("📋 Sample Portfolio:")
    print(sample_portfolio)
    print()
    
    # Validate portfolio
    if not trading_system.validate_portfolio_data(sample_portfolio):
        print("❌ Portfolio validation failed")
        return
    
    print("✅ Portfolio validation passed")
    print()
    
    # Process portfolio with enhanced system
    starting_cash = 1000.0  # 1000 MYR
    result = trading_system.process_portfolio_enhanced(sample_portfolio, starting_cash)
    
    # Show system health
    print(f"\n🏥 System Health Report:")
    health = trading_system.get_system_health()
    print(f"   Overall Status: {health['health_status']}")
    print(f"   Success Rate: {health['overall_success_rate']}%")
    print(f"   Total Requests: {health['total_successes']}/{health['total_attempts']}")
    
    print(f"\n📈 Data Source Performance:")
    for source, stats in health['data_sources'].items():
        print(f"   {source}: {stats['success_rate']}% ({stats['successes']}/{stats['attempts']})")
    
    return result

if __name__ == "__main__":
    # Run enhanced trading demo
    demo_result = demo_enhanced_trading()
    
    print(f"\n✅ Enhanced KLSE Trading Demo Complete!")
    print(f"\n🎯 PRODUCTION FEATURES:")
    print(f"   ✅ Redundant data sources with automatic failover")
    print(f"   ✅ Enhanced error handling and logging")
    print(f"   ✅ Data source performance monitoring")
    print(f"   ✅ Portfolio validation and board lot checking")
    print(f"   ✅ Comprehensive trade logging with metadata")
    print(f"   ✅ System health monitoring")
    
    print(f"\n🔧 INTEGRATION READY:")
    print(f"   - Replace existing trading script with this enhanced version")
    print(f"   - Add Alpha Vantage API key for additional redundancy")
    print(f"   - Monitor data source performance in production")
    print(f"   - Set up alerts for system health degradation")
