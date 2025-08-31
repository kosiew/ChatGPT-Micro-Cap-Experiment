#!/usr/bin/env python3
"""
KLSE Prompt Integration Guide
How to use Malaysian-focused AI prompts with the KLSE trading system
"""

import os
import json
from datetime import datetime
from typing import Dict, List

class KLSEPromptManager:
    """
    Manage Malaysian market-focused AI prompts for KLSE trading decisions
    """
    
    def __init__(self):
        self.prompts_file = "KLSE_System/KLSE_Market_Prompts.md"
        self.portfolio_file = "KLSE_System/klse_portfolio.csv"
        self.daily_updates_file = "KLSE_System/klse_daily_updates.csv"
        
    def generate_current_context(self) -> Dict[str, any]:
        """Generate current portfolio context for AI prompts"""
        import pandas as pd
        
        context = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "portfolio_holdings": {},
            "cash_balance_myr": 0,
            "total_equity_myr": 0,
            "current_return_pct": 0,
            "positions_count": 0,
            "available_slots": 10
        }
        
        # Load portfolio data if available
        if os.path.exists(self.portfolio_file):
            portfolio_df = pd.read_csv(self.portfolio_file)
            
            if not portfolio_df.empty:
                context["positions_count"] = len(portfolio_df)
                context["available_slots"] = 10 - len(portfolio_df)
                
                # Create holdings dictionary
                for _, row in portfolio_df.iterrows():
                    context["portfolio_holdings"][row["ticker"]] = {
                        "shares": row["shares"],
                        "avg_cost": row["avg_cost_myr"],
                        "company_name": row["company_name"],
                        "sector": row["sector"],
                        "stop_loss": row["stop_loss_myr"]
                    }
        
        # Load latest performance data
        if os.path.exists(self.daily_updates_file):
            daily_df = pd.read_csv(self.daily_updates_file)
            
            if not daily_df.empty:
                latest = daily_df.iloc[-1]
                context["cash_balance_myr"] = latest.get("cash_balance_myr", 0)
                context["total_equity_myr"] = latest.get("total_equity_myr", 0)
                context["current_return_pct"] = latest.get("total_return_pct", 0)
        
        return context
    
    def format_starting_prompt(self) -> str:
        """Format the initial Malaysian market research prompt"""
        context = self.generate_current_context()
        
        # Use actual portfolio value, fallback to 203,889 MYR if not available
        portfolio_value = context['total_equity_myr'] if context['total_equity_myr'] > 0 else 203889
        
        prompt = f"""You are a professional-grade portfolio strategist specializing in the Malaysian equity market. I have exactly {portfolio_value:,.0f} MYR as my current portfolio value and I want you to build the strongest possible stock portfolio using only board lot positions (100-share multiples) in KLSE-listed micro-cap stocks (market cap under 300 million MYR).

Your objective is to generate maximum return over the next 6 months, operating within Malaysian market regulations and dynamics.

MALAYSIAN MARKET CONSTRAINTS:
- All positions must be in 100-share board lots (Bursa Malaysia standard)
- Focus on stocks listed on Main Market or ACE Market with market cap < 300M MYR
- Consider Malaysian trading hours (9:00 AM - 5:00 PM, GMT+8)
- Account for Malaysian public holidays and trading suspensions
- Minimum investment consideration for liquidity (typically 50,000 MYR+ daily volume)

CURRENT PORTFOLIO STATUS:
- Total Portfolio Value: {portfolio_value:,.0f} MYR
- Cash Available: {context['cash_balance_myr']:,.0f} MYR
- Active Positions: {context['positions_count']}/{context['available_slots'] + context['positions_count']}
- Current Holdings: {json.dumps(context['portfolio_holdings'], indent=2) if context['portfolio_holdings'] else 'None'}

CURRENT PORTFOLIO STATUS:
- Available Cash: {context['cash_balance_myr']:,.2f} MYR
- Current Positions: {context['positions_count']}/10 slots used
- Portfolio Return: {context['current_return_pct']:+.2f}%
- Total Equity: {context['total_equity_myr']:,.2f} MYR

MALAYSIAN ECONOMIC FOCUS AREAS:
- Digital economy initiatives and Industry 4.0 adoption
- ESG compliance and sustainability trends in Malaysia
- Government infrastructure spending beneficiaries
- Export potential to China, ASEAN, and key trading partners
- Small-cap companies with strong fundamentals but limited analyst coverage

Research and create your optimal Malaysian micro-cap portfolio."""
        
        return prompt
    
    def format_weekly_reevaluation(self, previous_thesis: str = "") -> str:
        """Format weekly reevaluation prompt for Malaysian market"""
        context = self.generate_current_context()
        
        # Use actual portfolio value, fallback to 203,889 MYR if not available
        portfolio_value = context['total_equity_myr'] if context['total_equity_myr'] > 0 else 203889
        
        prompt = f"""MALAYSIAN MARKET WEEKLY PORTFOLIO REVIEW

Reevaluate your Malaysian micro-cap portfolio based on latest KLSE market developments and Malaysian economic indicators. 

CURRENT PORTFOLIO STATUS:
- Total Portfolio Value: {portfolio_value:,.0f} MYR
- Cash Available: {context['cash_balance_myr']:,.0f} MYR  
- Active Positions: {context['positions_count']}/{context['available_slots'] + context['positions_count']}
- Current Performance: {context['current_return_pct']:+.2f}%

HOLDINGS:"""
        
        for ticker, details in context['portfolio_holdings'].items():
            prompt += f"""
- {ticker}: {details['shares']} shares @ {details['avg_cost']:.3f} MYR
  Company: {details['company_name']} | Sector: {details['sector']}"""
        
        prompt += f"""

MALAYSIAN MARKET FACTORS TO ANALYZE:
- Recent government policy announcements affecting your sectors
- KLCI and FBM Small Cap Index performance trends  
- MYR exchange rate movements and sector impacts
- Bursa Malaysia regulatory changes or announcements
- Corporate earnings season results for Malaysian companies
- Regional ASEAN market developments

PREVIOUS THESIS: {previous_thesis}

Research current Malaysian market conditions and decide on any portfolio adjustments. Focus on Malaysian micro-caps only, considering board lot requirements and local market dynamics."""
        
        return prompt
    
    def format_deep_research_prompt(self, last_thesis: str = "") -> str:
        """Format deep research prompt for Malaysian market analysis"""
        context = self.generate_current_context()
        
        # Use actual portfolio value, fallback to 203,889 MYR if not available
        portfolio_value = context['total_equity_myr'] if context['total_equity_myr'] > 0 else 203889
        available_cash = context['cash_balance_myr'] if context['cash_balance_myr'] > 0 else 0
        
        prompt = f"""MALAYSIAN MICRO-CAP DEEP RESEARCH SESSION

You are a professional portfolio analyst specializing in Malaysian equity markets. Use deep research to reevaluate your KLSE micro-cap portfolio.

PORTFOLIO STATUS:
- Total Portfolio Value: {portfolio_value:,.0f} MYR
- Available Cash: {available_cash:,.0f} MYR
- Current Positions: {context['positions_count']}/10 slots
- Current Return vs KLCI: {context['current_return_pct']:+.2f}%

MALAYSIAN MARKET RESEARCH REQUIREMENTS:
- Analyze holdings using Malaysian-specific metrics and benchmarks
- Research new Malaysian micro-cap opportunities (< 300M MYR market cap)
- Consider Malaysian market seasonality and economic cycles
- Evaluate government policy impacts on target sectors
- Assess MYR currency trends and portfolio implications

RESEARCH FOCUS AREAS:
- Bursa Malaysia announcements and company filings
- Malaysian economic data and BNM monetary policy
- Securities Commission Malaysia regulatory updates
- Local Malaysian financial news and analyst coverage
- Regional ASEAN economic developments

PREVIOUS THESIS: {last_thesis}

OBJECTIVE: Generate alpha in Malaysian micro-cap space through local market expertise.

Provide portfolio recommendations and new thesis summary for next week."""
        
        return prompt
    
    def get_malaysian_market_guidelines(self) -> str:
        """Get Malaysian market-specific trading guidelines"""
        return """
MALAYSIAN MARKET TRADING GUIDELINES:

REGULATORY REQUIREMENTS:
- Board lots: 100-share minimum increments
- Disclosure threshold: 5% ownership requires announcement
- Settlement: T+2 cycle
- Trading hours: 9:00 AM - 5:00 PM (GMT+8) with lunch break

MARKET STRUCTURE:
- Main Market: Larger, more established companies
- ACE Market: Smaller, growth companies (our focus area)
- Foreign ownership limits may apply to certain sectors

SECTOR DYNAMICS:
- Plantation: Palm oil price sensitive, weather dependent
- Banking: Interest rate and BNM policy sensitive  
- Technology: Government digitalization beneficiary
- Healthcare: Aging population and medical tourism themes
- Industrial: Infrastructure spending and export manufacturing

RISK FACTORS:
- Currency: MYR volatility vs major currencies
- Liquidity: Lower volume in micro-cap space
- Regulatory: SC Malaysia policy changes
- Economic: Government fiscal policy impacts
- Regional: ASEAN economic integration effects

OPPORTUNITIES:
- Undervalued small-caps with limited analyst coverage
- Digital transformation beneficiaries
- ESG compliance leaders
- Export-oriented manufacturers
- Government infrastructure spending beneficiaries
        """

def demo_prompt_usage():
    """Demonstrate how to use Malaysian-focused prompts"""
    print("🇲🇾 KLSE AI PROMPT SYSTEM DEMO")
    print("=" * 50)
    
    prompt_manager = KLSEPromptManager()
    
    # Generate context
    context = prompt_manager.generate_current_context()
    print(f"📊 Current Portfolio Context:")
    print(f"   Total Equity: {context['total_equity_myr']:,.2f} MYR")
    print(f"   Cash Available: {context['cash_balance_myr']:,.2f} MYR")
    print(f"   Current Return: {context['current_return_pct']:+.2f}%")
    print(f"   Positions: {context['positions_count']}/10")
    
    # Show sample prompts
    print(f"\n🎯 Sample Malaysian Market Prompts:")
    print(f"\n1. STARTING RESEARCH PROMPT:")
    print("-" * 40)
    starting_prompt = prompt_manager.format_starting_prompt()
    print(starting_prompt[:500] + "...")
    
    print(f"\n2. WEEKLY REVIEW PROMPT:")
    print("-" * 40)
    weekly_prompt = prompt_manager.format_weekly_review_prompt(2, "Focus on technology and healthcare micro-caps")
    print(weekly_prompt[:500] + "...")
    
    print(f"\n3. DEEP RESEARCH PROMPT:")
    print("-" * 40)
    research_prompt = prompt_manager.format_deep_research_prompt(2500.0, "Malaysian digital economy beneficiaries")
    print(research_prompt[:500] + "...")
    
    print(f"\n📋 Malaysian Market Guidelines:")
    print("-" * 40)
    guidelines = prompt_manager.get_malaysian_market_guidelines()
    print(guidelines[:500] + "...")
    
    print(f"\n✅ Malaysian-focused AI prompts ready for use!")

if __name__ == "__main__":
    demo_prompt_usage()
