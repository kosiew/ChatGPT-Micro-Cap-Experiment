#!/usr/bin/env python3
"""
I3Investor Web Scraper for KLSE Stock Prices
Fallback data source when Yahoo Finance fails
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Optional
import time

class I3InvestorScraper:
    def __init__(self):
        self.base_url = "https://klse.i3investor.com/web/stock/analysis-price-target/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger = logging.getLogger(__name__)

    def get_stock_price(self, ticker: str, max_retries: int = 3) -> Optional[float]:
        """
        Get stock price from i3investor website
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AXIATA', 'BJCORP')
            max_retries: Maximum number of retry attempts
            
        Returns:
            Stock price as float, or None if failed
        """
        # Clean ticker - remove .KL suffix if present
        clean_ticker = ticker.replace('.KL', '').upper()
        
        url = f"{self.base_url}{clean_ticker}"
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Attempting i3investor scrape for {clean_ticker} (attempt {attempt})")
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find the stock price info div
                price_div = soup.find('div', {'id': 'stock-price-info'})
                
                if not price_div:
                    self.logger.warning(f"❌ i3investor: No price info div found for {clean_ticker}")
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    return None
                
                # Find the first column with "Last Price"
                last_price_col = None
                for col in price_div.find_all('div', class_=re.compile(r'col-')):
                    p_tags = col.find_all('p')
                    if len(p_tags) >= 2 and 'Last Price' in p_tags[0].get_text():
                        last_price_col = col
                        break
                
                if not last_price_col:
                    self.logger.warning(f"❌ i3investor: No 'Last Price' column found for {clean_ticker}")
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    return None
                
                # Extract price from the second p tag
                price_p = last_price_col.find_all('p')[1]
                price_text = price_p.get_text(strip=True)
                
                # Extract numeric value from price text
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                
                if price_match:
                    price = float(price_match.group())
                    self.logger.info(f"✅ i3investor success: {clean_ticker} = {price} MYR")
                    return price
                else:
                    self.logger.warning(f"❌ i3investor: Could not parse price '{price_text}' for {clean_ticker}")
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    return None
                    
            except requests.RequestException as e:
                self.logger.warning(f"❌ i3investor attempt {attempt} failed for {clean_ticker}: {str(e)}")
                if attempt < max_retries:
                    time.sleep(2)  # Longer delay for network errors
                    continue
                return None
                
            except Exception as e:
                self.logger.error(f"❌ i3investor unexpected error for {clean_ticker}: {str(e)}")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None
        
        self.logger.error(f"❌ i3investor: All {max_retries} attempts failed for {clean_ticker}")
        return None

    def test_scraper(self, test_tickers: list = None):
        """Test the scraper with a few known tickers"""
        if test_tickers is None:
            test_tickers = ['AXIATA', 'MAYBANK', 'TENAGA']
        
        print("Testing I3Investor Scraper:")
        print("=" * 40)
        
        for ticker in test_tickers:
            price = self.get_stock_price(ticker)
            status = f"{price} MYR" if price else "FAILED"
            print(f"{ticker:10}: {status}")

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = I3InvestorScraper()
    scraper.test_scraper()
