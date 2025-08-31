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
from typing import Optional, Dict, Any, List
import logging
from bs4 import BeautifulSoup
import re
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Typer app
app = typer.Typer(help="🚀 Redundant KLSE Data Fetcher - Robust Malaysian stock data with multiple fallback sources")
console = Console()

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
            'alpha_vantage': {'attempts': 0, 'successes': 0, 'last_used': None},
            'i3investor': {'attempts': 0, 'successes': 0, 'last_used': None}
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
            ('i3investor', self._fetch_i3investor),
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
    
    def _fetch_i3investor(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch data from i3investor website as fallback"""
        try:
            # Remove .KL suffix for i3investor URL
            base_ticker = ticker.replace('.KL', '')
            url = f"https://klse.i3investor.com/web/stock/analysis-price-target/{base_ticker}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract numerical ticker for future yfinance attempts
            self._extract_numerical_ticker(soup, base_ticker)
            
            # Find the stock price info div
            price_div = soup.find('div', {'id': 'stock-price-info'})
            if not price_div:
                logger.warning(f"Could not find stock-price-info div for {ticker}")
                return None
            
            # Look for the last price in the first column
            price_columns = price_div.find_all('div', class_='col-md-3')
            if not price_columns:
                logger.warning(f"Could not find price columns for {ticker}")
                return None
            
            # First column should contain "Last Price"
            last_price_column = price_columns[0]
            price_text = last_price_column.find('p', style=lambda value: value and 'font-size: 22px' in value)
            
            if not price_text:
                logger.warning(f"Could not find price text for {ticker}")
                return None
            
            # Extract price from the strong tag
            price_strong = price_text.find('strong')
            if not price_strong:
                logger.warning(f"Could not find price strong tag for {ticker}")
                return None
            
            price_str = price_strong.get_text().strip()
            
            # Clean the price string (remove commas, etc.)
            price_clean = re.sub(r'[^\d.]', '', price_str)
            
            if not price_clean:
                logger.warning(f"Could not extract clean price from '{price_str}' for {ticker}")
                return None
            
            price = float(price_clean)
            
            # Try to get volume from the fourth column
            volume = None
            if len(price_columns) >= 4:
                volume_column = price_columns[3]
                volume_text = volume_column.find('p', style=lambda value: value and 'font-size: 22px' in value)
                if volume_text:
                    volume_strong = volume_text.find('strong')
                    if volume_strong:
                        volume_str = volume_strong.get_text().strip()
                        # Remove commas and convert to int
                        volume_clean = re.sub(r'[^\d]', '', volume_str)
                        if volume_clean:
                            volume = int(volume_clean)
            
            logger.info(f"i3investor scraped price for {ticker}: {price} MYR")
            
            return {
                'price': round(price, 3),
                'currency': 'MYR',
                'volume': volume,
                'market_cap': None,
                'data_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"i3investor scraping failed for {ticker}: {e}")
            return None
    
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

    def _extract_numerical_ticker(self, soup, symbol_ticker: str):
        """
        Extract numerical ticker from i3investor page and store mapping
        Example: "KLSE (MYR): MBMR (5983)" -> maps MBMR to 5983
        """
        try:
            # Find the subtitle element with ticker information
            subtitle = soup.find('p', class_='subtitle')
            if not subtitle:
                # Try alternative selector
                subtitle = soup.find('p', style=lambda value: value and 'font-size: 18px' in value)
            
            if not subtitle:
                logger.debug(f"Could not find subtitle element for {symbol_ticker}")
                return
            
            subtitle_text = subtitle.get_text().strip()
            logger.debug(f"Found subtitle: {subtitle_text}")
            
            # Parse format: "KLSE (MYR): MBMR (5983)"
            match = re.search(r'(\w+)\s*\((\d+)\)', subtitle_text)
            if match:
                symbol = match.group(1).upper()
                numerical = match.group(2)
                
                if symbol == symbol_ticker.upper():
                    # Store the mapping
                    if not hasattr(self, 'ticker_mappings'):
                        self.ticker_mappings = {}
                    
                    self.ticker_mappings[symbol] = numerical
                    logger.info(f"📝 Ticker mapping discovered: {symbol} -> {numerical}")
                    
                    # Save to file for future use
                    self._save_ticker_mapping(symbol, numerical)
                    
        except Exception as e:
            logger.warning(f"Could not extract numerical ticker for {symbol_ticker}: {e}")

    def _save_ticker_mapping(self, symbol: str, numerical: str):
        """Save ticker mapping to JSON file for future use"""
        try:
            import json
            import os
            
            mapping_file = os.path.join(os.path.dirname(__file__), 'ticker_mappings.json')
            
            # Load existing mappings
            mappings = {}
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mappings = json.load(f)
            
            # Add new mapping
            mappings[symbol] = numerical
            
            # Save updated mappings
            with open(mapping_file, 'w') as f:
                json.dump(mappings, f, indent=2)
                
            logger.info(f"💾 Saved ticker mapping {symbol} -> {numerical}")
            
        except Exception as e:
            logger.warning(f"Could not save ticker mapping: {e}")

    def get_numerical_ticker(self, symbol: str) -> Optional[str]:
        """
        Get numerical ticker for a symbol from saved mappings
        Returns format suitable for yfinance (e.g., "5983.KL")
        """
        try:
            import json
            import os
            
            mapping_file = os.path.join(os.path.dirname(__file__), 'ticker_mappings.json')
            
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mappings = json.load(f)
                
                clean_symbol = symbol.replace('.KL', '').upper()
                if clean_symbol in mappings:
                    numerical = mappings[clean_symbol]
                    return f"{numerical}.KL"
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not load ticker mapping for {symbol}: {e}")
            return None
    
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

@app.command("fetch")
def fetch_stock(
    ticker: str = typer.Argument(..., help="Malaysian stock code (e.g., '1155' for Maybank)"),
    retries: int = typer.Option(3, help="Number of retry attempts per source"),
    api_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for additional data source")
):
    """Fetch current price for a single Malaysian stock"""
    console.print(f"[bold blue]🔍 Fetching data for {ticker}...[/bold blue]")
    
    fetcher = KLSEDataFetcher(alpha_vantage_key=api_key)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task(f"Fetching {ticker}", total=None)
        data = fetcher.get_stock_price(ticker, retries=retries)
    
    if data:
        # Create a results table
        table = Table(title=f"Stock Data for {ticker}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Ticker", data['ticker'])
        table.add_row("Price", f"{data['price']} {data['currency']}")
        table.add_row("Volume", str(data.get('volume', 'N/A')))
        table.add_row("Market Cap", str(data.get('market_cap', 'N/A')))
        table.add_row("Source", data['source'])
        table.add_row("Fetch Time", data['fetch_time'])
        
        console.print(table)
        console.print(f"[green]✅ Successfully fetched {ticker} price: {data['price']} {data['currency']}[/green]")
    else:
        console.print(f"[red]❌ Failed to fetch data for {ticker}[/red]")
        raise typer.Exit(1)

@app.command("batch")
def fetch_multiple(
    tickers: str = typer.Argument(..., help="Comma-separated list of tickers (e.g., '1155,4723,0090')"),
    api_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key for additional data source"),
    output_file: Optional[str] = typer.Option(None, help="Save results to CSV file")
):
    """Fetch data for multiple stocks in batch"""
    ticker_list = [t.strip() for t in tickers.split(',')]
    
    console.print(f"[bold blue]� Batch fetching {len(ticker_list)} stocks...[/bold blue]")
    
    fetcher = KLSEDataFetcher(alpha_vantage_key=api_key)
    
    with Progress() as progress:
        task = progress.add_task("Fetching stocks...", total=len(ticker_list))
        results = {}
        
        for ticker in ticker_list:
            data = fetcher.get_stock_price(ticker)
            results[ticker] = data
            progress.advance(task)
            time.sleep(0.5)  # Rate limiting
    
    # Create results table
    table = Table(title="Batch Stock Data Results")
    table.add_column("Ticker", style="cyan")
    table.add_column("Price", style="magenta")
    table.add_column("Currency", style="yellow")
    table.add_column("Source", style="green")
    table.add_column("Status", style="white")
    
    successful = 0
    for ticker, data in results.items():
        if data:
            table.add_row(
                ticker,
                str(data['price']),
                data['currency'],
                data['source'],
                "✅ Success"
            )
            successful += 1
        else:
            table.add_row(ticker, "N/A", "N/A", "N/A", "❌ Failed")
    
    console.print(table)
    console.print(f"[green]Success rate: {successful}/{len(ticker_list)} ({successful/len(ticker_list)*100:.1f}%)[/green]")
    
    # Save to CSV if requested
    if output_file:
        df_data = []
        for ticker, data in results.items():
            if data:
                df_data.append({
                    'ticker': ticker,
                    'price': data['price'],
                    'currency': data['currency'],
                    'volume': data.get('volume'),
                    'source': data['source'],
                    'fetch_time': data['fetch_time']
                })
        
        if df_data:
            df = pd.DataFrame(df_data)
            df.to_csv(output_file, index=False)
            console.print(f"[blue]💾 Results saved to {output_file}[/blue]")

@app.command("test")
def test_sources(
    ticker: str = typer.Option("1155", help="Stock ticker to test with (default: Maybank)"),
    api_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key")
):
    """Test all available data sources with a known stock"""
    console.print(f"[bold blue]🧪 Testing all data sources with {ticker}...[/bold blue]")
    
    fetcher = KLSEDataFetcher(alpha_vantage_key=api_key)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("Testing sources", total=None)
        test_results = fetcher.test_all_sources(ticker)
    
    # Create test results table
    table = Table(title=f"Data Source Test Results for {ticker}")
    table.add_column("Source", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Price", style="magenta")
    table.add_column("Currency", style="yellow")
    table.add_column("Details", style="dim")
    
    for source, result in test_results.items():
        status = result['status']
        
        if status == 'success':
            data = result['data']
            table.add_row(
                source,
                "✅ Success",
                str(data['price']),
                data['currency'],
                f"Volume: {data.get('volume', 'N/A')}"
            )
        elif status == 'no_api_key':
            table.add_row(source, "🔑 API Key Required", "N/A", "N/A", "Provide --api-key option")
        elif status == 'no_data':
            table.add_row(source, "📭 No Data", "N/A", "N/A", "Source returned empty")
        else:
            error_msg = result.get('error', 'Unknown error')
            table.add_row(source, "❌ Error", "N/A", "N/A", error_msg[:50])
    
    console.print(table)

@app.command("performance")
def show_performance(
    api_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key")
):
    """Show data source performance statistics"""
    console.print("[bold blue]📈 Data Source Performance Statistics[/bold blue]")
    
    fetcher = KLSEDataFetcher(alpha_vantage_key=api_key)
    
    # Run a quick test to generate some stats
    test_tickers = ["1155", "4723", "0090"]
    
    console.print("Running quick performance test...")
    with Progress() as progress:
        task = progress.add_task("Testing performance...", total=len(test_tickers))
        
        for ticker in test_tickers:
            fetcher.get_stock_price(ticker)
            progress.advance(task)
    
    # Get performance stats
    performance = fetcher.get_source_performance()
    
    if performance:
        table = Table(title="Data Source Performance")
        table.add_column("Source", style="cyan")
        table.add_column("Success Rate", style="green")
        table.add_column("Attempts", style="blue")
        table.add_column("Successes", style="magenta")
        table.add_column("Last Used", style="dim")
        
        for source, stats in performance.items():
            last_used = stats['last_used']
            if last_used:
                last_used = datetime.fromisoformat(last_used).strftime("%H:%M:%S")
            else:
                last_used = "Never"
                
            table.add_row(
                source,
                f"{stats['success_rate']}%",
                str(stats['attempts']),
                str(stats['successes']),
                last_used
            )
        
        console.print(table)
    else:
        console.print("[yellow]No performance data available yet. Run some fetch commands first.[/yellow]")

@app.command("show-mappings")
def show_mappings():
    """Show all currently saved ticker mappings"""
    try:
        import json
        import os
        
        mapping_file = os.path.join(os.path.dirname(__file__), 'ticker_mappings.json')
        
        if not os.path.exists(mapping_file):
            console.print("[yellow]No ticker mappings file found. Use 'extract-mappings' to create one.[/yellow]")
            return
        
        with open(mapping_file, 'r') as f:
            mappings = json.load(f)
        
        if not mappings:
            console.print("[yellow]Ticker mappings file is empty.[/yellow]")
            return
        
        table = Table(title="Saved Ticker Mappings")
        table.add_column("Symbol", style="cyan")
        table.add_column("Numerical Code", style="magenta")
        table.add_column("YFinance Format", style="green")
        
        for symbol, numerical in sorted(mappings.items()):
            table.add_row(symbol, numerical, f"{numerical}.KL")
        
        console.print(table)
        console.print(f"\n📊 Total: {len(mappings)} ticker mappings saved")
        
    except Exception as e:
        console.print(f"❌ [red]Error reading mappings file: {e}[/red]")

@app.command("extract-mappings")
def extract_mappings(
    tickers: List[str] = typer.Argument(..., help="List of symbol tickers to extract numerical mappings for (e.g., MBMR AXIATA)")
):
    """
    Extract numerical ticker mappings from i3investor for the given symbol tickers.
    This will visit i3investor pages and save the numerical mappings for future yfinance use.
    
    Example: python redundant_data_fetcher.py extract-mappings MBMR AXIATA BJCORP
    """
    console.print(f"🔍 [bold blue]Extracting ticker mappings for {len(tickers)} symbols[/bold blue]")
    
    fetcher = KLSEDataFetcher()
    extracted_count = 0
    
    for ticker in tickers:
        console.print(f"\n📋 Processing {ticker}...")
        
        try:
            # Visit i3investor page to extract mapping
            base_ticker = ticker.replace('.KL', '').upper()
            url = f"https://klse.i3investor.com/web/stock/analysis-price-target/{base_ticker.lower()}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = fetcher.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            fetcher._extract_numerical_ticker(soup, base_ticker)
            
            # Check if mapping was found
            numerical = fetcher.get_numerical_ticker(ticker)
            if numerical:
                console.print(f"✅ [green]{ticker} -> {numerical}[/green]")
                extracted_count += 1
            else:
                console.print(f"❌ [red]Could not extract mapping for {ticker}[/red]")
                
        except Exception as e:
            console.print(f"❌ [red]Error processing {ticker}: {e}[/red]")
    
    console.print(f"\n🎯 [bold green]Extracted {extracted_count}/{len(tickers)} ticker mappings[/bold green]")
    
    # Show current mappings file
    try:
        import json
        import os
        mapping_file = os.path.join(os.path.dirname(__file__), 'ticker_mappings.json')
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                mappings = json.load(f)
            console.print(f"\n📁 [bold]Current mappings file contains {len(mappings)} entries:[/bold]")
            for symbol, numerical in mappings.items():
                console.print(f"   {symbol} -> {numerical}.KL")
    except Exception as e:
        console.print(f"⚠️ Could not read mappings file: {e}")

@app.command("demo")
def run_demo(
    api_key: Optional[str] = typer.Option(None, help="Alpha Vantage API key")
):
    """Run a comprehensive demonstration of the redundant fetching system"""
    console.print(Panel.fit(
        "[bold blue]🚀 Redundant KLSE Data Fetching Demonstration[/bold blue]\n"
        "This demo will test various features of the redundant data fetching system.",
        title="Demo Mode"
    ))
    
    fetcher = KLSEDataFetcher(alpha_vantage_key=api_key)
    test_stocks = ["1155", "4723", "0090"]  # Maybank, JAKS, NETX
    
    # Test 1: Individual stock fetching
    console.print("\n[bold cyan]🔍 Test 1: Individual Stock Fetching[/bold cyan]")
    for ticker in test_stocks:
        console.print(f"Fetching {ticker}...")
        data = fetcher.get_stock_price(ticker)
        
        if data:
            console.print(f"✅ {ticker}: {data['price']} {data['currency']} (via {data['source']})")
        else:
            console.print(f"❌ {ticker}: Failed to fetch data")
    
    # Test 2: Batch fetching
    console.print(f"\n[bold cyan]📊 Test 2: Batch Fetching[/bold cyan]")
    batch_results = fetcher.get_multiple_stocks(test_stocks)
    successful_batch = sum(1 for v in batch_results.values() if v is not None)
    console.print(f"Batch success rate: {successful_batch}/{len(test_stocks)}")
    
    # Test 3: Performance stats
    console.print(f"\n[bold cyan]📈 Test 3: Performance Statistics[/bold cyan]")
    performance = fetcher.get_source_performance()
    for source, stats in performance.items():
        console.print(f"   {source}: {stats['success_rate']}% success ({stats['successes']}/{stats['attempts']})")
    
    # Test 4: Source testing
    console.print(f"\n[bold cyan]🧪 Test 4: Testing All Sources[/bold cyan]")
    test_results = fetcher.test_all_sources("1155")
    
    for source, result in test_results.items():
        status = result['status']
        if status == 'success':
            data = result['data']
            console.print(f"✅ {source}: {data['price']} {data['currency']}")
        elif status == 'no_api_key':
            console.print(f"🔑 {source}: API key required")
        else:
            console.print(f"❌ {source}: {status}")
    
    console.print(Panel.fit(
        "[bold green]Demo completed![/bold green]\n\n"
        "[bold white]Usage Recommendations:[/bold white]\n"
        "1. Use 'fetch <ticker>' for single stocks\n"
        "2. Use 'batch <tickers>' for multiple stocks\n"
        "3. Use 'test' to verify data sources\n"
        "4. Use 'performance' to monitor reliability\n"
        "5. Set up Alpha Vantage API key for additional redundancy",
        title="Summary"
    ))

if __name__ == "__main__":
    app()
