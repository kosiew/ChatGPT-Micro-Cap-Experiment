#!/usr/bin/env python3
"""
KLSE Trading Script
Malaysian stock trading engine for ChatGPT micro-cap experiment
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import os
import sys
import logging
from typing import Dict, List, Optional
import typer
from typing_extensions import Annotated
import yfinance as yf

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our portfolio manager and data fetcher
try:
    from KLSE_System.klse_portfolio_manager import KLSEPortfolioManager
    from KLSE_System.i3investor_scraper import I3InvestorScraper
    from redundant_data_fetcher import KLSEDataFetcher
    ENHANCED_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("   Falling back to basic functionality")
    ENHANCED_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Typer app
app = typer.Typer(
    name="klse-trading",
    help="KLSE Trading Engine - Malaysian stock trading system for micro-cap experiments",
    add_completion=False
)

class KLSETradingEngine:
    """
    Malaysian stock trading engine for automated portfolio management
    """
    
    def __init__(self, alpha_vantage_key: str = None):
        self.alpha_vantage_key = alpha_vantage_key
        
        # Initialize portfolio manager
        if ENHANCED_AVAILABLE:
            self.portfolio_manager = KLSEPortfolioManager(
                starting_cash_myr=0.0,  # Started with existing holdings, no cash
                alpha_vantage_key=alpha_vantage_key
            )
            self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
            self.i3_scraper = I3InvestorScraper()
        else:
            logger.error("Portfolio manager not available - please check imports")
            sys.exit(1)
        
        # Malaysian trading constraints
        self.TRADING_CURRENCY = "MYR"
        self.MIN_BOARD_LOT = 100
        self.MAX_POSITIONS = 10  # Maximum active positions
        self.MIN_CASH_RESERVE_MYR = 500  # Keep minimum cash reserve
        
        # File paths
        self.daily_update_file = "KLSE_System/klse_daily_updates.csv"
        self.performance_file = "KLSE_System/klse_performance_log.csv"
        
        # Ensure directory exists
        os.makedirs("KLSE_System", exist_ok=True)
        
        logger.info("KLSE Trading Engine initialized")
    
    def check_market_eligibility(self) -> Dict[str, any]:
        """Check if market is eligible for trading"""
        market_status = self.portfolio_manager.get_market_status()
        
        # Allow trading even when market is closed for testing/demo
        # Real implementation might restrict this
        eligibility = {
            'can_trade': True,  # Always allow for demo purposes
            'market_open': market_status['is_open'],
            'reason': 'Market status checked',
            'market_info': market_status
        }
        
        if not market_status['is_open']:
            eligibility['reason'] = f"Market closed. Next open: {market_status['next_open']}"
            logger.info(f"⏰ {eligibility['reason']}")
        
        return eligibility
    
    def execute_daily_processing(self) -> Dict[str, any]:
        """Execute daily portfolio processing"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"🇲🇾 Starting KLSE daily processing for {today}")
        
        # Check market eligibility
        eligibility = self.check_market_eligibility()
        
        # Process portfolio updates (stop-losses, valuations)
        update_result = self.portfolio_manager.process_daily_update()
        
        if update_result['status'] != 'success':
            logger.error(f"Portfolio update failed: {update_result}")
            return {'status': 'error', 'message': 'Portfolio update failed'}
        
        summary = update_result['summary']
        
        # Log daily performance
        daily_record = {
            'date': today,
            'total_equity_myr': summary['total_equity'],
            'cash_balance_myr': summary['cash_balance'],
            'total_stock_value_myr': summary['total_stock_value'],
            'total_return_pct': summary['total_return_pct'],
            'positions_count': summary['positions'],
            'stops_triggered': summary['stops_triggered'],
            'market_open': eligibility['market_open']
        }
        
        # Save daily record
        self._save_daily_record(daily_record)
        
        # Log performance
        self._log_performance(daily_record, update_result.get('positions', []))
        
        logger.info(f"✅ Daily processing complete: {summary['total_equity']:.2f} MYR "
                   f"({summary['total_return_pct']:+.2f}%)")
        
        return {
            'status': 'success',
            'date': today,
            'summary': summary,
            'positions': update_result.get('positions', []),
            'stops_triggered': update_result.get('stops_triggered', []),
            'market_info': eligibility['market_info']
        }
    
    def get_yfinance_ticker(self, ticker: str) -> str:
        """
        Convert Malaysian stock ticker to yfinance format
        
        Args:
            ticker: Stock name or ticker (e.g., 'MBMR', 'AXIATA')
            
        Returns:
            Formatted ticker for yfinance (e.g., '5983.KL', '6888.KL')
        """
        # If already in .KL format, return as is
        if ticker.endswith('.KL'):
            return ticker
            
        # If it's already a numeric code, add .KL
        if ticker.isdigit():
            return f"{ticker}.KL"
            
        # Try to get the ticker code from i3investor
        logger.info(f"🔍 Looking up ticker code for {ticker}")
        ticker_code = self.i3_scraper.get_ticker_code(ticker)
        
        if ticker_code:
            logger.info(f"✅ Found ticker: {ticker} -> {ticker_code}")
            return ticker_code
        else:
            # Fallback: assume it's already correct and add .KL
            logger.warning(f"⚠️  Could not find ticker code for {ticker}, using {ticker}.KL")
            return f"{ticker}.KL"
    
    def _save_daily_record(self, record: Dict):
        """Save daily record to CSV"""
        df = pd.DataFrame([record])
        
        if os.path.exists(self.daily_update_file):
            existing = pd.read_csv(self.daily_update_file)
            # Check if today's record already exists
            if record['date'] not in existing['date'].values:
                df = pd.concat([existing, df], ignore_index=True)
            else:
                # Update existing record
                existing.loc[existing['date'] == record['date']] = record
                df = existing
        
        df.to_csv(self.daily_update_file, index=False)
    
    def _log_performance(self, daily_record: Dict, positions: List[Dict]):
        """Log detailed performance data"""
        performance_data = []
        
        # Portfolio-level record
        performance_data.append({
            'date': daily_record['date'],
            'type': 'PORTFOLIO',
            'ticker': 'TOTAL',
            'value_myr': daily_record['total_equity_myr'],
            'return_pct': daily_record['total_return_pct'],
            'positions_count': daily_record['positions_count']
        })
        
        # Individual position records
        for position in positions:
            if position['action'] == 'HOLD':
                performance_data.append({
                    'date': daily_record['date'],
                    'type': 'POSITION',
                    'ticker': position['ticker'],
                    'value_myr': position['position_value'],
                    'return_pct': ((position['current_price'] - position['cost_basis']) / position['cost_basis']) * 100,
                    'data_source': position.get('data_source', 'unknown')
                })
        
        # Save to performance log
        perf_df = pd.DataFrame(performance_data)
        
        if os.path.exists(self.performance_file):
            existing_perf = pd.read_csv(self.performance_file)
            # Remove existing records for today
            existing_perf = existing_perf[existing_perf['date'] != daily_record['date']]
            perf_df = pd.concat([existing_perf, perf_df], ignore_index=True)
        
        perf_df.to_csv(self.performance_file, index=False)
    
    def add_new_position(self, ticker: str, target_weight_pct: float, 
                        stop_loss_pct: float = 15.0, company_name: str = "", 
                        sector: str = "") -> bool:
        """
        Add new position to portfolio
        
        Args:
            ticker: Malaysian stock code or name (e.g., "MBMR", "1155", "AXIATA")
            target_weight_pct: Target weight as percentage of portfolio
            stop_loss_pct: Stop loss percentage below cost basis
            company_name: Company name for records
            sector: Business sector
        """
        # Convert ticker to yfinance format
        yf_ticker = self.get_yfinance_ticker(ticker)
        logger.info(f"🔄 Converting ticker: {ticker} -> {yf_ticker}")
        
        # Check if we can add more positions
        current_positions = len(self.portfolio_manager.portfolio)
        
        if current_positions >= self.MAX_POSITIONS:
            logger.warning(f"Maximum positions ({self.MAX_POSITIONS}) reached")
            return False
        
        # Check market eligibility
        eligibility = self.check_market_eligibility()
        if not eligibility['can_trade']:
            logger.warning(f"Cannot trade: {eligibility['reason']}")
            return False
        
        # Check cash availability
        if self.portfolio_manager.current_cash_myr < self.MIN_CASH_RESERVE_MYR:
            logger.warning(f"Insufficient cash (reserve: {self.MIN_CASH_RESERVE_MYR} MYR)")
            return False
        
        # Add the position using the converted ticker
        success = self.portfolio_manager.add_stock(
            ticker=yf_ticker,  # Use converted ticker
            target_weight_pct=target_weight_pct,
            stop_loss_pct=stop_loss_pct,
            company_name=company_name,
            sector=sector
        )
        
        if success:
            logger.info(f"✅ Added new position: {ticker} -> {yf_ticker} ({target_weight_pct}% target weight)")
        else:
            logger.error(f"❌ Failed to add position: {ticker} -> {yf_ticker}")
        
        return success
    
    def remove_position(self, ticker: str, reason: str = "Manual sale") -> bool:
        """
        Manually remove a position (sell all shares)
        
        Args:
            ticker: Stock ticker to sell
            reason: Reason for sale
        """
        # Find position in portfolio
        position_mask = self.portfolio_manager.portfolio['ticker'] == ticker
        
        if not position_mask.any():
            logger.error(f"Position {ticker} not found in portfolio")
            return False
        
        position = self.portfolio_manager.portfolio[position_mask].iloc[0]
        shares = position['shares']
        
        # Get current price
        stock_data = self.portfolio_manager._get_stock_data(ticker)
        if not stock_data:
            logger.error(f"Cannot get current price for {ticker}")
            return False
        
        current_price = stock_data['price']
        sale_value = current_price * shares
        
        # Add cash from sale
        self.portfolio_manager.current_cash_myr += sale_value
        
        # Log the trade
        self.portfolio_manager._log_trade(
            "SELL_MANUAL", ticker, shares, current_price, sale_value,
            stock_data.get('source', 'unknown')
        )
        
        # Remove from portfolio
        self.portfolio_manager.portfolio = self.portfolio_manager.portfolio[~position_mask]
        
        # Save portfolio
        self.portfolio_manager._save_portfolio()
        
        logger.info(f"✅ Sold {shares} shares of {ticker} at {current_price:.3f} MYR "
                   f"(Total: {sale_value:.2f} MYR) - {reason}")
        
        return True
    
    def get_trading_summary(self) -> Dict[str, any]:
        """Get comprehensive trading summary"""
        portfolio_summary = self.portfolio_manager.get_portfolio_summary()
        
        # Add trading-specific metrics
        trading_summary = {
            **portfolio_summary,
            'max_positions': self.MAX_POSITIONS,
            'available_position_slots': self.MAX_POSITIONS - portfolio_summary['total_positions'],
            'min_cash_reserve_myr': self.MIN_CASH_RESERVE_MYR,
            'can_add_positions': (
                portfolio_summary['total_positions'] < self.MAX_POSITIONS and
                portfolio_summary['cash_balance'] > self.MIN_CASH_RESERVE_MYR
            )
        }
        
        return trading_summary
    
    def generate_daily_report(self) -> str:
        """Generate daily trading report"""
        summary = self.get_trading_summary()
        market_status = summary['market_status']
        
        report = []
        report.append("🇲🇾 KLSE DAILY TRADING REPORT")
        report.append("=" * 50)
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT+8")
        report.append(f"Market Status: {'🟢 OPEN' if market_status['is_open'] else '🔴 CLOSED'}")
        report.append("")
        
        # Portfolio Overview
        report.append("📊 PORTFOLIO OVERVIEW")
        report.append("-" * 30)
        report.append(f"Total Equity: {summary['total_equity']:,.2f} MYR")
        report.append(f"Cash Balance: {summary['cash_balance']:,.2f} MYR")
        report.append(f"Stock Value: {summary['total_stock_value']:,.2f} MYR")
        report.append(f"Total Return: {summary['total_return_pct']:+.2f}%")
        report.append(f"Active Positions: {summary['total_positions']}/{self.MAX_POSITIONS}")
        report.append("")
        
        # Position Details
        if summary['positions']:
            report.append("📋 POSITION DETAILS")
            report.append("-" * 30)
            for pos in summary['positions']:
                pnl_symbol = "🟢" if pos['position_pnl'] >= 0 else "🔴"
                report.append(f"{pnl_symbol} {pos['ticker']}: {pos['shares']} shares")
                report.append(f"   Price: {pos['current_price']:.3f} MYR (Cost: {pos['avg_cost']:.3f})")
                report.append(f"   Value: {pos['position_value']:,.2f} MYR")
                report.append(f"   PnL: {pos['position_pnl']:+,.2f} MYR ({pos['position_return_pct']:+.2f}%)")
                report.append(f"   Stop Loss: {pos['stop_loss']:.3f} MYR")
                report.append("")
        else:
            report.append("📋 No active positions")
            report.append("")
        
        # Trading Capacity
        report.append("⚙️ TRADING CAPACITY")
        report.append("-" * 30)
        report.append(f"Available Slots: {summary['available_position_slots']}")
        report.append(f"Can Add Positions: {'✅ Yes' if summary['can_add_positions'] else '❌ No'}")
        report.append(f"Min Cash Reserve: {self.MIN_CASH_RESERVE_MYR} MYR")
        
        return "\n".join(report)

@app.command("daily")
def daily_processing(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Execute daily portfolio processing"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    result = engine.execute_daily_processing()
    
    if result['status'] == 'success':
        typer.echo("✅ Daily processing completed successfully")
        
        summary = result['summary']
        typer.echo(f"📊 Total Equity: {summary['total_equity']:,.2f} MYR")
        typer.echo(f"📈 Return: {summary['total_return_pct']:+.2f}%")
        typer.echo(f"🏢 Positions: {summary['positions']}")
        
        if summary['stops_triggered'] > 0:
            typer.echo(f"🚨 Stop Losses: {summary['stops_triggered']}")
    else:
        typer.echo(f"❌ Daily processing failed: {result}", err=True)
        raise typer.Exit(1)

@app.command("report")
def generate_report(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Generate and display daily trading report"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    report = engine.generate_daily_report()
    typer.echo(report)

@app.command("demo")
def demo_mode(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Demo mode - add sample positions and run processing"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    typer.echo("🎯 KLSE Trading Engine Demo")
    typer.echo("=" * 40)
    
    # Add sample positions
    sample_stocks = [
        {"ticker": "4723", "name": "JAKS Resources", "weight": 30.0, "sector": "Industrial"},
        {"ticker": "0090", "name": "NetX Holdings", "weight": 25.0, "sector": "Technology"},
        {"ticker": "0176", "name": "Fintec Global", "weight": 20.0, "sector": "Technology"},
    ]
    
    typer.echo("\n🏗️ Adding sample positions...")
    for stock in sample_stocks:
        success = engine.add_new_position(
            ticker=stock["ticker"],
            target_weight_pct=stock["weight"],
            company_name=stock["name"],
            sector=stock["sector"]
        )
        
        if success:
            typer.echo(f"✅ Added {stock['name']} ({stock['ticker']}.KL)")
        else:
            typer.echo(f"❌ Failed to add {stock['name']}")
    
    typer.echo("\n📊 Processing daily update...")
    result = engine.execute_daily_processing()
    
    typer.echo("\n� Final Report:")
    typer.echo(engine.generate_daily_report())

@app.command("add")
def add_position(
    ticker: Annotated[str, typer.Argument(help="Stock ticker (e.g., 1155 for Maybank)")],
    target_weight: Annotated[float, typer.Argument(help="Target weight as percentage")],
    stop_loss: Annotated[float, typer.Option("--stop-loss", "-s", help="Stop loss percentage")] = 15.0,
    company_name: Annotated[str, typer.Option("--name", "-n", help="Company name")] = "",
    sector: Annotated[str, typer.Option("--sector", help="Business sector")] = "",
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Add a new position to the portfolio"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    success = engine.add_new_position(
        ticker=ticker,
        target_weight_pct=target_weight,
        stop_loss_pct=stop_loss,
        company_name=company_name,
        sector=sector
    )
    
    if success:
        typer.echo(f"✅ Successfully added position: {ticker} ({target_weight}% target weight)")
    else:
        typer.echo(f"❌ Failed to add position: {ticker}", err=True)
        raise typer.Exit(1)

@app.command("remove")
def remove_position(
    ticker: Annotated[str, typer.Argument(help="Stock ticker to sell")],
    reason: Annotated[str, typer.Option("--reason", "-r", help="Reason for sale")] = "Manual sale",
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Remove a position from the portfolio (sell all shares)"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    success = engine.remove_position(ticker=ticker, reason=reason)
    
    if success:
        typer.echo(f"✅ Successfully removed position: {ticker}")
    else:
        typer.echo(f"❌ Failed to remove position: {ticker}", err=True)
        raise typer.Exit(1)

@app.command("summary")
def trading_summary(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Get comprehensive trading summary"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    summary = engine.get_trading_summary()
    
    typer.echo("📊 TRADING SUMMARY")
    typer.echo("=" * 30)
    typer.echo(f"Total Equity: {summary['total_equity']:,.2f} MYR")
    typer.echo(f"Cash Balance: {summary['cash_balance']:,.2f} MYR")
    typer.echo(f"Stock Value: {summary['total_stock_value']:,.2f} MYR")
    typer.echo(f"Total Return: {summary['total_return_pct']:+.2f}%")
    typer.echo(f"Positions: {summary['total_positions']}/{summary['max_positions']}")
    typer.echo(f"Available Slots: {summary['available_position_slots']}")
    typer.echo(f"Can Add Positions: {'✅ Yes' if summary['can_add_positions'] else '❌ No'}")

@app.command("ticker")
def test_ticker_conversion(
    tickers: str = typer.Argument(..., help="Comma-separated list of tickers to test (e.g., 'MBMR,AXIATA,1155')"),
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Test ticker conversion from Malaysian names to yfinance format"""
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    ticker_list = [t.strip() for t in tickers.split(',')]
    
    typer.echo("🔍 TICKER CONVERSION TEST")
    typer.echo("=" * 40)
    
    for ticker in ticker_list:
        typer.echo(f"\nTesting: {ticker}")
        try:
            yf_ticker = engine.get_yfinance_ticker(ticker)
            typer.echo(f"  Result: {ticker} -> {yf_ticker}")
            
            # Test if we can get price data
            typer.echo(f"  Testing price fetch...")
            try:
                stock = yf.Ticker(yf_ticker)
                info = stock.history(period="1d")
                if not info.empty:
                    latest_price = info['Close'].iloc[-1]
                    typer.echo(f"  ✅ Price: {latest_price:.3f} MYR")
                else:
                    typer.echo(f"  ❌ No price data available")
            except Exception as e:
                typer.echo(f"  ❌ Price fetch failed: {str(e)}")
                
        except Exception as e:
            typer.echo(f"  ❌ Conversion failed: {str(e)}")

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()
