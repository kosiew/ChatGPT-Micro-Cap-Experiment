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
        self.capital_flow_file = "KLSE_System/klse_capital_flows.csv"
        self.config_file = "KLSE_System/klse_config.json"

        # Capital paid in beyond the starting cash. Buys that exceed cash on
        # hand top the account up, and that top-up is contributed capital, not
        # profit - returns must be measured against it or every injection
        # inflates the reported return.
        self.injected_capital_myr = 0.0
        
        # Initialize data fetcher
        if ENHANCED_DATA_AVAILABLE:
            self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
        else:
            self.data_fetcher = None
        
        # Trailing stop loss: the stop trails the highest price seen since entry
        # (the high-water mark), not the average purchase price, so it ratchets
        # up with a winning position to lock in gains and never moves down.
        self.DEFAULT_TRAIL_PCT = 15.0

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
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.current_cash_myr = config.get('current_cash_myr', self.starting_cash_myr)
                # Load starting cash from config if available (for proper return calculation)
                if 'starting_cash_myr' in config:
                    self.starting_cash_myr = config['starting_cash_myr']
                self.injected_capital_myr = config.get('injected_capital_myr', 0.0)
                # Load other config settings as needed
    
    def _validate_portfolio_data(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Validate portfolio data and fix/flag issues
        
        Checks:
        1. Cost basis must be > 0
        2. Stop loss must be < the high-water mark (trailing by trail_pct)
        3. Shares must be > 0
        4. Stop loss should sit close to the trail implied by the high-water mark
        """
        if portfolio.empty:
            return portfolio
        
        validation_errors = []
        fixed_positions = []
        
        for idx, row in portfolio.iterrows():
            ticker = row['ticker']
            avg_cost = row['avg_cost_myr']
            stop_loss = row['stop_loss_myr']
            shares = row['shares']
            highest = float(row.get('highest_price_myr') or 0) or avg_cost
            trail_pct = float(row.get('trail_pct') or self.DEFAULT_TRAIL_PCT)
            
            has_error = False
            error_details = []
            
            # Validation 1: Cost basis must be positive
            if avg_cost <= 0:
                has_error = True
                error_details.append(f"Invalid cost basis: {avg_cost:.3f} MYR (must be > 0)")
            
            # Validation 2: Shares must be positive
            if shares <= 0:
                has_error = True
                error_details.append(f"Invalid shares: {shares} (must be > 0)")
            
            # Validation 3: Stop loss must be below the high-water mark. It may
            # legitimately sit above the cost basis - a trailing stop that has
            # ratcheted up on a winner is exactly that.
            if highest > 0 and stop_loss >= highest:
                has_error = True
                error_details.append(
                    f"Invalid stop loss: {stop_loss:.3f} MYR >= high-water mark {highest:.3f} MYR "
                    f"(stop loss must trail below the highest price seen)"
                )
            
            # Validation 4: Stop loss should match the trail implied by the
            # high-water mark, within a tolerance for rounding and manual edits.
            if highest > 0:
                expected_stop = self._trailing_stop_price(highest, trail_pct)
                if abs(stop_loss - expected_stop) > max(0.01, expected_stop * 0.05):
                    has_error = True
                    error_details.append(
                        f"Stop loss {stop_loss:.3f} MYR does not match a {trail_pct:.0f}% trail "
                        f"below the high-water mark {highest:.3f} MYR (expected ~{expected_stop:.3f} MYR)"
                    )
            
            # Validation 5: Stop loss must be positive
            if stop_loss <= 0:
                has_error = True
                error_details.append(f"Invalid stop loss: {stop_loss:.3f} MYR (must be > 0)")
            
            if has_error:
                validation_errors.append({
                    'ticker': ticker,
                    'company': row.get('company_name', 'Unknown'),
                    'shares': shares,
                    'cost_basis': avg_cost,
                    'stop_loss': stop_loss,
                    'errors': error_details
                })
                
                logger.warning(f"⚠️  Data validation failed for {ticker}:")
                for error in error_details:
                    logger.warning(f"    - {error}")
        
        # Report all validation errors
        if validation_errors:
            logger.error("=" * 80)
            logger.error("🚨 PORTFOLIO DATA VALIDATION ERRORS DETECTED")
            logger.error("=" * 80)
            logger.error(f"Found {len(validation_errors)} position(s) with data integrity issues:\n")
            
            for i, error_info in enumerate(validation_errors, 1):
                logger.error(f"{i}. {error_info['ticker']} ({error_info['company']})")
                logger.error(f"   Shares: {error_info['shares']}")
                logger.error(f"   Cost Basis: {error_info['cost_basis']:.3f} MYR")
                logger.error(f"   Stop Loss: {error_info['stop_loss']:.3f} MYR")
                logger.error(f"   Issues:")
                for err in error_info['errors']:
                    logger.error(f"     • {err}")
                logger.error("")
            
            logger.error("=" * 80)
            logger.error("⚠️  ACTION REQUIRED: Please manually correct the portfolio CSV file")
            logger.error(f"   File location: {self.portfolio_file}")
            logger.error("   These positions will continue to be tracked but may cause errors")
            logger.error("=" * 80)
        
        return portfolio
    
    @staticmethod
    def _trailing_stop_price(highest_price: float, trail_pct: float) -> float:
        """Stop price implied by a high-water mark and a trail percentage."""
        return round(float(highest_price) * (1 - float(trail_pct) / 100), 3)

    def _seed_high_water_mark(self, row) -> float:
        """Starting high-water mark for a position being converted.

        Deliberately seeded from today's price rather than the historical peak
        since entry: the trail starts here and ratchets up from today onwards,
        so a drawdown that already happened does not fire a stop on the very
        first run. Floored at the entry price so the converted stop is never
        looser than the cost-based one it replaces.
        """
        avg_cost = float(row['avg_cost_myr'])

        seed = None
        try:
            stock_data = self._get_stock_data(row['ticker'])
            if stock_data and stock_data.get('price'):
                seed = float(stock_data['price'])
        except Exception as exc:
            logger.warning(f"Could not fetch today's price for {row['ticker']}: {exc}")

        if seed is None:
            # Only when today's price is unavailable: the last price the
            # portfolio recorded is a better guess than the cost basis alone.
            seed = float(row.get('current_price_myr') or 0)

        return max(avg_cost, seed)

    def _ensure_trailing_columns(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """Add and backfill the trailing-stop columns on a legacy portfolio.

        Runs once: a portfolio written before trailing stops has no
        highest_price_myr, so the high-water mark is seeded from today's price
        and the trail ratchets up from there.
        """
        if portfolio.empty:
            for column in ('highest_price_myr', 'trail_pct'):
                if column not in portfolio.columns:
                    portfolio[column] = pd.Series(dtype='float64')
            return portfolio

        if 'trail_pct' not in portfolio.columns:
            portfolio['trail_pct'] = self.DEFAULT_TRAIL_PCT
        portfolio['trail_pct'] = pd.to_numeric(
            portfolio['trail_pct'], errors='coerce').fillna(self.DEFAULT_TRAIL_PCT)

        seeding = 'highest_price_myr' not in portfolio.columns
        if seeding:
            portfolio['highest_price_myr'] = np.nan
            logger.info("Backfilling trailing-stop high-water marks from price history")

        for idx, row in portfolio.iterrows():
            if pd.notna(row.get('highest_price_myr')) and float(row['highest_price_myr']) > 0:
                continue

            ticker = row['ticker']
            peak = self._seed_high_water_mark(row)

            trail_pct = float(portfolio.at[idx, 'trail_pct'])
            portfolio.at[idx, 'highest_price_myr'] = round(peak, 3)
            portfolio.at[idx, 'stop_loss_myr'] = self._trailing_stop_price(peak, trail_pct)

            if seeding:
                logger.info(
                    f"  {ticker}: high-water mark {peak:.3f} MYR -> trailing stop "
                    f"{portfolio.at[idx, 'stop_loss_myr']:.3f} MYR ({trail_pct:.0f}% trail)"
                )

        return portfolio

    def _ratchet_trailing_stop(self, idx, current_price: float) -> bool:
        """Raise the high-water mark and stop if price made a new high.

        Returns True when the stop moved. The stop only ever ratchets up: a
        falling price leaves it where it is, which is what makes it a stop.
        """
        trail_pct = float(self.portfolio.at[idx, 'trail_pct'])
        previous_high = float(self.portfolio.at[idx, 'highest_price_myr'])
        if current_price <= previous_high:
            return False

        new_stop = self._trailing_stop_price(current_price, trail_pct)
        self.portfolio.at[idx, 'highest_price_myr'] = round(current_price, 3)
        self.portfolio.at[idx, 'stop_loss_myr'] = new_stop
        logger.info(
            f"📈 {self.portfolio.at[idx, 'ticker']}: new high {current_price:.3f} MYR "
            f"(was {previous_high:.3f}) -> trailing stop raised to {new_stop:.3f} MYR"
        )
        return True

    def _load_portfolio(self) -> pd.DataFrame:
        """Load existing portfolio or create new one"""
        if os.path.exists(self.portfolio_file):
            portfolio = pd.read_csv(self.portfolio_file)
            logger.info(f"Loaded existing portfolio with {len(portfolio)} positions")
            
            # Backfill trailing-stop columns before validating: the validator
            # judges the stop against the high-water mark, not the cost basis.
            portfolio = self._ensure_trailing_columns(portfolio)
            
            # Validate loaded portfolio data
            portfolio = self._validate_portfolio_data(portfolio)
        else:
            # Create empty portfolio
            portfolio = pd.DataFrame(columns=[
                'date_added', 'ticker', 'company_name', 'shares', 'avg_cost_myr', 
                'stop_loss_myr', 'highest_price_myr', 'trail_pct', 'sector',
                'market_cap_myr', 'target_weight_pct'
            ])
            logger.info("Created new empty portfolio")
        
        return portfolio
    
    def _save_portfolio(self):
        """Save portfolio to CSV and update cash balance in config"""
        # Validate before saving to prevent data corruption
        if not self.portfolio.empty:
            validation_result = self._validate_before_save(self.portfolio)
            if not validation_result['valid']:
                logger.error("❌ Portfolio validation failed - NOT SAVING to prevent data corruption")
                logger.error(f"   Errors: {validation_result['errors']}")
                raise ValueError(f"Portfolio validation failed: {validation_result['errors']}")
        
        self.portfolio.to_csv(self.portfolio_file, index=False)
        logger.info(f"Portfolio saved to {self.portfolio_file}")
        
        # Also save current cash balance to config file
        self._save_cash_balance()
    
    def _validate_before_save(self, portfolio: pd.DataFrame) -> dict:
        """
        Quick validation before saving to prevent obvious data corruption
        Returns: {'valid': bool, 'errors': list}
        """
        errors = []
        
        for idx, row in portfolio.iterrows():
            ticker = row['ticker']
            avg_cost = row['avg_cost_myr']
            stop_loss = row['stop_loss_myr']
            shares = row['shares']
            
            # Critical validations that must pass
            if avg_cost <= 0:
                errors.append(f"{ticker}: cost_basis={avg_cost} must be > 0")
            
            if shares <= 0:
                errors.append(f"{ticker}: shares={shares} must be > 0")
            
            if stop_loss <= 0:
                errors.append(f"{ticker}: stop_loss={stop_loss} must be > 0")
            
            # Note: stop_loss CAN be >= avg_cost for trailing stops to lock in profits
            # Only validate that stop_loss is positive and reasonable
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
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
            config['injected_capital_myr'] = round(self.injected_capital_myr, 2)
            
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
                
                self.injected_capital_myr = config.get('injected_capital_myr',
                                                       self.injected_capital_myr)
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
    
    def _resolve_ticker(self, ticker: str) -> str:
        """Normalize a KLSE code to the .KL form used throughout the portfolio."""
        ticker = str(ticker).strip().upper()
        return ticker if ticker.endswith('.KL') else f"{ticker}.KL"

    def _consolidate_position_rows(self, full_ticker: str) -> Optional[int]:
        """Collapse any duplicate rows for a ticker into one weighted-average row.

        Older portfolio files carry a separate row per purchase, but the sell,
        stop-loss and P&L paths all assume one row per counter and only look at
        the first match. Returns the index of the surviving row, or None when the
        ticker is not held.
        """
        if self.portfolio.empty or 'ticker' not in self.portfolio.columns:
            return None

        idxs = list(self.portfolio.index[self.portfolio['ticker'] == full_ticker])
        if not idxs:
            return None
        if len(idxs) == 1:
            return idxs[0]

        keep = idxs[0]
        rows = self.portfolio.loc[idxs]
        shares = rows['shares'].astype(float)
        total_shares = float(shares.sum())
        if total_shares <= 0:
            return keep

        # Share-weighted average keeps the aggregate cost basis intact. The
        # high-water mark is a maximum, not an average - averaging it would
        # lower the peak the trail is anchored to and loosen the stop.
        avg_cost = round(float((shares * rows['avg_cost_myr'].astype(float)).sum()) / total_shares, 8)
        trail_pct = float(rows['trail_pct'].astype(float).min())
        highest = float(rows['highest_price_myr'].astype(float).max())
        avg_stop = self._trailing_stop_price(highest, trail_pct)

        self.portfolio.loc[keep, 'shares'] = int(total_shares) if total_shares.is_integer() else total_shares
        self.portfolio.loc[keep, 'avg_cost_myr'] = avg_cost
        self.portfolio.loc[keep, 'highest_price_myr'] = round(highest, 3)
        self.portfolio.loc[keep, 'trail_pct'] = trail_pct
        self.portfolio.loc[keep, 'stop_loss_myr'] = avg_stop
        if 'current_price_myr' in self.portfolio.columns:
            prices = rows['current_price_myr'].astype(float).dropna()
            if not prices.empty:
                latest_price = float(prices.iloc[-1])
                self.portfolio.loc[keep, 'current_price_myr'] = latest_price
                if 'market_value_myr' in self.portfolio.columns:
                    self.portfolio.loc[keep, 'market_value_myr'] = round(total_shares * latest_price, 2)

        self.portfolio = self.portfolio.drop(index=idxs[1:])
        logger.warning(
            f"Consolidated {len(idxs)} duplicate rows for {full_ticker} into "
            f"{total_shares:,.0f} shares @ {avg_cost:.4f} MYR (stop loss {avg_stop:.4f})"
        )
        return keep

    def _merge_into_existing_position(self, full_ticker: str, shares: int, price: float,
                                      stop_loss_pct: float) -> bool:
        """Fold a new buy into an existing holding of the same ticker.

        Recomputes the weighted average cost instead of appending a second row
        for a counter we already own - a duplicate row hides the true position
        size from the sell and stop-loss paths, which only look at the first
        matching row. The trailing stop is re-derived from the high-water mark,
        which topping up can only raise, never lower.
        Returns True when an existing position was updated.
        """
        idx = self._consolidate_position_rows(full_ticker)
        if idx is None:
            return False

        old_shares = float(self.portfolio.loc[idx, 'shares'])
        old_cost = float(self.portfolio.loc[idx, 'avg_cost_myr'])
        total_shares = old_shares + shares
        if total_shares <= 0:
            return False

        # 8dp on the cost basis: a coarser average visibly shifts total cost on
        # positions of 100k+ shares.
        avg_cost = round((old_shares * old_cost + shares * price) / total_shares, 8)
        old_high = float(self.portfolio.loc[idx, 'highest_price_myr'] or 0)
        highest = max(old_high, price)
        stop_loss = self._trailing_stop_price(highest, stop_loss_pct)

        self.portfolio.loc[idx, 'shares'] = int(total_shares) if total_shares.is_integer() else total_shares
        self.portfolio.loc[idx, 'avg_cost_myr'] = avg_cost
        self.portfolio.loc[idx, 'highest_price_myr'] = round(highest, 3)
        self.portfolio.loc[idx, 'trail_pct'] = stop_loss_pct
        self.portfolio.loc[idx, 'stop_loss_myr'] = stop_loss
        if 'current_price_myr' in self.portfolio.columns:
            self.portfolio.loc[idx, 'current_price_myr'] = price
        if 'market_value_myr' in self.portfolio.columns:
            self.portfolio.loc[idx, 'market_value_myr'] = round(total_shares * price, 2)

        logger.info(
            f"Merged {shares:,} shares of {full_ticker} at {price:.3f} into existing "
            f"{old_shares:,.0f} @ {old_cost:.3f} -> {total_shares:,.0f} @ {avg_cost:.4f} MYR "
            f"(high-water mark {highest:.3f}, trailing stop {stop_loss:.4f})"
        )
        return True

    def add_stock(self, ticker: str, target_weight_pct: float, stop_loss_pct: float = 15.0, 
                  company_name: str = "", sector: str = "") -> bool:
        """
        Add a new stock to portfolio
        
        Args:
            ticker: Malaysian stock code (e.g., "1155" for Maybank)
            target_weight_pct: Target weight as percentage of portfolio
            stop_loss_pct: Trailing stop percentage below the high-water mark
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
            self._record_capital_injection(
                target_value - self.current_cash_myr,
                f"{target_weight_pct}% target position in {full_ticker}",
                full_ticker)
        
        # Calculate board lots
        shares, cost = self._calculate_board_lots(target_value, current_price)
        
        if shares == 0:
            logger.error(f"Insufficient cash for even 1 board lot of {full_ticker}")
            return False
        
        # Trailing stop: the entry price is the first high-water mark
        stop_loss_price = self._trailing_stop_price(current_price, stop_loss_pct)
        
        # Fold into the existing holding if we already own this counter
        if not self._merge_into_existing_position(full_ticker, shares, current_price, stop_loss_pct):
            # Add to portfolio
            new_position = {
                'date_added': datetime.now().strftime("%Y-%m-%d"),
                'ticker': full_ticker,
                'company_name': company_name or full_ticker,
                'shares': shares,
                'avg_cost_myr': current_price,
                'stop_loss_myr': stop_loss_price,
                'highest_price_myr': round(current_price, 3),
                'trail_pct': stop_loss_pct,
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
            stop_loss_pct: Trailing stop percentage below the high-water mark
            company_name: Company name for records
            sector: Business sector
        """
        # Input validation
        if shares <= 0:
            logger.error(f"Invalid shares: {shares} (must be > 0)")
            return {'success': False, 'error': 'Shares must be positive'}
        
        if price is not None and price <= 0:
            logger.error(f"Invalid price: {price} (must be > 0)")
            return {'success': False, 'error': 'Price must be positive'}
        
        if stop_loss_pct < 0 or stop_loss_pct >= 100:
            logger.error(f"Invalid stop loss percentage: {stop_loss_pct}% (must be between 0 and 100)")
            return {'success': False, 'error': 'Stop loss percentage must be between 0 and 100'}
        
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
        
        # Validate current price
        if current_price <= 0:
            logger.error(f"Invalid market price for {full_ticker}: {current_price}")
            return {'success': False, 'error': 'Invalid market price'}
        
        cost = current_price * shares
        
        # Auto-inject cash if the buy exceeds cash on hand
        if cost > self.current_cash_myr:
            self._record_capital_injection(
                cost - self.current_cash_myr,
                f"buy {shares:,} {full_ticker} @ {current_price:.3f}",
                full_ticker)
        
        # Trailing stop: the entry price is the first high-water mark
        stop_loss_price = self._trailing_stop_price(current_price, stop_loss_pct)
        
        # Validate stop loss calculation
        if stop_loss_price <= 0:
            logger.error(f"Invalid stop loss calculation: {stop_loss_price} (check stop_loss_pct: {stop_loss_pct}%)")
            return {'success': False, 'error': 'Invalid stop loss calculation'}
        
        if stop_loss_price >= current_price:
            logger.error(f"Stop loss {stop_loss_price:.3f} is not below entry price {current_price:.3f}")
            return {'success': False, 'error': 'Stop loss must be below the entry price'}
        
        # Fold into the existing holding if we already own this counter
        if not self._merge_into_existing_position(full_ticker, shares, current_price, stop_loss_pct):
            # Create new position
            new_position = {
                'date_added': datetime.now().strftime('%Y-%m-%d'),
                'ticker': full_ticker,
                'company_name': company_name or ticker,
                'shares': shares,
                'avg_cost_myr': current_price,
                'stop_loss_myr': stop_loss_price,
                'highest_price_myr': round(current_price, 3),
                'trail_pct': stop_loss_pct,
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
            ticker: Stock ticker to sell, with or without the .KL suffix
            shares: Number of shares to sell
            price: Price per share (if None, uses current market price)
            reason: Reason for sale
            
        Returns:
            Dictionary with sale details or error info
        """
        # Validate the request before touching the portfolio or the cash balance
        try:
            shares = int(shares)
        except (TypeError, ValueError):
            logger.error(f"Invalid number of shares to sell: {shares!r}")
            return {'success': False, 'error': f'Invalid share quantity: {shares!r}'}

        if shares <= 0:
            logger.error(f"Invalid number of shares to sell: {shares}")
            return {'success': False, 'error': f'Invalid share quantity: {shares}'}

        if price is not None and price <= 0:
            logger.error(f"Invalid price: {price} (must be > 0)")
            return {'success': False, 'error': 'Price must be positive'}

        full_ticker = self._resolve_ticker(ticker)

        # Fold duplicate rows together first: selling against a single row would
        # see only part of the holding, and closing it would drop every other row
        # for the same counter along with it.
        idx = self._consolidate_position_rows(full_ticker)
        if idx is None:
            logger.error(f"Position {full_ticker} not found in portfolio")
            return {'success': False, 'error': f'Position {full_ticker} not found'}

        current_shares = float(self.portfolio.loc[idx, 'shares'])

        if shares > current_shares:
            logger.error(f"Cannot sell {shares:,} shares of {full_ticker} - only have {current_shares:,.0f} shares")
            return {'success': False,
                    'error': f'Insufficient shares: have {current_shares:,.0f}, trying to sell {shares:,}'}

        # If price is provided, use it; otherwise get current market price
        if price is not None:
            current_price = price
            stock_data = {'price': price, 'source': 'manual'}
        else:
            # Get current market price
            stock_data = self._get_stock_data(full_ticker)
            if not stock_data:
                logger.error(f"Cannot get current price for {full_ticker}")
                return {'success': False, 'error': f'Could not fetch market data for {full_ticker}'}
            current_price = stock_data['price']

        if current_price is None or current_price <= 0:
            logger.error(f"Invalid market price for {full_ticker}: {current_price}")
            return {'success': False, 'error': 'Invalid market price'}

        sale_value = current_price * shares
        remaining_shares = current_shares - shares

        # Snapshot so a rejected save leaves the books exactly as they were
        prev_portfolio = self.portfolio.copy()
        prev_cash = self.current_cash_myr

        # Update the position (reduce shares or close it out)
        if remaining_shares <= 0:
            self.portfolio = self.portfolio.drop(index=idx)
        else:
            self.portfolio.loc[idx, 'shares'] = (
                int(remaining_shares) if remaining_shares.is_integer() else remaining_shares
            )
            if 'current_price_myr' in self.portfolio.columns:
                self.portfolio.loc[idx, 'current_price_myr'] = current_price
            if 'market_value_myr' in self.portfolio.columns:
                self.portfolio.loc[idx, 'market_value_myr'] = round(remaining_shares * current_price, 2)

        # Add cash from sale
        self.current_cash_myr += sale_value

        # Save portfolio - validation failures roll the sale back entirely
        try:
            self._save_portfolio()
        except ValueError as exc:
            self.portfolio = prev_portfolio
            self.current_cash_myr = prev_cash
            logger.error(f"Sale of {shares:,} shares of {full_ticker} rolled back: {exc}")
            return {'success': False, 'error': f'Portfolio validation failed: {exc}'}

        # Log the trade only once the portfolio is safely on disk
        action = "SELL_ALL" if remaining_shares <= 0 else "SELL_PARTIAL"
        self._log_trade(
            action, full_ticker, shares, current_price, sale_value,
            stock_data.get('source', 'unknown')
        )

        if remaining_shares <= 0:
            logger.info(f"✅ Sold all {shares:,} shares of {full_ticker} - position closed")
        else:
            logger.info(f"✅ Sold {shares:,} shares of {full_ticker} - {remaining_shares:,.0f} shares remaining")

        logger.info(f"Sale details: {shares:,} shares at {current_price:.3f} MYR = {sale_value:.2f} MYR - {reason}")

        # Return sale details
        return {
            'success': True,
            'ticker': full_ticker,
            'action': action,
            'shares_sold': shares,
            'price_per_share': current_price,
            'total_value': sale_value,
            'remaining_shares': int(remaining_shares) if remaining_shares.is_integer() else remaining_shares,
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

    @property
    def total_contributed_capital_myr(self) -> float:
        """Cash actually paid in: the starting balance plus every injection.

        This, not starting_cash_myr, is the denominator for returns. Funding a
        buy out of fresh capital raises equity without earning anything, so
        measuring against the starting balance alone books the injection as
        profit.
        """
        return self.starting_cash_myr + self.injected_capital_myr

    def _record_capital_injection(self, amount: float, reason: str, ticker: str = "") -> None:
        """Add fresh capital to the account and write it to the capital ledger."""
        if amount <= 0:
            return

        prev_cash = self.current_cash_myr
        self.current_cash_myr += amount
        self.injected_capital_myr += amount

        logger.info(f"💰 Capital injection: {amount:,.2f} MYR ({reason})")
        logger.info(f"   Cash: {prev_cash:,.2f} -> {self.current_cash_myr:,.2f} MYR | "
                    f"Total contributed capital: {self.total_contributed_capital_myr:,.2f} MYR")

        now = datetime.now()
        entry = {
            'timestamp': now.isoformat(),
            'date': now.strftime('%Y-%m-%d'),
            'type': 'INJECTION',
            'ticker': ticker,
            'amount_myr': round(amount, 2),
            'reason': reason,
            'cash_after_injection_myr': round(self.current_cash_myr, 2),
            'total_injected_myr': round(self.injected_capital_myr, 2),
            'contributed_capital_myr': round(self.total_contributed_capital_myr, 2),
        }
        try:
            frame = pd.DataFrame([entry])
            header = not os.path.exists(self.capital_flow_file)
            frame.to_csv(self.capital_flow_file, mode='a', header=header, index=False)
        except Exception as exc:
            logger.error(f"Failed to write capital flow ledger: {exc}")

        self._save_cash_balance()

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
        
        stops_raised = []

        for idx, position in self.portfolio.iterrows():
            ticker = position['ticker']
            shares = position['shares']
            cost_basis = position['avg_cost_myr']
            
            # Get current stock data
            stock_data = self._get_stock_data(ticker)
            
            if not stock_data:
                logger.warning(f"No data available for {ticker}")
                continue
            
            current_price = stock_data['price']

            # Ratchet the trailing stop up on a new high before testing it, so a
            # position that peaked and closed lower on the same day is measured
            # against the trail from that new peak.
            if self._ratchet_trailing_stop(idx, current_price):
                stops_raised.append({
                    'ticker': ticker,
                    'company_name': position.get('company_name', ''),
                    'highest_price': float(self.portfolio.at[idx, 'highest_price_myr']),
                    'stop_loss': float(self.portfolio.at[idx, 'stop_loss_myr'])
                })
            stop_loss = float(self.portfolio.at[idx, 'stop_loss_myr'])
            highest_price = float(self.portfolio.at[idx, 'highest_price_myr'])

            position_value = current_price * shares
            position_pnl = (current_price - cost_basis) * shares
            
            # Check stop loss
            if current_price <= stop_loss:
                # ALERT ONLY - Do not execute trade automatically
                stops_triggered.append({
                    'ticker': ticker,
                    'company_name': position.get('company_name', ''),
                    'shares': shares,
                    'stop_price': current_price,
                    'cost_basis': cost_basis,
                    'stop_loss': stop_loss,
                    'highest_price': highest_price,
                    'trail_pct': float(self.portfolio.at[idx, 'trail_pct']),
                    'pnl': position_pnl
                })
                
                # Log alert message
                logger.warning(f"🚨 TRAILING STOP ALERT: {ticker} ({position.get('company_name','')}) has hit its trailing stop!")
                logger.warning(f"   Current Price: {current_price:.3f} MYR | Stop Loss: {stop_loss:.3f} MYR "
                               f"| High-Water Mark: {highest_price:.3f} MYR")
                logger.warning(f"   Position: {shares} shares | Potential Loss: {position_pnl:.2f} MYR")
                logger.warning(f"   ⚠️  Manual action required - trade NOT automatically executed")
                
                # Continue tracking the position (do not remove from portfolio)
                total_value += position_value
                total_pnl += position_pnl
                
                result = {
                    'date': today,
                    'ticker': ticker,
                    'company_name': position.get('company_name',''),
                    'shares': shares,
                    'cost_basis': cost_basis,
                    'stop_loss': stop_loss,
                    'highest_price': highest_price,
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
                    'highest_price': highest_price,
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
        contributed = self.total_contributed_capital_myr
        total_return_pct = self._safe_return_pct((total_equity - contributed), contributed)

        summary = {
            'date': today,
            'total_stock_value': total_value,
            'cash_balance': self.current_cash_myr,
            'total_equity': total_equity,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'starting_capital': self.starting_cash_myr,
            'capital_injected': self.injected_capital_myr,
            'contributed_capital': contributed,
            'positions': len(self.portfolio),
            'stops_triggered': len(stops_triggered),
            'stop_details': stops_triggered,
            'stops_raised': len(stops_raised),
            'raised_details': stops_raised
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
                    'highest_price': position.get('highest_price_myr', position['avg_cost_myr']),
                    'trail_pct': position.get('trail_pct', self.DEFAULT_TRAIL_PCT),
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
        contributed = self.total_contributed_capital_myr
        total_return_pct = self._safe_return_pct((total_equity - contributed), contributed)

        return {
            'total_positions': len(positions),
            'total_stock_value': total_value,
            'cash_balance': self.current_cash_myr,
            'total_equity': total_equity,
            'total_return_pct': total_return_pct,
            'starting_capital': self.starting_cash_myr,
            'capital_injected': self.injected_capital_myr,
            'contributed_capital': contributed,
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
