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
            "holdings": [],
            "holdings_summary": "",
            "recent_trades": []
        }
        
        # Try to read current portfolio - check multiple possible locations
        portfolio_file = None
        possible_locations = [
            "klse_portfolio.csv",  # Current directory
            "KLSE_System/klse_portfolio.csv",  # From project root
            os.path.join(os.path.dirname(__file__), "klse_portfolio.csv")  # Same directory as script
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                portfolio_file = location
                break
        
        try:
            if portfolio_file:
                df = pd.read_csv(portfolio_file)
                if not df.empty:
                    # Calculate portfolio metrics
                    portfolio_data["current_positions"] = len(df)
                    total_market_value = df["market_value_myr"].sum()
                    portfolio_data["total_equity"] = total_market_value
                    
                    # Get holdings details
                    holdings = []
                    for _, row in df.iterrows():
                        holding = {
                            "ticker": row["ticker"],
                            "company": row["company_name"],
                            "shares": row["shares"],
                            "avg_cost": row["avg_cost_myr"],
                            "current_price": row["current_price_myr"],
                            "market_value": row["market_value_myr"],
                            "stop_loss": row["stop_loss_myr"],
                            "sector": row["sector"],
                            "pnl_pct": ((row["current_price_myr"] - row["avg_cost_myr"]) / row["avg_cost_myr"] * 100) if row["avg_cost_myr"] > 0 else 0
                        }
                        holdings.append(holding)
                    
                    portfolio_data["holdings"] = holdings
                    
                    # Create formatted holdings summary
                    holdings_text = []
                    for holding in holdings:
                        pnl_sign = "+" if holding["pnl_pct"] >= 0 else ""
                        holdings_text.append(
                            f"• {holding['ticker']} ({holding['company']}) - {holding['sector']}\n"
                            f"  Shares: {holding['shares']:,} | Avg Cost: MYR {holding['avg_cost']:.3f} | "
                            f"Current: MYR {holding['current_price']:.3f}\n"
                            f"  Market Value: MYR {holding['market_value']:,.2f} | "
                            f"P&L: {pnl_sign}{holding['pnl_pct']:.1f}% | "
                            f"Stop Loss: MYR {holding['stop_loss']:.3f}"
                        )
                    
                    portfolio_data["holdings_summary"] = "\n\n".join(holdings_text)
                    
                    # Calculate approximate cash (assuming starting capital)
                    total_invested = sum(h["shares"] * h["avg_cost"] for h in holdings if h["avg_cost"] > 0)
                    portfolio_data["cash_balance"] = max(0, self.config["portfolio"]["starting_capital"] - total_invested)
                    
            # Try to read recent trades
            trades_file = None
            possible_trade_locations = [
                "klse_trades.csv",  # Current directory
                "KLSE_System/klse_trades.csv",  # From project root
                os.path.join(os.path.dirname(__file__), "klse_trades.csv")  # Same directory as script
            ]
            
            for location in possible_trade_locations:
                if os.path.exists(location):
                    trades_file = location
                    break
                    
            if trades_file:
                trades_df = pd.read_csv(trades_file)
                if not trades_df.empty:
                    # Get last 5 trades
                    recent_trades = trades_df.tail(5).to_dict('records')
                    portfolio_data["recent_trades"] = recent_trades
                
        except Exception as e:
            print(f"Warning: Could not read portfolio data: {e}")
            
        return portfolio_data
    
    def generate_weekly_evaluation_prompt(self) -> str:
        """Generate weekly portfolio evaluation prompt"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        portfolio_status = self.get_portfolio_status()
        
        prompt = f"""# KLSE Micro-Cap Weekly Portfolio Evaluation - {current_date}

## Portfolio Performance Review

### Current Portfolio Status:
- Total Equity: MYR {portfolio_status['total_equity']:,.2f}
- Active Positions: {portfolio_status['current_positions']}
- Available Cash: MYR {portfolio_status['cash_balance']:,.2f}
- Maximum Positions Allowed: {self.config['portfolio']['max_positions']}

### Current Holdings:

{portfolio_status['holdings_summary'] if portfolio_status['holdings_summary'] else 'No current holdings in portfolio.'}

### Weekly Evaluation Tasks:

#### 1. Individual Position Analysis
For each current holding, analyze:
- Weekly price performance vs KLCI
- Fundamental developments (earnings, news, announcements)
- Technical chart patterns and volume trends
- Stop-loss proximity and adjustment needs
- Sector-specific trends affecting the stock

#### 2. Portfolio-Level Metrics
- Overall portfolio return this week
- Risk concentration by sector
- Position sizing balance
- Cash utilization efficiency
- Correlation with broader market

#### 3. Risk Management Review
- Positions approaching stop-loss levels
- Concentration risk assessment
- Sector allocation diversification
- Liquidity considerations
- Maximum drawdown analysis

#### 4. Market Context Analysis
- KLCI performance and trends
- Ringgit (MYR) strength/weakness impact
- Sector rotation patterns
- Micro-cap vs large-cap performance
- Economic indicators and policy changes

#### 5. Action Items for Next Week
- Holdings to monitor closely
- Stop-loss adjustments needed
- Position sizing modifications
- Profit-taking opportunities
- New research priorities

### Strategic Questions to Address:
1. Which holdings exceeded expectations this week?
2. Which positions are underperforming and why?
3. Are any holdings approaching fundamental thesis invalidation?
4. What market catalysts should we watch for next week?
5. Should we increase/decrease any position sizes?

### Risk Parameters:
- Market Cap Limit: MYR {self.config['trading_rules']['market_cap_limit']:,}
- Max Position Size: {self.config['risk_management']['max_position_size']*100}%
- Stop-Loss: {self.config['risk_management']['stop_loss_percentage']*100}%

### Deliverables Needed:
1. Performance summary for each holding
2. Overall portfolio assessment vs benchmarks
3. Risk adjustments required
4. Action plan for upcoming week
5. Any position changes recommended

---
*Weekly Evaluation Generated: {current_date}*
        """
        return prompt.strip()
    
    def generate_deep_research_prompt(self) -> str:
        """Generate deep research prompt for new opportunities"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        portfolio_status = self.get_portfolio_status()
        
        prompt = f"""# KLSE Micro-Cap Deep Research Analysis - {current_date}

## Research Objective
Conduct comprehensive analysis to identify high-potential micro-cap opportunities on Bursa Malaysia, considering current portfolio composition and diversification needs.

### Current Portfolio Context:
- Available Cash: MYR {portfolio_status['cash_balance']:,.2f}
- Current Positions: {portfolio_status['current_positions']}/{self.config['portfolio']['max_positions']}
- Total Equity: MYR {portfolio_status['total_equity']:,.2f}

### Current Holdings Summary:
{portfolio_status['holdings_summary'] if portfolio_status['holdings_summary'] else 'No current holdings - building initial portfolio.'}

### Sector Allocation Analysis:
Current sector exposure: {', '.join(set(h['sector'] for h in portfolio_status['holdings'])) if portfolio_status['holdings'] else 'None'}

## Deep Research Framework:

### 1. Diversification Strategy
**Portfolio Gaps to Address:**
- Identify underrepresented sectors in current holdings
- Avoid over-concentration in existing sectors
- Consider correlation with current positions
- Balance growth vs value opportunities

### 2. Market Screening Criteria
**Mandatory Requirements:**
- Market Cap: < MYR {self.config['trading_rules']['market_cap_limit']:,}
- Daily Volume: > {self.config['trading_rules']['minimum_volume']:,} shares
- Exclude Sectors: {', '.join(self.config['trading_rules']['sectors_excluded'])}
- Complement existing portfolio composition

### 3. Fundamental Analysis Deep Dive
**Key Metrics to Research:**
- Revenue growth trends (3-year)
- Profit margins and ROE vs current holdings
- Debt-to-equity ratios (prefer < 0.5)
- Cash flow generation consistency
- Book value vs market value analysis
- Dividend history and sustainability
- Management quality vs portfolio companies

### 4. Business Quality Assessment
**Evaluate Against Portfolio Standards:**
- Management track record comparison
- Competitive advantages/moats strength
- Industry position and market share growth
- Business model sustainability
- ESG considerations and compliance
- Corporate governance quality benchmarking

### 5. Technical Analysis
**Chart Pattern Recognition:**
- Support and resistance levels identification
- Volume trends and accumulation patterns
- Moving average analysis (20/50/200 day)
- RSI and momentum indicators
- Breakout patterns and entry timing
- Relative strength vs KLCI and sector peers

### 6. Strategic Catalysts Research
**High-Priority Catalysts:**
- Upcoming earnings releases (next 30-60 days)
- New contract announcements potential
- Expansion plans or capex initiatives
- Regulatory changes benefiting the company
- Industry tailwinds and adoption trends
- Merger & acquisition potential or rumors

### 7. Portfolio Integration Analysis
**Position Sizing Considerations:**
- Correlation with existing holdings
- Risk contribution to overall portfolio
- Optimal allocation given current cash
- Stop-loss impact on portfolio risk
- Rebalancing requirements

### 8. Comprehensive Risk Assessment
**Multi-Dimensional Risk Analysis:**
- Liquidity risks vs portfolio needs
- Key person dependencies
- Regulatory and compliance risks
- Market concentration vulnerabilities
- Currency exposure implications
- Cyclical sensitivity assessment
- Correlation risks with existing positions

### 9. Valuation Analysis Suite
**Multiple Valuation Methods:**
- P/E ratios vs sector peers and portfolio average
- P/B ratios analysis and book value quality
- EV/EBITDA multiples comparison
- DCF modeling (where applicable)
- Asset-based valuation for asset-heavy companies
- Sum-of-parts analysis for conglomerates
- Relative valuation vs current holdings

## Research Deliverables Required:

### Primary Recommendations:
1. **Top 3-5 new stock recommendations** with detailed analysis
2. **Specific entry price targets** with technical justification
3. **Stop-loss levels** calculated using portfolio risk framework
4. **Optimal position sizing** considering current allocation
5. **Detailed investment thesis** for each (3-4 paragraphs)
6. **Timeline expectations** for thesis realization (3-12 months)

### Supporting Analysis:
7. **Sector diversification impact** on portfolio
8. **Risk-return profile** vs existing holdings
9. **Catalyst calendar** for next 6 months
10. **Alternative opportunities** (backup options)
11. **Exit strategy** considerations

### Risk Documentation:
12. **Comprehensive risk factors** for each recommendation
13. **Mitigation strategies** and monitoring points
14. **Scenario analysis** (best/base/worst case)
15. **Portfolio impact assessment** if positions move against thesis

## Research Sources Framework:
- Bursa Malaysia official announcements and filings
- Company annual reports and quarterly results (latest 3 years)
- Industry research reports and trend analysis
- Broker research notes (where available)
- Economic indicators and policy developments
- Peer company analysis within and outside Malaysia
- Management interviews and corporate presentations

### Priority Sectors for Research Focus:
Consider these sectors for portfolio diversification:
- Technology and digital transformation
- Healthcare and biotechnology
- Sustainable energy and green technology
- Consumer goods and e-commerce
- Industrial automation and manufacturing
- Agricultural technology and food security

---
*Deep Research Session: {current_date}*
*Portfolio-Integrated Analysis*
        """
        return prompt.strip()
    
    def generate_starting_prompt(self) -> str:
        """Generate initial trading system prompt"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        portfolio_status = self.get_portfolio_status()
        
        holdings_section = ""
        if portfolio_status['holdings']:
            holdings_section = f"""### Existing Holdings:
{portfolio_status['holdings_summary']}

"""
        else:
            holdings_section = """### Portfolio Status: 
Starting fresh with no existing positions.

"""
        
        strategy_section = ""
        if portfolio_status['holdings']:
            strategy_section = f"""## Current Portfolio Strategy:

### Immediate Priorities:
Given your current {portfolio_status['current_positions']} positions, focus on:
1. **Portfolio Monitoring**: Track existing holdings performance
2. **Risk Management**: Ensure stop-losses are appropriate
3. **Diversification**: Assess sector concentration and balance
4. **Opportunity Identification**: Research complementary positions
5. **Performance Evaluation**: Benchmark against KLCI

### Available Capital Deployment:
With MYR {portfolio_status['cash_balance']:,.2f} in available cash, consider:
- New position opportunities that complement existing holdings
- Diversification into underrepresented sectors
- Opportunistic additions to high-conviction existing positions (if within risk limits)

"""
        else:
            strategy_section = """## Initial Portfolio Development Strategy:

### Phase 1: Foundation Building (First Month)
1. Conduct comprehensive micro-cap screening across all sectors
2. Identify 15-20 high-quality candidates for deep analysis
3. Perform detailed fundamental and technical analysis
4. Create prioritized watchlist with entry targets

### Phase 2: Initial Positioning (Month 2)
1. Start with 3-4 highest-conviction opportunities
2. Equal weight allocation approach
3. Set disciplined stop-loss levels
4. Monitor market conditions and position performance

### Phase 3: Portfolio Completion (Month 3-4)
1. Gradually add positions (1-2 per month maximum)
2. Reach target of 6-8 diversified positions
3. Maintain sector and risk diversification
4. Adjust strategy based on performance and market conditions

"""
        
        action_focus = ""
        if portfolio_status['holdings']:
            action_focus = f"Review and analyze current {portfolio_status['current_positions']} positions"
        else:
            action_focus = "Begin comprehensive market screening for initial positions"
            
        prompt = f"""# KLSE Micro-Cap Trading System - Initial Setup - {current_date}

## Welcome to KLSE Micro-Cap Trading

You are now managing a systematic micro-cap trading portfolio focused on Bursa Malaysia (KLSE). 

### Current Portfolio Status:
- **Total Equity**: MYR {portfolio_status['total_equity']:,.2f}
- **Active Positions**: {portfolio_status['current_positions']}/{self.config['portfolio']['max_positions']}
- **Available Cash**: MYR {portfolio_status['cash_balance']:,.2f}

{holdings_section}## Trading System Framework:

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
- Strong balance sheets (low debt-to-equity < 0.5)
- Experienced management teams with track record
- Growing or stable industries with tailwinds
- Reasonable valuations (P/E < 15, P/B < 2)
- Good corporate governance and transparency

### 3. Risk Management Framework
- **Position Sizing**: Equal weight approach (~12.5% per position)
- **Maximum Position**: {self.config['risk_management']['max_position_size']*100}% of portfolio
- **Stop-Loss**: {self.config['risk_management']['stop_loss_percentage']*100}% below purchase price
- **Daily Loss Limit**: {self.config['risk_management']['max_daily_loss']*100}% of portfolio value
- **Diversification**: No more than 2 stocks per sector
- **Maximum Positions**: {self.config['portfolio']['max_positions']} concurrent holdings

### 4. Trading Workflow and Discipline
**Weekly Process:**
1. Market and economic environment review
2. Portfolio performance evaluation and metrics
3. Individual stock monitoring and news analysis
4. New opportunity research and screening
5. Position adjustments and rebalancing if needed

**Monthly Deep Dive:**
- Comprehensive fundamental research session
- Industry analysis and competitive landscape review
- New stock discovery and thesis development
- Strategy refinement based on performance

### 5. Performance Benchmarks and Targets
- **Primary Benchmark**: KLCI (FTSE Bursa Malaysia KLCI)
- **Secondary Benchmark**: Small-cap focused indices
- **Return Target**: Outperform benchmarks by 3-5% annually
- **Risk Metric**: Maximum drawdown < 15%
- **Sharpe Ratio Target**: > 0.8

## Malaysian Market Context:

### Economic Environment:
- GDP growth trajectory and economic indicators
- Interest rate environment (OPR trends)
- Inflation dynamics and currency stability
- Government policy initiatives and fiscal measures

### Market Dynamics:
- **Currency**: Ringgit (MYR) strength vs USD and regional currencies
- **Sector Trends**: Technology adoption, ESG focus, infrastructure development
- **Regulatory**: Capital market reforms, foreign investment policies
- **Liquidity**: Market participation and trading volumes

{strategy_section}## Success Metrics and Monitoring:
- **Annual Return Target**: 12-15% (vs KLCI benchmark)
- **Risk-Adjusted Returns**: Sharpe ratio > 0.8
- **Maximum Drawdown**: Keep below 15% at all times
- **Win Rate**: Target >60% of positions to be profitable
- **Sector Diversification**: No single sector >30% of portfolio

## Immediate Action Plan:

### This Week's Priorities:
1. {action_focus}
2. {'Assess portfolio balance and diversification needs' if portfolio_status['holdings'] else 'Research top 10 micro-cap opportunities across sectors'}
3. {'Monitor existing holdings for news and developments' if portfolio_status['holdings'] else 'Prepare detailed investment thesis for top candidates'}
4. {'Identify potential new opportunities for available cash' if portfolio_status['holdings'] else 'Create initial portfolio allocation plan'}
5. {'Review and adjust stop-loss levels if needed' if portfolio_status['holdings'] else 'Set up monitoring and evaluation systems'}

### Research Focus Areas:
- Companies with strong fundamental metrics in growth sectors
- Undervalued opportunities with specific catalysts
- Management teams with proven track records
- Businesses benefiting from structural trends in Malaysia
- Quality companies trading at reasonable valuations

---
*Trading System {'Status Update' if portfolio_status['holdings'] else 'Initialized'}: {current_date}*
*KLSE Micro-Cap Investment Framework Active*
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
