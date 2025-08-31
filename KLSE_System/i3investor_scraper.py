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

    def get_ticker_code(self, ticker: str, max_retries: int = 3) -> Optional[str]:
        """
        Get the numeric ticker code from i3investor website
        
        Args:
            ticker: Stock ticker symbol (e.g., 'MBMR', 'AXIATA')
            max_retries: Maximum number of retry attempts
            
        Returns:
            Formatted ticker for yfinance (e.g., '5983.KL'), or None if failed
        """
        # Clean ticker - remove .KL suffix if present
        clean_ticker = ticker.replace('.KL', '').upper()
        
        url = f"{self.base_url}{clean_ticker}"
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Attempting to get ticker code for {clean_ticker} (attempt {attempt})")
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for the subtitle element with ticker information
                # <p class="m-0 subtitle" style="font-size: 18px; ">
                #     <strong style="">KLSE (MYR): MBMR (5983)</strong>
                # </p>
                subtitle_p = soup.find('p', class_='subtitle')
                
                if subtitle_p:
                    strong_tag = subtitle_p.find('strong')
                    if strong_tag:
                        text = strong_tag.get_text(strip=True)
                        
                        # Extract ticker code from text like "KLSE (MYR): MBMR (5983)"
                        # Look for pattern: SYMBOL (NNNN)
                        match = re.search(fr'{clean_ticker}\s*\((\d+)\)', text)
                        if match:
                            ticker_code = match.group(1)
                            formatted_ticker = f"{ticker_code}.KL"
                            self.logger.info(f"✅ Found ticker code: {clean_ticker} -> {formatted_ticker}")
                            return formatted_ticker
                
                # Fallback: look for any pattern with the ticker name and numbers in parentheses
                all_text = soup.get_text()
                match = re.search(fr'{clean_ticker}\s*\((\d+)\)', all_text)
                if match:
                    ticker_code = match.group(1)
                    formatted_ticker = f"{ticker_code}.KL"
                    self.logger.info(f"✅ Found ticker code (fallback): {clean_ticker} -> {formatted_ticker}")
                    return formatted_ticker
                
                self.logger.warning(f"❌ Could not find ticker code for {clean_ticker}")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None
                    
            except requests.RequestException as e:
                self.logger.warning(f"❌ i3investor ticker attempt {attempt} failed for {clean_ticker}: {str(e)}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None
                
            except Exception as e:
                self.logger.error(f"❌ i3investor ticker unexpected error for {clean_ticker}: {str(e)}")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None
        
        self.logger.error(f"❌ i3investor: All {max_retries} attempts failed for ticker {clean_ticker}")
        return None

    def test_scraper(self, test_tickers: list = None):
        """Test the scraper with a few known tickers"""
        if test_tickers is None:
            test_tickers = ['AXIATA', 'MAYBANK', 'TENAGA', 'MBMR']
        
        print("Testing I3Investor Scraper:")
        print("=" * 50)
        
        for ticker in test_tickers:
            print(f"\nTesting {ticker}:")
            
            # Test ticker code extraction
            ticker_code = self.get_ticker_code(ticker)
            ticker_status = ticker_code if ticker_code else "FAILED"
            print(f"  Ticker Code: {ticker_status}")
            
            # Test price fetching
            price = self.get_stock_price(ticker)
            price_status = f"{price} MYR" if price else "FAILED"
            print(f"  Price:       {price_status}")

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = I3InvestorScraper()
    scraper.test_scraper()
