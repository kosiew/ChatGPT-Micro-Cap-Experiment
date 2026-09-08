# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
A live trading experiment where ChatGPT manages a $100 micro-cap portfolio from June-December 2025. The project tracks AI-driven trading decisions against market benchmarks.

## Key Commands

### Trading Scripts
- **Update portfolio**: `python "Scripts and CSV Files/Trading_Script.py"` - Updates daily positions and calculates PnL
- **Generate performance chart**: `python "Scripts and CSV Files/Generate_Graph.py" - Creates matplotlib visualization comparing ChatGPT vs S&P 500

### Development Setup
Dependencies: `yfinance`, `pandas`, `matplotlib`, `numpy`

## Architecture

### Core Components
- **Trading_Script.py**: Main trading engine with stop-loss automation and daily reporting
- **Generate_Graph.py**: Performance visualization comparing portfolio vs benchmarks
- **CSV Files**: `chatgpt_portfolio_update.csv` (daily positions) and `chatgpt_trade_log.csv` (transaction history)

### Key Functions
- `process_portfolio()`: Updates positions, applies stop-losses, calculates totals
- `daily_results()`: Generates daily performance metrics (Sharpe, Sortino ratios)
- `log_manual_buy/sell()`: Manual trade logging with validation

### Data Sources
- Real-time data: Yahoo Finance via `yfinance` library
- Benchmarks: S&P 500 (^SPX), Russell 2000 (^RUT), IWO, XBI

## File Structure
- **Scripts and CSV Files/**: Trading logic and data storage
- **Weekly Deep Research/**: Weekly AI research reports (PDF and MD formats)
- **Experiment Details/**: Trading prompts, Q&A, research index

## Trading Rules
- Micro-cap stocks only (market cap < $300M)
- Full-share positions only
- Strict trailing stop-loss implementation (trails the high-water mark, not the purchase price)
- Weekly deep research allowed for strategy adjustments
- $100 starting capital, 6-month timeframe