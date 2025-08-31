#!/usr/bin/env python3
"""
Alternative Malaysian Stock Data Sources Investigation
Tests multiple data providers for backup/redundancy options
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import re

# Test stocks for consistency checking
TEST_STOCKS = {
    "MAYBANK": "1155",    # Major bank - good for testing
    "JAKS": "4723",       # Micro-cap we confirmed works
    "NETX": "0090",       # Another confirmed micro-cap
}

class DataSourceTester:
    def __init__(self):
        self.results = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def test_investing_com(self):
        """Test Investing.com scraping approach"""
        print("🔍 Testing Investing.com Data Access")
        print("-" * 50)
        
        results = {}
        
        try:
            # Test general Malaysia stocks page
            url = "https://www.investing.com/equities/malaysia"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                print("✅ Investing.com Malaysia page accessible")
                
                # Look for stock data patterns
                content = response.text.lower()
                stock_mentions = []
                
                for name, code in TEST_STOCKS.items():
                    if name.lower() in content:
                        stock_mentions.append(name)
                
                print(f"   Found stock mentions: {stock_mentions}")
                
                # Check if we can find price patterns
                price_pattern = r'\d+\.\d{2,3}'
                prices_found = len(re.findall(price_pattern, content))
                print(f"   Price-like patterns found: {prices_found}")
                
                results['status'] = 'accessible'
                results['stock_mentions'] = len(stock_mentions)
                results['price_patterns'] = prices_found
                
            else:
                print(f"❌ HTTP {response.status_code}")
                results['status'] = f'error_{response.status_code}'
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results['status'] = f'error_{str(e)[:50]}'
        
        self.results['investing_com'] = results
        return results
    
    def test_yahoo_finance_alternatives(self):
        """Test different Yahoo Finance API endpoints"""
        print("\n🔍 Testing Yahoo Finance Alternative Endpoints")
        print("-" * 50)
        
        results = {}
        
        # Test different API endpoints
        endpoints = {
            'chart_api': 'https://query1.finance.yahoo.com/v8/finance/chart/{}.KL',
            'quote_api': 'https://query1.finance.yahoo.com/v7/finance/quote?symbols={}.KL',
            'options_api': 'https://query1.finance.yahoo.com/v7/finance/options/{}.KL'
        }
        
        test_stock = "1155"  # Maybank
        
        for endpoint_name, url_template in endpoints.items():
            try:
                url = url_template.format(test_stock)
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if endpoint_name == 'chart_api':
                        chart_result = data.get('chart', {}).get('result', [])
                        if chart_result:
                            meta = chart_result[0].get('meta', {})
                            current_price = meta.get('regularMarketPrice', 'N/A')
                            currency = meta.get('currency', 'N/A')
                            print(f"✅ {endpoint_name}: {current_price} {currency}")
                            results[endpoint_name] = {'status': 'working', 'price': current_price, 'currency': currency}
                        else:
                            print(f"❌ {endpoint_name}: No chart data")
                            results[endpoint_name] = {'status': 'no_data'}
                    
                    elif endpoint_name == 'quote_api':
                        quote_result = data.get('quoteResponse', {}).get('result', [])
                        if quote_result:
                            quote = quote_result[0]
                            price = quote.get('regularMarketPrice', 'N/A')
                            currency = quote.get('currency', 'N/A')
                            print(f"✅ {endpoint_name}: {price} {currency}")
                            results[endpoint_name] = {'status': 'working', 'price': price, 'currency': currency}
                        else:
                            print(f"❌ {endpoint_name}: No quote data")
                            results[endpoint_name] = {'status': 'no_data'}
                    
                    elif endpoint_name == 'options_api':
                        options_result = data.get('optionChain', {}).get('result', [])
                        if options_result:
                            print(f"✅ {endpoint_name}: Options data available")
                            results[endpoint_name] = {'status': 'working'}
                        else:
                            print(f"⚠️  {endpoint_name}: No options (normal for many stocks)")
                            results[endpoint_name] = {'status': 'no_options'}
                
                else:
                    print(f"❌ {endpoint_name}: HTTP {response.status_code}")
                    results[endpoint_name] = {'status': f'error_{response.status_code}'}
                    
            except Exception as e:
                print(f"❌ {endpoint_name}: {str(e)[:50]}")
                results[endpoint_name] = {'status': f'error_{str(e)[:50]}'}
            
            time.sleep(0.5)  # Rate limiting
        
        self.results['yahoo_alternatives'] = results
        return results
    
    def test_bursa_malaysia_api(self):
        """Test if Bursa Malaysia has any accessible APIs"""
        print("\n🔍 Testing Bursa Malaysia Official Sources")
        print("-" * 50)
        
        results = {}
        
        # Test Bursa Malaysia website
        urls_to_test = [
            "https://www.bursamalaysia.com/",
            "https://www.bursamalaysia.com/market_information/equities_prices",
            "https://api.bursamalaysia.com/",  # Speculative API endpoint
        ]
        
        for url in urls_to_test:
            try:
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ {url}: Accessible")
                    
                    # Look for API hints or data patterns
                    content = response.text.lower()
                    
                    api_hints = []
                    if 'api' in content:
                        api_hints.append('api_mentioned')
                    if 'json' in content:
                        api_hints.append('json_data')
                    if 'real-time' in content or 'realtime' in content:
                        api_hints.append('realtime_data')
                    
                    results[url] = {
                        'status': 'accessible',
                        'content_size': len(content),
                        'api_hints': api_hints
                    }
                    
                    if api_hints:
                        print(f"   🔍 Found: {', '.join(api_hints)}")
                else:
                    print(f"❌ {url}: HTTP {response.status_code}")
                    results[url] = {'status': f'error_{response.status_code}'}
                    
            except Exception as e:
                print(f"❌ {url}: {str(e)[:50]}")
                results[url] = {'status': f'error_{str(e)[:50]}'}
            
            time.sleep(1)  # Be respectful
        
        self.results['bursa_official'] = results
        return results
    
    def test_alpha_vantage_potential(self):
        """Test Alpha Vantage's Malaysian coverage potential"""
        print("\n🔍 Testing Alpha Vantage Potential")
        print("-" * 50)
        
        # Note: This requires an API key, so we'll just test the structure
        print("📝 Alpha Vantage Analysis:")
        print("   - Requires free API key from alphavantage.co")
        print("   - Known to support some international markets")
        print("   - API format: https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=1155.KL&apikey=YOUR_KEY")
        print("   - Would need testing with actual API key")
        
        # Test if their demo endpoint is accessible
        demo_url = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo"
        
        try:
            response = self.session.get(demo_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'Global Quote' in data:
                    print("✅ Alpha Vantage demo endpoint working")
                    print("   - API structure confirmed functional")
                    self.results['alpha_vantage'] = {'status': 'demo_working', 'needs_api_key': True}
                else:
                    print("⚠️  Alpha Vantage demo returned unexpected format")
                    self.results['alpha_vantage'] = {'status': 'demo_unusual_format'}
            else:
                print(f"❌ Alpha Vantage demo: HTTP {response.status_code}")
                self.results['alpha_vantage'] = {'status': f'demo_error_{response.status_code}'}
        except Exception as e:
            print(f"❌ Alpha Vantage demo: {e}")
            self.results['alpha_vantage'] = {'status': f'demo_error_{str(e)[:50]}'}
    
    def test_financial_modeling_prep(self):
        """Test Financial Modeling Prep API potential"""
        print("\n🔍 Testing Financial Modeling Prep")
        print("-" * 50)
        
        # Test their free tier
        base_url = "https://financialmodelingprep.com/api/v3/"
        
        # Try some endpoints that might work without API key
        test_endpoints = [
            "search?query=apple",  # General search
            "quote/1155.KL",       # Malaysian stock quote
        ]
        
        for endpoint in test_endpoints:
            try:
                url = base_url + endpoint
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ {endpoint}: Response received")
                        
                        if isinstance(data, list) and len(data) > 0:
                            print(f"   📊 Data points: {len(data)}")
                        elif isinstance(data, dict):
                            print(f"   📊 Data keys: {list(data.keys())[:5]}")
                            
                    except json.JSONDecodeError:
                        print(f"⚠️  {endpoint}: Non-JSON response")
                        
                elif response.status_code == 401:
                    print(f"🔑 {endpoint}: Requires API key")
                else:
                    print(f"❌ {endpoint}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {endpoint}: {str(e)[:50]}")
            
            time.sleep(0.5)
        
        print("📝 Financial Modeling Prep offers free tier with API key")
        print("   - Might support Malaysian stocks (.KL suffix)")
        
    def test_web_scraping_sources(self):
        """Test various web scraping possibilities"""
        print("\n🔍 Testing Web Scraping Sources")
        print("-" * 50)
        
        scraping_targets = {
            "Yahoo Finance MY": "https://finance.yahoo.com/quote/1155.KL",
            "Google Finance": "https://www.google.com/finance/quote/1155:KLSE",
            "MarketWatch": "https://www.marketwatch.com/investing/stock/1155?countrycode=my",
            "Bloomberg": "https://www.bloomberg.com/quote/1155:MK",
        }
        
        for source_name, url in scraping_targets.items():
            try:
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # Look for price indicators
                    price_indicators = 0
                    indicators = ['myr', 'ringgit', 'price', 'quote', '1155', 'maybank']
                    
                    for indicator in indicators:
                        if indicator in content:
                            price_indicators += 1
                    
                    print(f"✅ {source_name}: Accessible (indicators: {price_indicators}/{len(indicators)})")
                    
                    # Check for anti-bot measures
                    anti_bot_signs = []
                    if 'cloudflare' in content:
                        anti_bot_signs.append('cloudflare')
                    if 'captcha' in content:
                        anti_bot_signs.append('captcha')
                    if 'robot' in content:
                        anti_bot_signs.append('robot_check')
                    
                    if anti_bot_signs:
                        print(f"   ⚠️  Anti-bot measures: {', '.join(anti_bot_signs)}")
                    
                else:
                    print(f"❌ {source_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {source_name}: {str(e)[:50]}")
            
            time.sleep(1)  # Be respectful
    
    def generate_redundancy_report(self):
        """Generate comprehensive redundancy assessment"""
        print("\n" + "=" * 60)
        print("📊 DATA SOURCE REDUNDANCY REPORT")
        print("=" * 60)
        
        # Categorize data sources by viability
        viable_sources = []
        potential_sources = []
        problematic_sources = []
        
        # Analyze Yahoo Finance alternatives
        yahoo_results = self.results.get('yahoo_alternatives', {})
        working_yahoo_endpoints = [k for k, v in yahoo_results.items() if v.get('status') == 'working']
        
        if working_yahoo_endpoints:
            viable_sources.append(f"Yahoo Finance API ({len(working_yahoo_endpoints)} endpoints)")
        
        # Check other sources
        if self.results.get('alpha_vantage', {}).get('status') == 'demo_working':
            potential_sources.append("Alpha Vantage (requires API key)")
        
        # Print recommendations
        print(f"\n🎯 REDUNDANCY STRATEGY RECOMMENDATIONS:")
        
        print(f"\n✅ PRIMARY SOURCES:")
        print(f"   1. YFinance library (proven working)")
        for source in viable_sources:
            print(f"   2. {source}")
        
        if potential_sources:
            print(f"\n🔑 BACKUP SOURCES (require setup):")
            for i, source in enumerate(potential_sources, 1):
                print(f"   {i}. {source}")
        
        print(f"\n🛠️  IMPLEMENTATION STRATEGY:")
        print(f"   1. Primary: Continue using yfinance library")
        print(f"   2. Backup: Implement Yahoo Finance direct API calls")
        print(f"   3. Monitoring: Add data freshness checks")
        print(f"   4. Failover: Automatic source switching on errors")
        print(f"   5. Validation: Cross-check prices between sources")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"   - Implement backup data fetching logic")
        print(f"   - Set up Alpha Vantage API key for testing")
        print(f"   - Create data source health monitoring")
        print(f"   - Test during Malaysian market hours")
        
        return {
            'viable_sources': len(viable_sources) + 1,  # +1 for yfinance
            'potential_sources': len(potential_sources),
            'recommendation': 'implement_redundancy'
        }

def main():
    print("🚀 Starting Alternative Data Sources Investigation")
    print("=" * 60)
    print(f"Investigation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = DataSourceTester()
    
    # Run all tests
    tester.test_investing_com()
    tester.test_yahoo_finance_alternatives()
    tester.test_bursa_malaysia_api()
    tester.test_alpha_vantage_potential()
    tester.test_financial_modeling_prep()
    tester.test_web_scraping_sources()
    
    # Generate final report
    final_assessment = tester.generate_redundancy_report()
    
    print(f"\n✅ Investigation Complete!")
    print(f"   Found {final_assessment['viable_sources']} viable source(s)")
    print(f"   Identified {final_assessment['potential_sources']} potential backup(s)")

if __name__ == "__main__":
    main()
