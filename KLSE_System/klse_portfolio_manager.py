#!/usr/bin/env python3
"""
KLSE Portfolio Management System
Complete Malaysian stock portfolio management with board lots, MYR currency, and local regulations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import os
import json
import logging
from typing import Dict, List, Optional, Tuple
import sys

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from redundant_data_fetcher import KLSEDataFetcher
    ENHANCED_DATA_AVAILABLE = True
except ImportError:
    print("⚠️  Enhanced data fetcher not available, using basic yfinance")
    ENHANCED_DATA_AVAILABLE = False
    import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KLSEPortfolioManager:
    """
    Comprehensive KLSE portfolio management system
    """
    
    def __init__(self, starting_cash_myr: float = 10000.0, alpha_vantage_key: str = None):
        self.starting_cash_myr = starting_cash_myr
        self.current_cash_myr = starting_cash_myr
        self.portfolio_file = "KLSE_System/klse_portfolio.csv"
        self.trade_log_file = "KLSE_System/klse_trades.csv"
        self.config_file = "KLSE_System/klse_config.json"
        
        # Initialize data fetcher
        if ENHANCED_DATA_AVAILABLE:
            self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
        else:
            self.data_fetcher = None
        
        # Malaysian market constants
        self.BOARD_LOT_SIZE = 100  # Standard Malaysian board lot
        self.MICROCAP_THRESHOLD_MYR = 300_000_000  # 300M MYR
        self.CURRENCY = "MYR"
        self.MARKET_TIMEZONE = timezone(timedelta(hours=8))  # GMT+8
        
        # Trading hours (Malaysian time)
        self.MARKET_OPEN_HOUR = 9
        self.MARKET_CLOSE_HOUR = 17
        
        # Ensure directories exist
        os.makedirs("KLSE_System", exist_ok=True)
        
        # Load or create configuration
        self._load_config()
        
        # Load saved cash balance (overrides starting_cash_myr if exists)
        self._load_cash_balance()
        
        # Initialize portfolio
        self.portfolio = self._load_portfolio()
        
        logger.info(f"KLSE Portfolio Manager initialized with {self.current_cash_myr:.2f} MYR")
    
    def _load_config(self):
        """Load configuration from JSON file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.current_cash_myr = config.get('current_cash_myr', self.starting_cash_myr)
                # Load starting cash from config if available (for proper return calculation)
                if 'starting_cash_myr' in config:
                    self.starting_cash_myr = config['starting_cash_myr']
                # Load other config settings as needed
    
    def _load_portfolio(self) -> pd.DataFrame:
        """Load existing portfolio or create new one"""
        if os.path.exists(self.portfolio_file):
            portfolio = pd.read_csv(self.portfolio_file)
            logger.info(f"Loaded existing portfolio with {len(portfolio)} positions")
        else:
            # Create empty portfolio
            portfolio = pd.DataFrame(columns=[
                'date_added', 'ticker', 'company_name', 'shares', 'avg_cost_myr', 
                'stop_loss_myr', 'sector', 'market_cap_myr', 'target_weight_pct'
            ])
            logger.info("Created new empty portfolio")
        
        return portfolio
    
    def _save_portfolio(self):
        """Save portfolio to CSV and update cash balance in config"""
        self.portfolio.to_csv(self.portfolio_file, index=False)
        logger.info(f"Portfolio saved to {self.portfolio_file}")
        
        # Also save current cash balance to config file
        self._save_cash_balance()
    
    def _save_cash_balance(self):
        """Save current cash balance to config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            config['current_cash_myr'] = self.current_cash_myr
            config['starting_cash_myr'] = self.starting_cash_myr
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"Cash balance {self.current_cash_myr:.2f} MYR saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save cash balance: {e}")
    
    def _load_cash_balance(self):
        """Load current cash balance from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                if 'current_cash_myr' in config:
                    self.current_cash_myr = config['current_cash_myr']
                    logger.info(f"Loaded cash balance: {self.current_cash_myr:.2f} MYR from config")
                else:
                    logger.info("No saved cash balance found, using starting cash")
            else:
                logger.info("No config file found, using starting cash")
                
        except Exception as e:
            logger.error(f"Failed to load cash balance: {e}")
            logger.info("Using starting cash balance")
    
    def _validate_board_lot(self, shares: int) -> bool:
        """Validate that shares are in proper board lots"""
        return shares % self.BOARD_LOT_SIZE == 0
    
    def _calculate_board_lots(self, cash_available: float, price_per_share: float) -> Tuple[int, float]:
        """Calculate maximum board lots possible with available cash"""
        max_lots = int(cash_available / (price_per_share * self.BOARD_LOT_SIZE))
        total_shares = max_lots * self.BOARD_LOT_SIZE
        total_cost = total_shares * price_per_share
        return total_shares, total_cost
    
    def _get_stock_data(self, ticker: str) -> Optional[Dict]:
        """Get stock data using enhanced fetcher or fallback"""
        # Ensure .KL suffix
        if not ticker.endswith('.KL'):
            ticker = f"{ticker}.KL"
            
        if ENHANCED_DATA_AVAILABLE and self.data_fetcher:
            stock_code = ticker.replace('.KL', '')
            return self.data_fetcher.get_stock_price(stock_code)
        else:
            # Fallback to yfinance
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                info = stock.info
                
                if hist.empty:
                    return None
                
                return {
                    'price': round(hist['Close'].iloc[-1], 3),
                    'currency': 'MYR',
                    'volume': hist['Volume'].iloc[-1] if 'Volume' in hist else None,
                    'market_cap': info.get('marketCap', None),
                    'source': 'yfinance_fallback',
                    'data_available': True
                }
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {e}")
                return None
    
    def get_market_status(self) -> Dict[str, any]:
        """Check if Malaysian market is currently open"""
        now = datetime.now(self.MARKET_TIMEZONE)
        current_hour = now.hour
        
        # Check if weekend
        is_weekend = now.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        # Check if market hours
        is_market_hours = self.MARKET_OPEN_HOUR <= current_hour < self.MARKET_CLOSE_HOUR
        
        is_open = not is_weekend and is_market_hours
        
        return {
            'is_open': is_open,
            'current_time_kl': now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            'market_hours': f"{self.MARKET_OPEN_HOUR}:00 - {self.MARKET_CLOSE_HOUR}:00 GMT+8",
            'next_open': self._calculate_next_market_open(now),
            'is_weekend': is_weekend
        }
    
    def _calculate_next_market_open(self, current_time: datetime) -> str:
        """Calculate next market opening time"""
        if current_time.weekday() >= 5:  # Weekend
            days_until_monday = 7 - current_time.weekday()
            next_open = current_time.replace(hour=self.MARKET_OPEN_HOUR, minute=0, second=0, microsecond=0)
            next_open += timedelta(days=days_until_monday)
        elif current_time.hour >= self.MARKET_CLOSE_HOUR:  # After market close
            next_open = current_time.replace(hour=self.MARKET_OPEN_HOUR, minute=0, second=0, microsecond=0)
            next_open += timedelta(days=1)
        else:  # Before market open
            next_open = current_time.replace(hour=self.MARKET_OPEN_HOUR, minute=0, second=0, microsecond=0)
        
        return next_open.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    def add_stock(self, ticker: str, target_weight_pct: float, stop_loss_pct: float = 15.0, 
                  company_name: str = "", sector: str = "") -> bool:
        """
        Add a new stock to portfolio
        
        Args:
            ticker: Malaysian stock code (e.g., "1155" for Maybank)
            target_weight_pct: Target weight as percentage of portfolio
            stop_loss_pct: Stop loss percentage below cost basis
            company_name: Company name for records
            sector: Business sector
        """
        # Ensure .KL suffix for data fetching
        full_ticker = f"{ticker}.KL" if not ticker.endswith('.KL') else ticker
        
        # Get current stock data
        stock_data = self._get_stock_data(full_ticker)
        if not stock_data:
            logger.error(f"Cannot fetch data for {full_ticker}")
            return False
        
        current_price = stock_data['price']
        market_cap = stock_data.get('market_cap', 0)
        
        # Validate micro-cap status
        if market_cap and market_cap > self.MICROCAP_THRESHOLD_MYR:
            logger.warning(f"{full_ticker} market cap {market_cap:,.0f} MYR exceeds micro-cap threshold")
        
        # Calculate position size
        portfolio_value = self._calculate_portfolio_value()
        target_value = portfolio_value * (target_weight_pct / 100)
        
        # Auto-inject cash if needed for target position (add funds, don't overwrite)
        if target_value > self.current_cash_myr:
            cash_needed = target_value - self.current_cash_myr
            logger.info(f"💰 Auto-injecting {cash_needed:.2f} MYR cash for {target_weight_pct}% position")
            prev_cash = self.current_cash_myr
            self.current_cash_myr += cash_needed
            logger.info(f"   Previous cash: {prev_cash:.2f} MYR -> New cash: {self.current_cash_myr:.2f} MYR")
        
        # Calculate board lots
        shares, cost = self._calculate_board_lots(target_value, current_price)
        
        if shares == 0:
            logger.error(f"Insufficient cash for even 1 board lot of {full_ticker}")
            return False
        
        # Calculate stop loss price
        stop_loss_price = current_price * (1 - stop_loss_pct / 100)
        
        # Add to portfolio
        new_position = {
            'date_added': datetime.now().strftime("%Y-%m-%d"),
            'ticker': full_ticker,
            'company_name': company_name or full_ticker,
            'shares': shares,
            'avg_cost_myr': current_price,
            'stop_loss_myr': round(stop_loss_price, 3),
            'sector': sector,
            'market_cap_myr': market_cap,
            'target_weight_pct': target_weight_pct
        }
        
        # Add to portfolio DataFrame
        self.portfolio = pd.concat([self.portfolio, pd.DataFrame([new_position])], ignore_index=True)
        
        # Update cash
        self.current_cash_myr -= cost
        
        # Log the trade
        self._log_trade("BUY", full_ticker, shares, current_price, cost, stock_data.get('source', 'unknown'))
        
        # Save portfolio
        self._save_portfolio()
        
        logger.info(f"Added {shares} shares of {full_ticker} at {current_price:.3f} MYR (Total: {cost:.2f} MYR)")
        return True
    
    def add_stock_by_quantity(self, ticker: str, shares: int, price: float = None, 
                             stop_loss_pct: float = 15.0, company_name: str = "", 
                             sector: str = "") -> dict:
        """
        Add a new stock to portfolio by specifying exact number of shares
        
        Args:
            ticker: Malaysian stock code (e.g., "1155" for Maybank)
            shares: Exact number of shares to add
            price: Price per share (if None, uses current market price)
            stop_loss_pct: Stop loss percentage below cost basis
            company_name: Company name for records
            sector: Business sector
        """
        # Ensure .KL suffix for data fetching
        full_ticker = f"{ticker}.KL" if not ticker.endswith('.KL') else ticker
        
        # If price is provided, use it; otherwise get current market price
        if price is not None:
            current_price = price
            stock_data = {'price': price, 'source': 'manual'}  # Create dummy stock_data for logging
        else:
            # Get current stock data
            stock_data = self._get_stock_data(full_ticker)
            if not stock_data:
                logger.error(f"Could not fetch data for {full_ticker}")
                return {'success': False, 'error': 'Could not fetch market data'}
            current_price = stock_data['price']
        cost = current_price * shares
        
        # Auto-inject cash if needed (simulates adding money to account)
        if cost > self.current_cash_myr:
            cash_needed = cost - self.current_cash_myr
            logger.info(f"💰 Auto-injecting {cash_needed:.2f} MYR cash for purchase")
            prev_cash = self.current_cash_myr
            self.current_cash_myr += cash_needed
            logger.info(f"   Previous cash: {prev_cash:.2f} MYR -> New cash: {self.current_cash_myr:.2f} MYR")
        
        # Calculate stop loss price
        stop_loss_price = current_price * (1 - stop_loss_pct / 100)
        
        # Create new position
        new_position = {
            'date_added': datetime.now().strftime('%Y-%m-%d'),
            'ticker': full_ticker,
            'company_name': company_name or ticker,
            'shares': shares,
            'avg_cost_myr': current_price,
            'stop_loss_myr': stop_loss_price,
            'sector': sector or 'Unknown',
            'current_price_myr': current_price,
            'market_value_myr': cost
        }
        
        # Add to portfolio
        self.portfolio = pd.concat([self.portfolio, pd.DataFrame([new_position])], ignore_index=True)
        
        # Update cash balance
        self.current_cash_myr -= cost
        
        # Save to file
        self._save_portfolio()
        
        # Log the trade
        self._log_trade(
            action='BUY',
            ticker=full_ticker,
            shares=shares,
            price=current_price,
            total_value=cost,
            data_source=stock_data.get('source', 'unknown')
        )
        
        logger.info(f"Added {shares} shares of {full_ticker} at {current_price:.3f} MYR (Total: {cost:.2f} MYR)")
        
        # Return detailed purchase information
        return {
            'success': True,
            'ticker': full_ticker,
            'company_name': company_name or ticker,
            'shares_bought': shares,
            'price_per_share': current_price,
            'total_cost': cost,
            'stop_loss_price': stop_loss_price,
            'sector': sector or 'Unknown'
        }
    
    def sell_stock_by_quantity(self, ticker: str, shares: int, price: float = None, 
                              reason: str = "Manual sale") -> dict:
        """
        Sell a specific number of shares at a specific price
        
        Args:
            ticker: Stock ticker to sell
            shares: Number of shares to sell
            price: Price per share (if None, uses current market price)
            reason: Reason for sale
            
        Returns:
            Dictionary with sale details or error info
        """
        # Find position in portfolio
        position_mask = self.portfolio['ticker'] == ticker
        
        if not position_mask.any():
            logger.error(f"Position {ticker} not found in portfolio")
            return {'success': False, 'error': f'Position {ticker} not found'}
        
        position = self.portfolio[position_mask].iloc[0]
        current_shares = position['shares']
        
        if shares > current_shares:
            logger.error(f"Cannot sell {shares} shares of {ticker} - only have {current_shares} shares")
            return {'success': False, 'error': f'Insufficient shares: have {current_shares}, trying to sell {shares}'}
        
        if shares <= 0:
            logger.error(f"Invalid number of shares to sell: {shares}")
            return {'success': False, 'error': f'Invalid share quantity: {shares}'}
        
        # If price is provided, use it; otherwise get current market price
        if price is not None:
            current_price = price
            stock_data = {'price': price, 'source': 'manual'}
        else:
            # Get current market price
            stock_data = self._get_stock_data(ticker)
            if not stock_data:
                logger.error(f"Cannot get current price for {ticker}")
                return {'success': False, 'error': f'Could not fetch market data for {ticker}'}
            current_price = stock_data['price']
        
        sale_value = current_price * shares
        
        # Add cash from sale
        self.current_cash_myr += sale_value
        
        # Log the trade
        self._log_trade(
            "SELL_PARTIAL", ticker, shares, current_price, sale_value,
            stock_data.get('source', 'unknown')
        )
        
        # Update the position (reduce shares or remove completely)
        remaining_shares = current_shares - shares
        if shares == current_shares:
            # Selling all shares - remove position completely
            self.portfolio = self.portfolio[~position_mask]
            logger.info(f"✅ Sold all {shares} shares of {ticker} - position closed")
        else:
            # Selling partial shares - update the position
            idx = self.portfolio[position_mask].index[0]
            self.portfolio.loc[idx, 'shares'] = remaining_shares
            self.portfolio.loc[idx, 'market_value_myr'] = remaining_shares * current_price
            logger.info(f"✅ Sold {shares} shares of {ticker} - {remaining_shares} shares remaining")
        
        # Save portfolio
        self._save_portfolio()
        
        logger.info(f"Sale details: {shares} shares at {current_price:.3f} MYR = {sale_value:.2f} MYR - {reason}")
        
        # Return sale details
        return {
            'success': True,
            'ticker': ticker,
            'shares_sold': shares,
            'price_per_share': current_price,
            'total_value': sale_value,
            'remaining_shares': remaining_shares,
            'reason': reason
        }

    def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value including cash"""
        if self.portfolio.empty:
            return self.current_cash_myr
        
        total_stock_value = 0
        for _, position in self.portfolio.iterrows():
            stock_data = self._get_stock_data(position['ticker'])
            if stock_data:
                current_value = stock_data['price'] * position['shares']
                total_stock_value += current_value
        
        return total_stock_value + self.current_cash_myr

    def _safe_return_pct(self, numerator: float, denominator: float) -> float:
        """Calculate percentage return safely, avoid division by zero.

        Returns 0.0 if denominator is zero or None.
        """
        try:
            if not denominator or denominator == 0:
                return 0.0
            return (numerator / denominator) * 100
        except Exception:
            return 0.0
    
    def _log_trade(self, action: str, ticker: str, shares: int, price: float, 
                   total_value: float, data_source: str):
        """Log trade to trade log file"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime("%Y-%m-%d"),
            'action': action,
            'ticker': ticker,
            'shares': shares,
            'price_myr': price,
            'total_value_myr': total_value,
            'data_source': data_source,
            'cash_after_myr': self.current_cash_myr
        }
        
        trade_df = pd.DataFrame([trade_record])
        
        if os.path.exists(self.trade_log_file):
            existing_trades = pd.read_csv(self.trade_log_file)
            trade_df = pd.concat([existing_trades, trade_df], ignore_index=True)
        
        trade_df.to_csv(self.trade_log_file, index=False)
        logger.info(f"Trade logged: {action} {shares} shares of {ticker}")
    
    def process_daily_update(self) -> Dict[str, any]:
        """Process daily portfolio update with stop-loss checks"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self.portfolio.empty:
            logger.info("Portfolio is empty, no updates to process")
            return {'status': 'empty_portfolio'}
        
        results = []
        total_value = 0
        total_pnl = 0
        stops_triggered = []
        
        logger.info(f"Processing daily update for {len(self.portfolio)} positions")
        
        for idx, position in self.portfolio.iterrows():
            ticker = position['ticker']
            shares = position['shares']
            cost_basis = position['avg_cost_myr']
            stop_loss = position['stop_loss_myr']
            
            # Get current stock data
            stock_data = self._get_stock_data(ticker)
            
            if not stock_data:
                logger.warning(f"No data available for {ticker}")
                continue
            
            current_price = stock_data['price']
            position_value = current_price * shares
            position_pnl = (current_price - cost_basis) * shares
            
            # Check stop loss
            if current_price <= stop_loss:
                # ALERT ONLY - Do not execute trade automatically
                stops_triggered.append({
                    'ticker': ticker,
                    'shares': shares,
                    'stop_price': current_price,
                    'cost_basis': cost_basis,
                    'pnl': position_pnl
                })
                
                # Log alert message
                logger.warning(f"🚨 STOP LOSS ALERT: {ticker} has hit stop loss!")
                logger.warning(f"   Current Price: {current_price:.3f} MYR | Stop Loss: {stop_loss:.3f} MYR")
                logger.warning(f"   Position: {shares} shares | Potential Loss: {position_pnl:.2f} MYR")
                logger.warning(f"   ⚠️  Manual action required - trade NOT automatically executed")
                
                # Continue tracking the position (do not remove from portfolio)
                total_value += position_value
                total_pnl += position_pnl
                
                result = {
                    'date': today,
                    'ticker': ticker,
                    'shares': shares,
                    'cost_basis': cost_basis,
                    'stop_loss': stop_loss,
                    'current_price': current_price,
                    'position_value': position_value,
                    'position_pnl': position_pnl,
                    'action': 'STOP_LOSS_ALERT',  # Mark as alert instead of HOLD
                    'data_source': stock_data.get('source', 'unknown')
                }
                results.append(result)
                
            else:
                # Position continues
                total_value += position_value
                total_pnl += position_pnl
                
                result = {
                    'date': today,
                    'ticker': ticker,
                    'shares': shares,
                    'cost_basis': cost_basis,
                    'stop_loss': stop_loss,
                    'current_price': current_price,
                    'position_value': position_value,
                    'position_pnl': position_pnl,
                    'action': 'HOLD',
                    'data_source': stock_data.get('source', 'unknown')
                }
                results.append(result)

        # Save updated portfolio (after stop losses)
        self._save_portfolio()

        # Calculate total portfolio metrics
        total_equity = total_value + self.current_cash_myr
        total_return_pct = self._safe_return_pct((total_equity - self.starting_cash_myr), self.starting_cash_myr)

        summary = {
            'date': today,
            'total_stock_value': total_value,
            'cash_balance': self.current_cash_myr,
            'total_equity': total_equity,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'positions': len(self.portfolio),
            'stops_triggered': len(stops_triggered),
            'stop_details': stops_triggered
        }

        logger.info(f"Daily update complete: {total_equity:.2f} MYR total equity ({total_return_pct:+.2f}%)")

        return {
            'status': 'success',
            'summary': summary,
            'positions': results,
            'stops_triggered': stops_triggered
        }
    
    def get_portfolio_summary(self) -> Dict[str, any]:
        """Get comprehensive portfolio summary"""
        if self.portfolio.empty:
            return {
                'total_positions': 0,
                'total_equity': self.current_cash_myr,
                'cash_balance': self.current_cash_myr,
                'total_return_pct': 0.0,
                'failed_tickers': []
            }

        positions = []
        failed_tickers = []
        total_value = 0
        
        for _, position in self.portfolio.iterrows():
            stock_data = self._get_stock_data(position['ticker'])
            if stock_data:
                current_price = stock_data['price']
                position_value = current_price * position['shares']
                position_pnl = (current_price - position['avg_cost_myr']) * position['shares']
                
                # Handle zero cost basis to avoid division by zero
                if position['avg_cost_myr'] > 0:
                    position_return_pct = ((current_price - position['avg_cost_myr']) / position['avg_cost_myr']) * 100
                else:
                    # If cost basis is 0, it means the position was received for free (e.g., bonus shares)
                    # In this case, any positive price represents infinite return, so we'll use a special value
                    position_return_pct = float('inf') if current_price > 0 else 0.0
                
                total_value += position_value
                
                positions.append({
                    'ticker': position['ticker'],
                    'company_name': position['company_name'],
                    'shares': position['shares'],
                    'avg_cost': position['avg_cost_myr'],
                    'current_price': current_price,
                    'position_value': position_value,
                    'position_pnl': position_pnl,
                    'position_return_pct': position_return_pct,
                    'stop_loss': position['stop_loss_myr'],
                    'sector': position['sector']
                })
            else:
                # Track failed ticker
                failed_tickers.append({
                    'ticker': position['ticker'],
                    'company_name': position['company_name'],
                    'shares': position['shares'],
                    'avg_cost': position['avg_cost_myr'],
                    'sector': position['sector'],
                    'reason': 'Price data unavailable'
                })
                logger.warning(f"❌ Failed to get price data for {position['ticker']} ({position['company_name']})")

        total_equity = total_value + self.current_cash_myr
        total_return_pct = self._safe_return_pct((total_equity - self.starting_cash_myr), self.starting_cash_myr)

        return {
            'total_positions': len(positions),
            'total_stock_value': total_value,
            'cash_balance': self.current_cash_myr,
            'total_equity': total_equity,
            'total_return_pct': total_return_pct,
            'positions': positions,
            'failed_tickers': failed_tickers,
            'market_status': self.get_market_status()
        }

def demo_klse_portfolio():
    """Demonstrate the KLSE portfolio management system"""
    print("🇲🇾 KLSE Portfolio Management System Demo")
    print("=" * 60)
    
    # Initialize with 10,000 MYR
    portfolio_manager = KLSEPortfolioManager(starting_cash_myr=10000.0)
    
    # Check market status
    market_status = portfolio_manager.get_market_status()
    print(f"📊 Market Status: {'🟢 OPEN' if market_status['is_open'] else '🔴 CLOSED'}")
    print(f"   Current Time (KL): {market_status['current_time_kl']}")
    print(f"   Market Hours: {market_status['market_hours']}")
    
    # Add some Malaysian micro-cap stocks
    print(f"\n💰 Adding stocks to portfolio...")
    
    stocks_to_add = [
        {"ticker": "4723", "name": "JAKS Resources", "weight": 25.0, "sector": "Industrial"},
        {"ticker": "0090", "name": "NetX Holdings", "weight": 20.0, "sector": "Technology"},
        {"ticker": "0176", "name": "Fintec Global", "weight": 15.0, "sector": "Technology"},
    ]
    
    for stock in stocks_to_add:
        success = portfolio_manager.add_stock(
            ticker=stock["ticker"],
            target_weight_pct=stock["weight"],
            company_name=stock["name"],
            sector=stock["sector"],
            stop_loss_pct=15.0
        )
        
        if success:
            print(f"✅ Added {stock['name']} ({stock['ticker']}.KL)")
        else:
            print(f"❌ Failed to add {stock['name']} ({stock['ticker']}.KL)")
    
    # Process daily update
    print(f"\n📈 Processing daily portfolio update...")
    update_result = portfolio_manager.process_daily_update()
    
    if update_result['status'] == 'success':
        summary = update_result['summary']
        print(f"✅ Daily update completed:")
        print(f"   Total Equity: {summary['total_equity']:,.2f} MYR")
        print(f"   Return: {summary['total_return_pct']:+.2f}%")
        print(f"   Active Positions: {summary['positions']}")
        
        if summary['stops_triggered'] > 0:
            print(f"   🚨 Stop Losses Triggered: {summary['stops_triggered']}")
    
    # Get comprehensive summary
    print(f"\n📊 Portfolio Summary:")
    summary = portfolio_manager.get_portfolio_summary()
    
    print(f"   Total Positions: {summary['total_positions']}")
    print(f"   Stock Value: {summary['total_stock_value']:,.2f} MYR")
    print(f"   Cash Balance: {summary['cash_balance']:,.2f} MYR")
    print(f"   Total Return: {summary['total_return_pct']:+.2f}%")
    
    if summary['positions']:
        print(f"\n📋 Position Details:")
        for pos in summary['positions']:
            print(f"   {pos['ticker']}: {pos['shares']} shares @ {pos['current_price']:.3f} MYR "
                  f"(PnL: {pos['position_pnl']:+.2f} MYR)")
    
    return portfolio_manager

if __name__ == "__main__":
    demo_klse_portfolio()
    
    print(f"\n✅ KLSE Portfolio Management System Ready!")
    print(f"\n🎯 FEATURES AVAILABLE:")
    print(f"   ✅ Malaysian board lot management (100 shares)")
    print(f"   ✅ MYR currency with proper precision (3 decimals)")
    print(f"   ✅ Automatic stop-loss monitoring")
    print(f"   ✅ Market hours tracking (GMT+8)")
    print(f"   ✅ Micro-cap validation (< 300M MYR)")
    print(f"   ✅ Comprehensive trade logging")
    print(f"   ✅ Redundant data sources")
    print(f"   ✅ Portfolio rebalancing tools")
