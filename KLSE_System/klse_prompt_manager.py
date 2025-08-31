#!/usr/bin/env python3
"""
KLSE Prompt Manager - Typer CLI for generating trading prompts
Provides three types of prompts: weekly evaluation, deep research, and starting prompt
"""

import typer
import os
import json
import pandas as pd
from datetime import datetime
from typing import Optional

app = typer.Typer(help="KLSE Micro-Cap Trading Prompt Generator")

class KLSEPromptManager:
    def __init__(self, config_path: str = "klse_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """Load configuration from JSON file"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self.get_default_config()
    
    def get_default_config(self) -> dict:
        """Return default configuration"""
        return {
            "portfolio": {
                "starting_capital": 5000,
                "currency": "MYR",
                "market": "KLSE",
                "max_positions": 8,
                "position_sizing": "equal_weight"
            },
            "risk_management": {
                "max_position_size": 0.20,
                "stop_loss_percentage": 0.15,
                "max_daily_loss": 0.05
            },
            "trading_rules": {
                "market_cap_limit": 500000000,
                "minimum_volume": 50000,
                "sectors_excluded": []
            }
        }
    
    def get_portfolio_status(self) -> dict:
        """Get current portfolio status from CSV files"""
        portfolio_data = {
            "total_equity": 5000,  # Default
            "current_positions": 0,
            "cash_balance": 5000,
            "recent_trades": []
        }
        
        # Try to read current portfolio
        try:
            if os.path.exists("klse_portfolio.csv"):
                df = pd.read_csv("klse_portfolio.csv")
                if not df.empty:
                    latest_row = df.iloc[-1]
                    portfolio_data["total_equity"] = latest_row.get("Total_Equity", 5000)
                    portfolio_data["cash_balance"] = latest_row.get("Cash_Balance", 5000)
                    
            # Count current positions
            if os.path.exists("klse_portfolio.csv"):
                df = pd.read_csv("klse_portfolio.csv")
                current_positions = df[df["Shares"] > 0] if not df.empty else pd.DataFrame()
                portfolio_data["current_positions"] = len(current_positions)
                
        except Exception as e:
            print(f"Warning: Could not read portfolio data: {e}")
            
        return portfolio_data
    
    def generate_weekly_evaluation_prompt(self) -> str:
        """Generate weekly portfolio evaluation prompt"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        portfolio_status = self.get_portfolio_status()
        
        prompt = f"""
# KLSE Micro-Cap Weekly Portfolio Evaluation - {current_date}

## Portfolio Performance Review

### Current Portfolio Status:
- Total Equity: MYR {portfolio_status['total_equity']:,.2f}
- Active Positions: {portfolio_status['current_positions']}
- Cash Balance: MYR {portfolio_status['cash_balance']:,.2f}
- Maximum Positions Allowed: {self.config['portfolio']['max_positions']}

### Weekly Evaluation Tasks:

#### 1. Performance Analysis
- Calculate weekly returns vs KLCI benchmark
- Analyze individual position performance
- Identify best and worst performing stocks
- Review stop-loss triggers and exits

#### 2. Risk Assessment
- Current portfolio concentration
- Sector allocation review
- Position sizing analysis
- Risk-adjusted returns evaluation

#### 3. Market Review
- KLSE market sentiment this week
- Micro-cap sector trends
- Economic indicators impact
- Currency (MYR) strength assessment

#### 4. Position Management
- Review existing holdings fundamentals
- Assess stop-loss levels
- Consider position adjustments
- Identify underperforming assets

#### 5. Strategic Planning
- Market outlook for next week
- Potential new opportunities
- Sector rotation considerations
- Risk management adjustments

### Action Items:
1. Provide detailed analysis of current positions
2. Recommend any position adjustments
3. Suggest new micro-cap opportunities if applicable
4. Update stop-loss levels if needed
5. Outline strategy for upcoming week

### Risk Parameters:
- Market Cap Limit: MYR {self.config['trading_rules']['market_cap_limit']:,}
- Max Position Size: {self.config['risk_management']['max_position_size']*100}%
- Stop-Loss: {self.config['risk_management']['stop_loss_percentage']*100}%

---
*Weekly Evaluation Generated: {current_date}*
        """
        return prompt.strip()
    
    def generate_deep_research_prompt(self) -> str:
        """Generate deep research prompt for new opportunities"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        portfolio_status = self.get_portfolio_status()
        
        prompt = f"""
# KLSE Micro-Cap Deep Research Analysis - {current_date}

## Research Objective
Conduct comprehensive analysis to identify high-potential micro-cap opportunities on Bursa Malaysia.

### Current Portfolio Context:
- Available Cash: MYR {portfolio_status['cash_balance']:,.2f}
- Current Positions: {portfolio_status['current_positions']}/{self.config['portfolio']['max_positions']}
- Total Equity: MYR {portfolio_status['total_equity']:,.2f}

## Deep Research Framework:

### 1. Market Screening
**Criteria:**
- Market Cap: < MYR {self.config['trading_rules']['market_cap_limit']:,}
- Daily Volume: > {self.config['trading_rules']['minimum_volume']:,} shares
- Exclude Sectors: {', '.join(self.config['trading_rules']['sectors_excluded'])}

### 2. Fundamental Analysis
**Key Metrics to Research:**
- Revenue growth trends (3-year)
- Profit margins and ROE
- Debt-to-equity ratios
- Cash flow generation
- Book value vs market value
- Dividend history and sustainability

### 3. Business Quality Assessment
**Evaluate:**
- Management track record
- Competitive advantages/moats
- Industry position and market share
- Business model sustainability
- ESG considerations
- Corporate governance quality

### 4. Technical Analysis
**Chart Patterns:**
- Support and resistance levels
- Volume trends
- Moving average analysis
- RSI and momentum indicators
- Breakout patterns

### 5. Catalysts Identification
**Look for:**
- Upcoming earnings releases
- New contract announcements
- Expansion plans or capex
- Regulatory changes impact
- Industry tailwinds
- Merger & acquisition potential

### 6. Risk Assessment
**Evaluate:**
- Liquidity risks
- Key man dependencies
- Regulatory risks
- Market concentration
- Currency exposure
- Cyclical sensitivity

### 7. Valuation Analysis
**Methods:**
- P/E ratios vs peers
- P/B ratios analysis
- EV/EBITDA multiples
- DCF modeling (if applicable)
- Asset-based valuation
- Sum-of-parts analysis

## Research Deliverables:
1. **Top 3-5 stock recommendations** with detailed analysis
2. **Entry price targets** and rationale
3. **Stop-loss levels** for each recommendation
4. **Position sizing** suggestions
5. **Investment thesis** for each stock (2-3 paragraphs)
6. **Risk factors** and mitigation strategies
7. **Expected timeline** for thesis to play out

## Research Sources to Consider:
- Bursa Malaysia announcements
- Company annual reports and quarterly results
- Industry research reports
- Broker research (if available)
- Economic indicators and trends
- Peer company analysis

### Target Sectors for Research:
- Technology and fintech
- Healthcare and pharmaceuticals
- Consumer goods and services
- Industrial products and services
- Plantation and agriculture
- Construction and property development

---
*Deep Research Session: {current_date}*
        """
        return prompt.strip()
    
    def generate_starting_prompt(self) -> str:
        """Generate initial trading system prompt"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
# KLSE Micro-Cap Trading System - Initial Setup - {current_date}

## Welcome to KLSE Micro-Cap Trading

You are now managing a systematic micro-cap trading portfolio focused on Bursa Malaysia (KLSE). This is the beginning of your trading journey.

### Portfolio Initialization:
- **Starting Capital**: MYR {self.config['portfolio']['starting_capital']:,}
- **Trading Universe**: KLSE micro-cap stocks
- **Investment Horizon**: Medium to long-term value investing
- **Maximum Positions**: {self.config['portfolio']['max_positions']} stocks

## Trading System Framework:

### 1. Investment Philosophy
- **Value-Oriented Approach**: Focus on undervalued micro-cap companies
- **Quality Bias**: Prefer companies with solid fundamentals
- **Catalyst-Driven**: Look for specific events that can unlock value
- **Risk-Conscious**: Emphasize capital preservation

### 2. Stock Selection Criteria
**Mandatory Requirements:**
- Market Cap: < MYR {self.config['trading_rules']['market_cap_limit']:,} million
- Minimum Daily Volume: {self.config['trading_rules']['minimum_volume']:,} shares
- Listed on Main Board or ACE Market
- Exclude: {', '.join(self.config['trading_rules']['sectors_excluded'])} sectors

**Preferred Characteristics:**
- Profitable companies with consistent earnings
- Strong balance sheets (low debt)
- Experienced management teams
- Growing or stable industries
- Reasonable valuations (P/E < 15, P/B < 2)

### 3. Risk Management Rules
- **Position Sizing**: Equal weight approach (~12.5% per position)
- **Maximum Position**: {self.config['risk_management']['max_position_size']*100}% of portfolio
- **Stop-Loss**: {self.config['risk_management']['stop_loss_percentage']*100}% below purchase price
- **Daily Loss Limit**: {self.config['risk_management']['max_daily_loss']*100}% of portfolio value
- **Diversification**: No more than 2 stocks per sector

### 4. Trading Workflow
**Weekly Process:**
1. Market and economic review
2. Portfolio performance evaluation
3. Individual stock monitoring
4. New opportunity research
5. Position adjustments if needed

**Monthly Deep Dive:**
- Comprehensive fundamental research
- Industry analysis and trends
- New stock discovery
- Strategy refinement

### 5. Performance Benchmarks
- **Primary**: KLCI (FTSE Bursa Malaysia KLCI)
- **Secondary**: Small-cap indices
- **Target**: Outperform benchmarks with lower volatility
- **Risk Metric**: Maximum drawdown < 20%

## Initial Action Plan:

### Phase 1: Market Research (Week 1-2)
1. Conduct comprehensive micro-cap screening
2. Identify 15-20 potential candidates
3. Perform fundamental analysis
4. Create watchlist with entry targets

### Phase 2: Initial Positioning (Week 3-4)
1. Start with 3-4 high-conviction positions
2. Equal weight allocation
3. Set stop-loss levels
4. Monitor market conditions

### Phase 3: Portfolio Build-out (Month 2-3)
1. Gradually add positions (1-2 per month)
2. Reach target of 6-8 positions
3. Maintain diversification
4. Adjust based on performance

## Market Context (Malaysia):
- **Economic Environment**: [Current GDP growth, inflation, interest rates]
- **Currency**: MYR strength vs USD, regional currencies
- **Sector Trends**: Technology adoption, ESG focus, infrastructure development
- **Regulatory**: Capital market reforms, foreign investment rules

## Success Metrics:
- **Annual Return Target**: 12-15% (beating KLCI)
- **Sharpe Ratio**: > 0.8
- **Maximum Drawdown**: < 15%
- **Win Rate**: > 60% of positions profitable

## Next Steps:
1. Begin comprehensive market screening
2. Research top 10 micro-cap opportunities
3. Prepare detailed investment thesis for each
4. Create initial portfolio allocation plan
5. Set up monitoring and evaluation schedule

---
*Trading System Initialized: {current_date}*
*Ready to begin systematic micro-cap investing on KLSE*
        """
        return prompt.strip()

@app.command()
def weekly():
    """Generate weekly portfolio evaluation prompt"""
    manager = KLSEPromptManager()
    prompt = manager.generate_weekly_evaluation_prompt()
    print(prompt)

@app.command()
def research():
    """Generate deep research prompt for new opportunities"""
    manager = KLSEPromptManager()
    prompt = manager.generate_deep_research_prompt()
    print(prompt)

@app.command()
def starting():
    """Generate starting/initialization prompt"""
    manager = KLSEPromptManager()
    prompt = manager.generate_starting_prompt()
    print(prompt)

@app.command()
def demo():
    """Show all available prompt types with brief descriptions"""
    print("""# KLSE Prompt Manager - Available Commands

## Command Options:

### `weekly`
Generate a comprehensive weekly portfolio evaluation prompt.
- Reviews current positions and performance
- Analyzes market conditions
- Provides decision framework for the upcoming week

### `research` 
Generate a deep research prompt for identifying new opportunities.
- Systematic screening methodology
- Fundamental and technical analysis framework
- Catalyst identification and timing

### `starting`
Generate the initial setup prompt for beginning the trading system.
- Portfolio configuration and rules
- Investment framework and criteria
- Risk management protocols

## Usage Examples:
```bash
python klse_prompt_manager.py weekly
python klse_prompt_manager.py research  
python klse_prompt_manager.py starting
```

Choose the appropriate prompt type for your current trading session needs.""")

if __name__ == "__main__":
    app()
