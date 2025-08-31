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
from rich.console import Console
from rich.table import Table
from rich import print as rich_print

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from klse_portfolio_manager import KLSEPortfolioManager

app = typer.Typer(help="🚀 KLSE Trading Engine")
console = Console()

class KLSETradingEngine:
    def __init__(self):
        self.portfolio_manager = KLSEPortfolioManager()
        logger.info("KLSE Trading Engine initialized")
    
    def run_daily_update(self):
        """Run daily portfolio update"""
        try:
            logger.info("Starting daily portfolio update...")
            self.portfolio_manager.update_portfolio()
            logger.info("✅ Daily update completed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Daily update failed: {e}")
            return False
    
    def get_portfolio_summary(self):
        """Get portfolio summary"""
        return self.portfolio_manager.get_portfolio_summary()

@app.command()
def summary():
    """📊 Display current portfolio summary"""
    try:
        engine = KLSETradingEngine()
        summary = engine.get_portfolio_summary()
        
        console.print("\n[bold blue]📊 KLSE Portfolio Summary[/bold blue]")
        console.print(f"💰 Total Equity: [green]{summary['total_equity']:,.2f} MYR[/green]")
        console.print(f"💵 Cash Balance: [yellow]{summary['cash_balance']:,.2f} MYR[/yellow]")
        console.print(f"📈 Total P&L: [{'green' if summary['total_pnl'] >= 0 else 'red'}]{summary['total_pnl']:+,.2f} MYR[/{'green' if summary['total_pnl'] >= 0 else 'red'}]")
        console.print(f"📊 Return: [{'green' if summary['total_return'] >= 0 else 'red'}]{summary['total_return']:+.2f}%[/{'green' if summary['total_return'] >= 0 else 'red'}]")
        
        if summary['positions']:
            console.print("\n[bold]📋 Current Positions:[/bold]")
            for pos in summary['positions']:
                pnl_symbol = "🟢" if pos['position_pnl'] >= 0 else "🔴"
                console.print(f"   {pnl_symbol} [bold]{pos['ticker']}[/bold]: {pos['shares']} shares")
                console.print(f"      Value: [green]{pos['position_value']:,.2f} MYR[/green]")
                console.print(f"      PnL: [{'green' if pos['position_pnl'] >= 0 else 'red'}]{pos['position_pnl']:+,.2f} MYR ({pos['position_return_pct']:+.2f}%)[/{'green' if pos['position_pnl'] >= 0 else 'red'}]")
    
        # Display failed tickers if any
        if 'failed_tickers' in summary and summary['failed_tickers']:
            console.print(f"\n[bold red]⚠️  Failed to Get Price Data ({len(summary['failed_tickers'])} tickers):[/bold red]")
            console.print("=" * 50)
            for failed in summary['failed_tickers']:
                console.print(f"   ❌ [bold]{failed['ticker']}[/bold] ({failed['company_name']})")
                console.print(f"      Shares: {failed['shares']}")
                console.print(f"      Cost Basis: {failed['avg_cost']:.3f} MYR")
                console.print(f"      Sector: {failed['sector']}")
                console.print(f"      Reason: {failed['reason']}")
                console.print()
            
            console.print("💡 Investigation needed for these tickers:")
            console.print("   • Check if companies are still listed")
            console.print("   • Verify ticker symbols are correct")
            console.print("   • Consider manual price updates or position removal")
            console.print()
    
    except Exception as e:
        console.print(f"[red]❌ Error getting portfolio summary: {e}[/red]")
        logger.error(f"Portfolio summary failed: {e}")

@app.command()
def update():
    """🔄 Run daily portfolio update"""
    """
    
    def __init__(self, alpha_vantage_key: str = None):
        self.alpha_vantage_key = alpha_vantage_key
        
        # Initialize portfolio manager
        if ENHANCED_AVAILABLE:
            self.portfolio_manager = KLSEPortfolioManager(
                starting_cash_myr=10000.0,  # 10K MYR starting capital
                alpha_vantage_key=alpha_vantage_key
            )
            self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
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
            ticker: Malaysian stock code (e.g., "1155" for Maybank)
            target_weight_pct: Target weight as percentage of portfolio
            stop_loss_pct: Stop loss percentage below cost basis
            company_name: Company name for records
            sector: Business sector
        """
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
        
        # Add the position
        success = self.portfolio_manager.add_stock(
            ticker=ticker,
            target_weight_pct=target_weight_pct,
            stop_loss_pct=stop_loss_pct,
            company_name=company_name,
            sector=sector
        )
        
        if success:
            logger.info(f"✅ Added new position: {ticker} ({target_weight_pct}% target weight)")
        else:
            logger.error(f"❌ Failed to add position: {ticker}")
        
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
    alpha_vantage_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for data")
):
    """Execute daily portfolio processing and updates"""
    print("🇲🇾 Starting KLSE daily processing...")
    
    # Initialize trading engine
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    # Execute daily processing
    result = engine.execute_daily_processing()
    
    if result['status'] == 'success':
        print("✅ Daily processing completed successfully")
        
        summary = result['summary']
        print(f"📊 Total Equity: {summary['total_equity']:,.2f} MYR")
        print(f"📈 Return: {summary['total_return_pct']:+.2f}%")
        print(f"🏢 Positions: {summary['positions']}")
        
        if summary['stops_triggered'] > 0:
            print(f"🚨 Stop Losses: {summary['stops_triggered']}")
    else:
        print(f"❌ Daily processing failed: {result}")


@app.command("report")
def generate_report(
    alpha_vantage_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for data")
):
    """Generate and display comprehensive daily trading report"""
    print("📋 Generating KLSE trading report...")
    
    # Initialize trading engine
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    # Generate and display report
    report = engine.generate_daily_report()
    print(report)


@app.command("add")
def add_position(
    ticker: str = typer.Argument(..., help="Malaysian stock ticker (e.g., '1155' for Maybank)"),
    weight: float = typer.Argument(..., help="Target weight as percentage (e.g., 20.0 for 20%)"),
    stop_loss: float = typer.Option(15.0, help="Stop loss percentage below cost basis"),
    company_name: str = typer.Option("", help="Company name for records"),
    sector: str = typer.Option("", help="Business sector"),
    alpha_vantage_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for data")
):
    """Add a new stock position to the portfolio"""
    print(f"🎯 Adding new position: {ticker} ({weight}% target weight)")
    
    # Initialize trading engine
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    # Add the position
    success = engine.add_new_position(
        ticker=ticker,
        target_weight_pct=weight,
        stop_loss_pct=stop_loss,
        company_name=company_name,
        sector=sector
    )
    
    if success:
        print(f"✅ Successfully added {ticker} to portfolio")
        # Show updated summary
        summary = engine.get_trading_summary()
        print(f"📊 Available slots: {summary['available_position_slots']}/{summary['max_positions']}")
    else:
        print(f"❌ Failed to add {ticker}")


@app.command("remove")
def remove_position(
    ticker: str = typer.Argument(..., help="Stock ticker to remove"),
    reason: str = typer.Option("Manual sale", help="Reason for removing position"),
    alpha_vantage_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for data")
):
    """Remove (sell) a stock position from the portfolio"""
    print(f"🔄 Removing position: {ticker}")
    
    # Initialize trading engine
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    # Remove the position
    success = engine.remove_position(ticker=ticker, reason=reason)
    
    if success:
        print(f"✅ Successfully removed {ticker} from portfolio")
        # Show updated summary
        summary = engine.get_trading_summary()
        print(f"📊 Active positions: {summary['total_positions']}/{summary['max_positions']}")
    else:
        print(f"❌ Failed to remove {ticker}")


@app.command("summary")
def portfolio_summary(
    alpha_vantage_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for data")
):
    """Show current portfolio summary and trading capacity"""
    print("📊 KLSE Portfolio Summary")
    
    # Initialize trading engine
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    # Get comprehensive summary
    summary = engine.get_trading_summary()
    
    # Display summary
    print(f"\n� Portfolio Value: {summary['total_equity']:,.2f} MYR")
    print(f"💵 Cash Balance: {summary['cash_balance']:,.2f} MYR")
    print(f"📈 Total Return: {summary['total_return_pct']:+.2f}%")
    print(f"🏢 Active Positions: {summary['total_positions']}/{summary['max_positions']}")
    print(f"📊 Available Slots: {summary['available_position_slots']}")
    print(f"➕ Can Add Positions: {'✅ Yes' if summary['can_add_positions'] else '❌ No'}")
    
    if summary['positions']:
        print("\n� Current Positions:")
        for pos in summary['positions']:
            pnl_symbol = "🟢" if pos['position_pnl'] >= 0 else "🔴"
            print(f"   {pnl_symbol} {pos['ticker']}: {pos['shares']} shares")
            print(f"      Value: {pos['position_value']:,.2f} MYR")
            print(f"      PnL: {pos['position_pnl']:+,.2f} MYR ({pos['position_return_pct']:+.2f}%)")


@app.command("demo")
def demo_mode(
    alpha_vantage_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for data")
):
    """Run demo mode with sample positions"""
    print("🎯 KLSE Trading Engine Demo")
    print("=" * 40)
    
    # Initialize trading engine
    engine = KLSETradingEngine(alpha_vantage_key=alpha_vantage_key)
    
    # Add sample positions
    sample_stocks = [
        {"ticker": "4723", "name": "JAKS Resources", "weight": 30.0, "sector": "Industrial"},
        {"ticker": "0090", "name": "NetX Holdings", "weight": 25.0, "sector": "Technology"},
        {"ticker": "0176", "name": "Fintec Global", "weight": 20.0, "sector": "Technology"},
    ]
    
    print("\n🏗️ Adding sample positions...")
    for stock in sample_stocks:
        success = engine.add_new_position(
            ticker=stock["ticker"],
            target_weight_pct=stock["weight"],
            company_name=stock["name"],
            sector=stock["sector"]
        )
        
        if success:
            print(f"✅ Added {stock['name']} ({stock['ticker']}.KL)")
        else:
            print(f"❌ Failed to add {stock['name']}")
    
    print("\n📊 Processing daily update...")
    result = engine.execute_daily_processing()
    
    print("\n📋 Final Report:")
    print(engine.generate_daily_report())


if __name__ == "__main__":
    app()
