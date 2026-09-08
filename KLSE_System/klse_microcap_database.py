#!/usr/bin/env python3
"""
KLSE Micro-Cap Database System
Comprehensive database of Malaysian micro-cap stocks for AI trading selection
"""

import pandas as pd
import numpy as np
import json
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import time

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from redundant_data_fetcher import KLSEDataFetcher
    ENHANCED_DATA_AVAILABLE = True
except ImportError:
    print("⚠️  Enhanced data fetcher not available, using basic functionality")
    ENHANCED_DATA_AVAILABLE = False
    try:
        import yfinance as yf
    except ImportError:
        print("❌ No data sources available")
        yf = None

# Shared with the portfolio manager so the empty-concat guard has one
# definition. Kept in its own try so a failure here cannot flip
# ENHANCED_DATA_AVAILABLE above.
try:
    from KLSE_System.klse_portfolio_manager import append_row
except ImportError:
    def append_row(frame, row):
        """Local stand-in when the portfolio manager cannot be imported."""
        if frame is None or frame.empty:
            return row
        return pd.concat([frame, row], ignore_index=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KLSEMicroCapDatabase:
    """
    Comprehensive Malaysian micro-cap stock database and analysis system
    """
    
    def __init__(self, alpha_vantage_key: str = None):
        self.alpha_vantage_key = alpha_vantage_key
        
        # Initialize data fetcher
        if ENHANCED_DATA_AVAILABLE:
            self.data_fetcher = KLSEDataFetcher(alpha_vantage_key)
        else:
            self.data_fetcher = None
        
        # Database files
        self.database_file = "KLSE_System/klse_microcap_database.csv"
        self.sectors_file = "KLSE_System/klse_sectors.json"
        self.analysis_file = "KLSE_System/klse_microcap_analysis.csv"
        self.universe_file = "KLSE_System/klse_stock_universe.json"
        
        # Micro-cap criteria
        self.MICROCAP_THRESHOLD_MYR = 300_000_000  # 300M MYR
        self.MIN_PRICE_MYR = 0.05  # Minimum price to avoid penny stocks
        self.MIN_VOLUME = 10000     # Minimum daily volume
        self.MIN_MARKET_CAP_MYR = 50_000_000  # 50M MYR minimum
        
        # Malaysian stock sectors
        self.SECTORS = {
            "Technology": ["Software", "Hardware", "Telecommunications", "E-commerce"],
            "Industrial": ["Manufacturing", "Construction", "Engineering", "Transportation"],
            "Consumer": ["Retail", "Food & Beverage", "Consumer Goods", "Automotive"],
            "Healthcare": ["Pharmaceuticals", "Medical Equipment", "Healthcare Services"],
            "Financial": ["Banks", "Insurance", "Investment", "REIT"],
            "Energy": ["Oil & Gas", "Renewable Energy", "Utilities"],
            "Materials": ["Chemicals", "Mining", "Steel", "Paper"],
            "Real Estate": ["Property Development", "Property Investment"],
            "Agriculture": ["Palm Oil", "Rubber", "Food Production"],
            "Tourism": ["Hotels", "Entertainment", "Travel"]
        }
        
        # Known Malaysian micro-cap stocks for seed data
        self.SEED_STOCKS = [
            # Technology
            {"code": "0090", "name": "NetX Holdings", "sector": "Technology", "subsector": "Software"},
            {"code": "0176", "name": "Fintec Global", "sector": "Technology", "subsector": "Software"},
            {"code": "0066", "name": "PUC Berhad", "sector": "Technology", "subsector": "Telecommunications"},
            {"code": "5027", "name": "Genetec Technology", "sector": "Technology", "subsector": "Hardware"},
            
            # Industrial
            {"code": "4723", "name": "JAKS Resources", "sector": "Industrial", "subsector": "Construction"},
            {"code": "7204", "name": "Zecon Berhad", "sector": "Industrial", "subsector": "Construction"},
            {"code": "5284", "name": "Pohuat Berhad", "sector": "Industrial", "subsector": "Manufacturing"},
            {"code": "7157", "name": "MKH Berhad", "sector": "Industrial", "subsector": "Engineering"},
            
            # Consumer
            {"code": "3816", "name": "Luxchem Corporation", "sector": "Consumer", "subsector": "Consumer Goods"},
            {"code": "7943", "name": "Trive Property Group", "sector": "Consumer", "subsector": "Retail"},
            {"code": "5230", "name": "Lebtech Berhad", "sector": "Consumer", "subsector": "Food & Beverage"},
            
            # Materials
            {"code": "5161", "name": "Poh Huat Resources", "sector": "Materials", "subsector": "Manufacturing"},
            {"code": "7595", "name": "Vsolar Group", "sector": "Materials", "subsector": "Manufacturing"},
            
            # Healthcare
            {"code": "7078", "name": "Careplus Group", "sector": "Healthcare", "subsector": "Healthcare Services"},
            {"code": "0167", "name": "Pharmaniaga", "sector": "Healthcare", "subsector": "Pharmaceuticals"},
            
            # Energy
            {"code": "5166", "name": "Sealink International", "sector": "Energy", "subsector": "Oil & Gas"},
            {"code": "5249", "name": "Reach Energy", "sector": "Energy", "subsector": "Renewable Energy"}
        ]
        
        # Ensure directories exist
        os.makedirs("KLSE_System", exist_ok=True)
        
        logger.info("KLSE Micro-Cap Database initialized")
    
    def _get_stock_data(self, stock_code: str) -> Optional[Dict]:
        """Get comprehensive stock data"""
        ticker = f"{stock_code}.KL"
        
        if ENHANCED_DATA_AVAILABLE and self.data_fetcher:
            # Use enhanced data fetcher
            return self.data_fetcher.get_stock_price(stock_code)
        elif yf:
            # Fallback to yfinance
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period="5d")
                
                if hist.empty:
                    return None
                
                return {
                    'price': round(hist['Close'].iloc[-1], 3),
                    'volume': hist['Volume'].iloc[-1] if 'Volume' in hist else 0,
                    'market_cap': info.get('marketCap', 0),
                    'currency': 'MYR',
                    'source': 'yfinance',
                    'data_available': True,
                    'full_name': info.get('longName', ''),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', '')
                }
            except Exception as e:
                logger.warning(f"Error fetching data for {ticker}: {e}")
                return None
        else:
            return None
    
    def _is_microcap(self, market_cap: float, price: float, volume: float) -> bool:
        """Check if stock meets micro-cap criteria"""
        # Handle None values
        if market_cap is None or price is None or volume is None:
            return False
        
        return (
            self.MIN_MARKET_CAP_MYR <= market_cap <= self.MICROCAP_THRESHOLD_MYR and
            price >= self.MIN_PRICE_MYR and
            volume >= self.MIN_VOLUME
        )
    
    def build_seed_database(self) -> bool:
        """Build initial database from seed stocks"""
        logger.info("Building micro-cap database from seed stocks...")
        
        database_records = []
        analysis_records = []
        
        for i, stock in enumerate(self.SEED_STOCKS):
            logger.info(f"Processing {stock['code']} ({i+1}/{len(self.SEED_STOCKS)}): {stock['name']}")
            
            # Get stock data
            stock_data = self._get_stock_data(stock['code'])
            
            if not stock_data:
                logger.warning(f"No data available for {stock['code']}")
                continue
            
            # Extract data
            price = stock_data['price']
            volume = stock_data.get('volume', 0)
            market_cap = stock_data.get('market_cap', 0)
            
            # Check micro-cap criteria
            is_microcap = self._is_microcap(market_cap, price, volume)
            
            # Create database record
            record = {
                'stock_code': stock['code'],
                'ticker': f"{stock['code']}.KL",
                'company_name': stock['name'],
                'sector': stock['sector'],
                'subsector': stock['subsector'],
                'current_price': price,
                'market_cap_myr': market_cap,
                'avg_volume': volume,
                'is_microcap': is_microcap,
                'meets_criteria': is_microcap,
                'currency': 'MYR',
                'last_updated': datetime.now().isoformat(),
                'data_source': stock_data.get('source', 'unknown')
            }
            
            database_records.append(record)
            
            # Create analysis record
            analysis = {
                'stock_code': stock['code'],
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'price': price,
                'market_cap': market_cap,
                'volume': volume,
                'microcap_score': self._calculate_microcap_score(price, market_cap, volume),
                'liquidity_score': self._calculate_liquidity_score(volume, price),
                'size_score': self._calculate_size_score(market_cap),
                'overall_score': 0  # Will calculate after individual scores
            }
            
            # Calculate overall score
            analysis['overall_score'] = (
                analysis['microcap_score'] * 0.4 +
                analysis['liquidity_score'] * 0.3 +
                analysis['size_score'] * 0.3
            )
            
            analysis_records.append(analysis)
            
            # Small delay to avoid overwhelming APIs
            time.sleep(0.1)
        
        # Save database
        if database_records:
            db_df = pd.DataFrame(database_records)
            db_df.to_csv(self.database_file, index=False)
            logger.info(f"Saved {len(database_records)} stocks to database")
            
            # Save analysis
            analysis_df = pd.DataFrame(analysis_records)
            analysis_df.to_csv(self.analysis_file, index=False)
            logger.info(f"Saved analysis for {len(analysis_records)} stocks")
            
            # Save sectors
            with open(self.sectors_file, 'w') as f:
                json.dump(self.SECTORS, f, indent=2)
            
            return True
        else:
            logger.error("No valid stocks found for database")
            return False
    
    def _calculate_microcap_score(self, price: float, market_cap: float, volume: float) -> float:
        """Calculate microcap suitability score (0-100)"""
        score = 0
        
        # Price score (prefer stocks between 0.10 - 2.00 MYR)
        if 0.10 <= price <= 2.00:
            score += 30
        elif 0.05 <= price < 0.10 or 2.00 < price <= 5.00:
            score += 20
        elif price > 5.00:
            score += 10
        
        # Market cap score (prefer smaller micro-caps)
        if market_cap <= 100_000_000:  # < 100M MYR
            score += 40
        elif market_cap <= 200_000_000:  # 100-200M MYR
            score += 30
        elif market_cap <= 300_000_000:  # 200-300M MYR
            score += 20
        
        # Volume score (prefer adequate liquidity)
        if volume >= 100_000:
            score += 30
        elif volume >= 50_000:
            score += 20
        elif volume >= 10_000:
            score += 10
        
        return min(score, 100)
    
    def _calculate_liquidity_score(self, volume: float, price: float) -> float:
        """Calculate liquidity score (0-100)"""
        daily_value = volume * price
        
        if daily_value >= 100_000:  # >100K MYR daily
            return 100
        elif daily_value >= 50_000:   # 50-100K MYR daily
            return 80
        elif daily_value >= 20_000:   # 20-50K MYR daily
            return 60
        elif daily_value >= 5_000:    # 5-20K MYR daily
            return 40
        else:
            return 20
    
    def _calculate_size_score(self, market_cap: float) -> float:
        """Calculate size score for micro-cap suitability (0-100)"""
        if market_cap <= 50_000_000:    # < 50M MYR (very small)
            return 100
        elif market_cap <= 100_000_000:  # 50-100M MYR
            return 80
        elif market_cap <= 200_000_000:  # 100-200M MYR
            return 60
        elif market_cap <= 300_000_000:  # 200-300M MYR
            return 40
        else:
            return 20
    
    def load_database(self) -> pd.DataFrame:
        """Load the micro-cap database"""
        if not os.path.exists(self.database_file):
            logger.warning("Database file not found - run build_seed_database() first")
            return pd.DataFrame()
        
        return pd.read_csv(self.database_file)
    
    def get_top_microcaps(self, limit: int = 10, sector: str = None, 
                         min_score: float = 60.0) -> pd.DataFrame:
        """Get top-rated micro-cap stocks"""
        # Load analysis data
        if not os.path.exists(self.analysis_file):
            logger.warning("Analysis file not found")
            return pd.DataFrame()
        
        analysis_df = pd.read_csv(self.analysis_file)
        database_df = self.load_database()
        
        if analysis_df.empty or database_df.empty:
            return pd.DataFrame()
        
        # Merge with database info
        merged = analysis_df.merge(database_df, on='stock_code', how='inner')
        
        # Filter by criteria
        filtered = merged[
            (merged['meets_criteria'] == True) &
            (merged['overall_score'] >= min_score)
        ]
        
        # Filter by sector if specified
        if sector:
            filtered = filtered[filtered['sector'] == sector]
        
        # Sort by overall score
        top_stocks = filtered.sort_values('overall_score', ascending=False).head(limit)
        
        # Select relevant columns
        result_columns = [
            'stock_code', 'ticker', 'company_name', 'sector', 'subsector',
            'current_price', 'market_cap_myr', 'avg_volume',
            'overall_score', 'microcap_score', 'liquidity_score', 'size_score',
            'last_updated'
        ]
        
        return top_stocks[result_columns]
    
    def get_sector_analysis(self) -> Dict[str, any]:
        """Get sector-wise analysis of micro-cap stocks"""
        database_df = self.load_database()
        
        if database_df.empty:
            return {}
        
        # Filter microcaps only
        microcaps = database_df[database_df['meets_criteria'] == True]
        
        sector_analysis = {}
        
        for sector in microcaps['sector'].unique():
            sector_stocks = microcaps[microcaps['sector'] == sector]
            
            sector_analysis[sector] = {
                'total_stocks': len(sector_stocks),
                'avg_market_cap': sector_stocks['market_cap_myr'].mean(),
                'avg_price': sector_stocks['current_price'].mean(),
                'avg_volume': sector_stocks['avg_volume'].mean(),
                'total_market_cap': sector_stocks['market_cap_myr'].sum(),
                'stocks': sector_stocks[['stock_code', 'company_name', 'current_price', 'market_cap_myr']].to_dict('records')
            }
        
        return sector_analysis
    
    def update_stock_data(self, stock_codes: List[str] = None) -> bool:
        """Update stock data for specified stocks or all stocks in database"""
        database_df = self.load_database()
        
        if database_df.empty:
            logger.error("No database found to update")
            return False
        
        if stock_codes is None:
            stock_codes = database_df['stock_code'].tolist()
        
        logger.info(f"Updating data for {len(stock_codes)} stocks")
        
        updated_records = []
        
        for i, stock_code in enumerate(stock_codes):
            logger.info(f"Updating {stock_code} ({i+1}/{len(stock_codes)})")
            
            # Get current data
            stock_data = self._get_stock_data(stock_code)
            
            if stock_data:
                # Find existing record
                existing = database_df[database_df['stock_code'] == stock_code]
                
                if not existing.empty:
                    record = existing.iloc[0].to_dict()
                    
                    # Update with new data
                    record['current_price'] = stock_data['price']
                    record['market_cap_myr'] = stock_data.get('market_cap', record['market_cap_myr'])
                    record['avg_volume'] = stock_data.get('volume', record['avg_volume'])
                    record['last_updated'] = datetime.now().isoformat()
                    record['data_source'] = stock_data.get('source', 'unknown')
                    
                    # Recalculate criteria
                    record['is_microcap'] = self._is_microcap(
                        record['market_cap_myr'], 
                        record['current_price'], 
                        record['avg_volume']
                    )
                    record['meets_criteria'] = record['is_microcap']
                    
                    updated_records.append(record)
            
            time.sleep(0.1)  # Rate limiting
        
        if updated_records:
            # Update database
            updated_df = pd.DataFrame(updated_records)
            
            # Merge with unchanged records
            # Every record can be in stock_codes, leaving nothing unchanged -
            # a column-only frame, which pandas no longer concatenates cleanly.
            unchanged = database_df[~database_df['stock_code'].isin(stock_codes)]
            final_df = append_row(unchanged, updated_df)
            
            # Save updated database
            final_df.to_csv(self.database_file, index=False)
            logger.info(f"Updated {len(updated_records)} stock records")
            
            return True
        else:
            logger.error("No stocks were successfully updated")
            return False
    
    def generate_stock_universe(self) -> Dict[str, any]:
        """Generate comprehensive stock universe for AI selection"""
        database_df = self.load_database()
        analysis_df = pd.read_csv(self.analysis_file) if os.path.exists(self.analysis_file) else pd.DataFrame()
        
        if database_df.empty:
            return {}
        
        # Merge data
        if not analysis_df.empty:
            merged = database_df.merge(analysis_df, on='stock_code', how='left')
        else:
            merged = database_df
        
        # Filter valid microcaps
        microcaps = merged[merged['meets_criteria'] == True]
        
        # Create universe
        universe = {
            'generated_date': datetime.now().isoformat(),
            'total_microcaps': len(microcaps),
            'selection_criteria': {
                'max_market_cap_myr': self.MICROCAP_THRESHOLD_MYR,
                'min_market_cap_myr': self.MIN_MARKET_CAP_MYR,
                'min_price_myr': self.MIN_PRICE_MYR,
                'min_volume': self.MIN_VOLUME
            },
            'sectors': {},
            'top_picks': {},
            'all_stocks': {}
        }
        
        # Sector breakdown
        for sector in microcaps['sector'].unique():
            sector_stocks = microcaps[microcaps['sector'] == sector]
            universe['sectors'][sector] = {
                'count': len(sector_stocks),
                'stocks': sector_stocks['stock_code'].tolist()
            }
        
        # Top picks by score (if available)
        if 'overall_score' in microcaps.columns:
            top_picks = microcaps.sort_values('overall_score', ascending=False).head(20)
            universe['top_picks'] = {
                'by_overall_score': top_picks[['stock_code', 'company_name', 'overall_score']].to_dict('records'),
                'by_liquidity': microcaps.sort_values('liquidity_score', ascending=False).head(10)[['stock_code', 'company_name', 'liquidity_score']].to_dict('records'),
                'by_microcap_score': microcaps.sort_values('microcap_score', ascending=False).head(10)[['stock_code', 'company_name', 'microcap_score']].to_dict('records')
            }
        
        # All stocks summary
        for _, stock in microcaps.iterrows():
            universe['all_stocks'][stock['stock_code']] = {
                'name': stock['company_name'],
                'sector': stock['sector'],
                'subsector': stock.get('subsector', ''),
                'price': stock['current_price'],
                'market_cap': stock['market_cap_myr'],
                'volume': stock['avg_volume'],
                'score': stock.get('overall_score', 0)
            }
        
        # Save universe
        with open(self.universe_file, 'w') as f:
            json.dump(universe, f, indent=2)
        
        logger.info(f"Generated stock universe with {len(microcaps)} micro-cap stocks")
        return universe
    
    def get_ai_recommendations(self, num_recommendations: int = 5, 
                              exclude_sectors: List[str] = None) -> List[Dict]:
        """Get AI-optimized stock recommendations"""
        database_df = self.load_database()
        analysis_df = pd.read_csv(self.analysis_file) if os.path.exists(self.analysis_file) else pd.DataFrame()
        
        if database_df.empty:
            return []
        
        # Merge data
        if not analysis_df.empty:
            merged = database_df.merge(analysis_df, on='stock_code', how='left')
        else:
            merged = database_df
        
        # Filter criteria
        filtered = merged[merged['meets_criteria'] == True]
        
        # Exclude sectors if specified
        if exclude_sectors:
            filtered = filtered[~filtered['sector'].isin(exclude_sectors)]
        
        # Score and rank
        if 'overall_score' in filtered.columns:
            # Use calculated scores
            recommendations = filtered.sort_values('overall_score', ascending=False).head(num_recommendations)
        else:
            # Use basic market cap ranking
            recommendations = filtered.sort_values('market_cap_myr', ascending=True).head(num_recommendations)
        
        # Format recommendations
        result = []
        for _, stock in recommendations.iterrows():
            rec = {
                'stock_code': stock['stock_code'],
                'ticker': stock['ticker'],
                'company_name': stock['company_name'],
                'sector': stock['sector'],
                'subsector': stock.get('subsector', ''),
                'current_price': stock['current_price'],
                'market_cap_myr': stock['market_cap_myr'],
                'volume': stock['avg_volume'],
                'score': stock.get('overall_score', 0),
                'recommendation_reason': self._generate_recommendation_reason(stock)
            }
            result.append(rec)
        
        return result
    
    def _generate_recommendation_reason(self, stock: pd.Series) -> str:
        """Generate AI recommendation reasoning"""
        reasons = []
        
        # Market cap based
        market_cap = stock['market_cap_myr']
        if market_cap < 100_000_000:
            reasons.append("Small market cap offers high growth potential")
        elif market_cap < 200_000_000:
            reasons.append("Mid-tier micro-cap with balanced risk/reward")
        
        # Price based
        price = stock['current_price']
        if price < 0.50:
            reasons.append("Low share price allows for large position sizes")
        elif price < 1.00:
            reasons.append("Moderate share price with room for appreciation")
        
        # Volume based
        volume = stock['avg_volume']
        if volume > 50_000:
            reasons.append("Good liquidity for entry/exit")
        
        # Sector based
        sector = stock['sector']
        if sector == 'Technology':
            reasons.append("Technology sector growth exposure")
        elif sector == 'Industrial':
            reasons.append("Industrial sector stability")
        elif sector == 'Healthcare':
            reasons.append("Defensive healthcare exposure")
        
        return "; ".join(reasons) if reasons else "Meets micro-cap criteria"

def main():
    """Main database management script"""
    parser = argparse.ArgumentParser(description='KLSE Micro-Cap Database')
    parser.add_argument('--action', choices=['build', 'update', 'analyze', 'recommend', 'universe'], 
                       default='build', help='Action to perform')
    parser.add_argument('--alpha-vantage-key', help='Alpha Vantage API key')
    parser.add_argument('--sector', help='Filter by sector')
    parser.add_argument('--limit', type=int, default=10, help='Number of results')
    
    args = parser.parse_args()
    
    # Initialize database
    db = KLSEMicroCapDatabase(alpha_vantage_key=args.alpha_vantage_key)
    
    if args.action == 'build':
        print("🏗️  Building KLSE micro-cap database...")
        success = db.build_seed_database()
        if success:
            print("✅ Database built successfully")
        else:
            print("❌ Failed to build database")
    
    elif args.action == 'update':
        print("🔄 Updating stock data...")
        success = db.update_stock_data()
        if success:
            print("✅ Stock data updated")
        else:
            print("❌ Failed to update data")
    
    elif args.action == 'analyze':
        print("📊 Analyzing micro-cap stocks...")
        
        # Get top stocks
        top_stocks = db.get_top_microcaps(limit=args.limit, sector=args.sector)
        
        if not top_stocks.empty:
            print(f"\n🎯 Top {len(top_stocks)} Micro-Cap Stocks:")
            print("-" * 80)
            for _, stock in top_stocks.iterrows():
                print(f"{stock['stock_code']:>4} | {stock['company_name']:<25} | "
                      f"{stock['sector']:<12} | {stock['current_price']:>6.3f} MYR | "
                      f"{stock['market_cap_myr']/1_000_000:>6.1f}M | Score: {stock['overall_score']:>5.1f}")
        
        # Sector analysis
        sector_analysis = db.get_sector_analysis()
        print(f"\n📈 Sector Analysis:")
        print("-" * 50)
        for sector, data in sector_analysis.items():
            print(f"{sector:<15}: {data['total_stocks']} stocks, "
                  f"Avg Cap: {data['avg_market_cap']/1_000_000:.1f}M MYR")
    
    elif args.action == 'recommend':
        print("🤖 AI Stock Recommendations...")
        recommendations = db.get_ai_recommendations(num_recommendations=args.limit)
        
        if recommendations:
            print(f"\n🎯 Top {len(recommendations)} AI Recommendations:")
            print("-" * 80)
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec['stock_code']} - {rec['company_name']}")
                print(f"   Sector: {rec['sector']} | Price: {rec['current_price']:.3f} MYR")
                print(f"   Market Cap: {rec['market_cap_myr']/1_000_000:.1f}M MYR")
                print(f"   Reason: {rec['recommendation_reason']}")
                print()
    
    elif args.action == 'universe':
        print("🌌 Generating stock universe...")
        universe = db.generate_stock_universe()
        
        if universe:
            print(f"✅ Generated universe with {universe['total_microcaps']} micro-cap stocks")
            print(f"\n📊 Sector Distribution:")
            for sector, data in universe['sectors'].items():
                print(f"   {sector:<15}: {data['count']} stocks")

if __name__ == "__main__":
    main()
