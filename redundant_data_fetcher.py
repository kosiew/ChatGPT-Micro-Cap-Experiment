#!/usr/bin/env python3
"""
Redundant Malaysian Stock Data Fetcher
Implements fallback data sources for robust KLSE data access
"""

import yfinance as yf
import requests
import json
import time
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KLSEDataFetcher:
    """
    Robust data fetcher for Malaysian stocks with multiple fallback sources
    """
    
    def __init__(self, alpha_vantage_key: Optional[str] = None):
        self.alpha_vantage_key = alpha_vantage_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Track data source performance
        self.source_stats = {
            'yfinance': {'attempts': 0, 'successes': 0, 'last_used': None},
            'yahoo_api': {'attempts': 0, 'successes': 0, 'last_used': None},
            'alpha_vantage': {'attempts': 0, 'successes': 0, 'last_used': None}
        }
    
    def get_stock_price(self, ticker: str, retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Get stock price with automatic fallback between data sources
        
        Args:
            ticker: Malaysian stock code (e.g., "1155" for Maybank)
            retries: Number of retry attempts per source
            
        Returns:
            Dict with price data or None if all sources fail
        """
        
        # Ensure .KL suffix for Malaysian stocks
        klse_ticker = f"{ticker}.KL" if not ticker.endswith('.KL') else ticker
        
        # Try data sources in order of reliability
        data_sources = [
            ('yfinance', self._fetch_yfinance),
            ('yahoo_api', self._fetch_yahoo_api),
        ]
        
        # Add Alpha Vantage if API key is available
        if self.alpha_vantage_key:
            data_sources.append(('alpha_vantage', self._fetch_alpha_vantage))
        
        for source_name, fetch_function in data_sources:
            for attempt in range(retries):
                try:
                    self.source_stats[source_name]['attempts'] += 1
                    
                    logger.info(f"Attempting {source_name} for {klse_ticker} (attempt {attempt + 1})")
                    
                    result = fetch_function(klse_ticker)
                    
                    if result and self._validate_price_data(result):
                        self.source_stats[source_name]['successes'] += 1
                        self.source_stats[source_name]['last_used'] = datetime.now()
                        
                        logger.info(f"✅ Success: {source_name} returned {result['price']} {result['currency']}")
                        
                        # Add metadata
                        result['source'] = source_name
                        result['ticker'] = klse_ticker
                        result['fetch_time'] = datetime.now().isoformat()
                        
                        return result
                    
                except Exception as e:
                    logger.warning(f"❌ {source_name} attempt {attempt + 1} failed: {e}")
                    
                time.sleep(1)  # Brief pause between attempts
        
        logger.error(f"🚨 All data sources failed for {klse_ticker}")
        return None
    
    def _fetch_yfinance(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch data using yfinance library"""
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        info = stock.info
        
        if hist.empty:
            return None
        
        return {
            'price': round(hist['Close'].iloc[-1], 3),
            'currency': info.get('currency', 'MYR'),
            'volume': hist['Volume'].iloc[-1] if 'Volume' in hist else None,
            'market_cap': info.get('marketCap', None),
            'data_timestamp': hist.index[-1].isoformat()
        }
    
    def _fetch_yahoo_api(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch data using direct Yahoo Finance API"""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        chart_result = data.get('chart', {}).get('result', [])
        
        if not chart_result:
            return None
        
        meta = chart_result[0].get('meta', {})
        
        return {
            'price': round(meta.get('regularMarketPrice', 0), 3),
            'currency': meta.get('currency', 'MYR'),
            'volume': meta.get('regularMarketVolume', None),
            'market_cap': None,  # Not available in this endpoint
            'data_timestamp': datetime.fromtimestamp(meta.get('regularMarketTime', 0)).isoformat()
        }
    
    def _fetch_alpha_vantage(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch data using Alpha Vantage API"""
        if not self.alpha_vantage_key:
            return None
        
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': ticker,
            'apikey': self.alpha_vantage_key
        }
        
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        quote_data = data.get('Global Quote', {})
        
        if not quote_data:
            return None
        
        price_str = quote_data.get('05. price', '0')
        
        return {
            'price': round(float(price_str), 3),
            'currency': 'MYR',  # Assume MYR for Malaysian stocks
            'volume': quote_data.get('06. volume', None),
            'market_cap': None,
            'data_timestamp': quote_data.get('07. latest trading day', '')
        }
    
    def _validate_price_data(self, data: Dict[str, Any]) -> bool:
        """Validate that price data is reasonable"""
        if not data or 'price' not in data:
            return False
        
        price = data['price']
        
        # Basic sanity checks
        if not isinstance(price, (int, float)) or price <= 0:
            return False
        
        # Malaysian stock price ranges (very broad check)
        if price > 1000:  # Extremely high for Malaysian stocks
            logger.warning(f"Suspicious high price: {price}")
            return False
        
        return True
    
    def get_multiple_stocks(self, tickers: list) -> Dict[str, Any]:
        """
        Fetch data for multiple stocks efficiently
        
        Args:
            tickers: List of Malaysian stock codes
            
        Returns:
            Dict mapping tickers to their data
        """
        results = {}
        
        logger.info(f"Fetching data for {len(tickers)} stocks")
        
        for ticker in tickers:
            data = self.get_stock_price(ticker)
            results[ticker] = data
            time.sleep(0.5)  # Rate limiting
        
        # Log summary
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"Successfully fetched {successful}/{len(tickers)} stocks")
        
        return results
    
    def get_source_performance(self) -> Dict[str, Any]:
        """Get performance statistics for all data sources"""
        performance = {}
        
        for source, stats in self.source_stats.items():
            if stats['attempts'] > 0:
                success_rate = (stats['successes'] / stats['attempts']) * 100
                performance[source] = {
                    'success_rate': round(success_rate, 1),
                    'attempts': stats['attempts'],
                    'successes': stats['successes'],
                    'last_used': stats['last_used'].isoformat() if stats['last_used'] else None
                }
        
        return performance
    
    def test_all_sources(self, test_ticker: str = "1155") -> Dict[str, Any]:
        """
        Test all available data sources with a known stock
        
        Args:
            test_ticker: Stock to test with (default: Maybank)
            
        Returns:
            Dict with test results for each source
        """
        test_results = {}
        klse_ticker = f"{test_ticker}.KL"
        
        logger.info(f"Testing all data sources with {klse_ticker}")
        
        # Test yfinance
        try:
            result = self._fetch_yfinance(klse_ticker)
            test_results['yfinance'] = {
                'status': 'success' if result else 'no_data',
                'data': result
            }
        except Exception as e:
            test_results['yfinance'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Test Yahoo API
        try:
            result = self._fetch_yahoo_api(klse_ticker)
            test_results['yahoo_api'] = {
                'status': 'success' if result else 'no_data',
                'data': result
            }
        except Exception as e:
            test_results['yahoo_api'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Test Alpha Vantage if key available
        if self.alpha_vantage_key:
            try:
                result = self._fetch_alpha_vantage(klse_ticker)
                test_results['alpha_vantage'] = {
                    'status': 'success' if result else 'no_data',
                    'data': result
                }
            except Exception as e:
                test_results['alpha_vantage'] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            test_results['alpha_vantage'] = {
                'status': 'no_api_key',
                'data': None
            }
        
        return test_results

def demo_redundant_fetching():
    """Demonstrate the redundant data fetching system"""
    print("🚀 Demonstrating Redundant KLSE Data Fetching")
    print("=" * 60)
    
    # Initialize fetcher (without Alpha Vantage key for demo)
    fetcher = KLSEDataFetcher()
    
    # Test with our known working stocks
    test_stocks = ["1155", "4723", "0090"]  # Maybank, JAKS, NETX
    
    print("🔍 Testing individual stock fetching...")
    for ticker in test_stocks:
        print(f"\nFetching {ticker}...")
        data = fetcher.get_stock_price(ticker)
        
        if data:
            print(f"✅ {ticker}: {data['price']} {data['currency']} (via {data['source']})")
        else:
            print(f"❌ {ticker}: Failed to fetch data")
    
    print(f"\n📊 Batch fetching test...")
    batch_results = fetcher.get_multiple_stocks(test_stocks)
    
    successful_batch = sum(1 for v in batch_results.values() if v is not None)
    print(f"Batch success rate: {successful_batch}/{len(test_stocks)}")
    
    print(f"\n📈 Data source performance:")
    performance = fetcher.get_source_performance()
    for source, stats in performance.items():
        print(f"   {source}: {stats['success_rate']}% success ({stats['successes']}/{stats['attempts']})")
    
    print(f"\n🧪 Testing all sources with Maybank...")
    test_results = fetcher.test_all_sources("1155")
    
    for source, result in test_results.items():
        status = result['status']
        if status == 'success':
            data = result['data']
            print(f"✅ {source}: {data['price']} {data['currency']}")
        elif status == 'no_api_key':
            print(f"🔑 {source}: API key required")
        else:
            print(f"❌ {source}: {status}")

if __name__ == "__main__":
    demo_redundant_fetching()
    
    print(f"\n💡 USAGE RECOMMENDATIONS:")
    print(f"   1. Use KLSEDataFetcher.get_stock_price() for single stocks")
    print(f"   2. Use get_multiple_stocks() for batch processing") 
    print(f"   3. Monitor source performance with get_source_performance()")
    print(f"   4. Set up Alpha Vantage API key for additional redundancy")
    print(f"   5. Implement this in your trading scripts for reliability")
