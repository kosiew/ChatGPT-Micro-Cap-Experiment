# ChatGPT Micro-Cap Trading Experiment - AI Coding Agent Instructions

## Project Overview

A dual-market live trading experiment where ChatGPT manages both:

1. **US micro-cap portfolio**: $100 starting capital (June-December 2025)
2. **Malaysian KLSE portfolio**: 10,000 MYR starting capital (2025)

This repo tracks AI-driven trading decisions across both markets, comparing performance against benchmarks like S&P 500, Russell 2000 (US) and KLCI, FBM Small Cap (Malaysia).

## Core Architecture

### US Trading System (`Scripts and CSV Files/`)

#### Trading Engine (`Scripts and CSV Files/Trading_Script.py`)

- **Main function**: `process_portfolio()` - Updates daily positions, applies stop-losses, calculates PnL
- **Data source**: Yahoo Finance via `yfinance` library for real-time pricing
- **Stop-loss automation**: Automatically sells positions when price <= stop_loss threshold
- **CSV output**: Updates `chatgpt_portfolio_update.csv` with daily portfolio snapshots

#### Performance Visualization (`Scripts and CSV Files/Generate_Graph.py`)

- Generates matplotlib charts comparing ChatGPT portfolio vs S&P 500
- **Key pattern**: Uses $100 baseline normalization for fair comparison
- **Data filtering**: Extracts TOTAL rows from portfolio CSV for equity curves
- **Benchmark integration**: Downloads S&P 500 (^SPX) data and scales to $100 starting value

### Malaysian Trading System (`KLSE_System/`)

#### KLSE Trading Engine (`KLSE_System/klse_trading_engine.py`)

- **Modern Typer CLI**: Commands include `buy`, `sell`, `add`, `remove`, `summary`, `ticker`, `daily`, `report`, `demo`
- **Portfolio management**: Automated board lot compliance (100 shares), MYR currency, stop-loss monitoring
- **Ticker conversion**: Converts company names to yfinance-compatible Malaysian tickers (.KL suffix)
- **Data integration**: i3investor.com scraping for company names, sectors, and ticker codes
- **Cash persistence**: JSON config file stores current cash balance across sessions

#### Portfolio Manager (`KLSE_System/klse_portfolio_manager.py`)

- **Malaysian-specific constraints**: Board lots (100 shares minimum), MYR currency with 3-decimal precision
- **Market timing**: Malaysian market hours validation (9:00-17:00 GMT+8)
- **Advanced features**: Position size limits (max 10 positions), cash reserves (500 MYR minimum)
- **Trade methods**: `add_stock_by_quantity()`, `sell_stock_by_quantity()` for precise Malaysian trading

#### Data Sources (`KLSE_System/i3investor_scraper.py`, `redundant_data_fetcher.py`)

- **Web scraping**: i3investor.com for company names, sectors, ticker extraction
- **Redundant data**: Multiple Malaysian stock data sources with Alpha Vantage integration
- **Error handling**: Robust data fetching with fallbacks for Malaysian market data gaps

#### Visualization (`KLSE_System/klse_visualization.py`)

- **Malaysian benchmarks**: Performance vs KLCI, FBM Small Cap indices
- **Sector analysis**: Malaysian sector allocation charts with local market context
- **Charts location**: `KLSE_System/charts/` directory for all generated visualizations

### Data Structure

#### US System

- **Portfolio CSV**: Daily snapshots with columns: Date, Ticker, Shares, Cost Basis, Stop Loss, Current Price, Total Value, PnL, Action, Cash Balance, Total Equity
- **Trade Log CSV**: Transaction history for all buys/sells with PnL calculations
- **TOTAL rows**: Special aggregation rows in portfolio CSV containing portfolio-wide metrics

#### Malaysian System

- **Portfolio CSV** (`KLSE_System/klse_portfolio.csv`): Malaysian positions with board lot tracking, MYR values
- **Trade Log CSV** (`KLSE_System/klse_trades.csv`): Complete transaction history with Malaysian market specifics
- **Config JSON** (`KLSE_System/klse_config.json`): Persistent cash balance, trading parameters, system settings
- **Micro-cap Database** (`KLSE_System/klse_microcap_database.csv`): 17 seed Malaysian stocks with AI scoring
- **Daily Updates** (`KLSE_System/klse_daily_updates.csv`): Daily portfolio snapshots for performance tracking

## Trading Rules & Constraints

### US System

- **Micro-cap only**: Market cap < $300M requirement (enforced through AI prompts, not code)
- **Full shares only**: No fractional positions allowed
- **Stop-loss mandatory**: Each position requires stop-loss level
- **$100 starting capital**: Fixed initial investment
- **6-month timeframe**: June 27, 2025 - December 27, 2025

### Malaysian System

- **Micro-cap only**: Market cap < 300M MYR requirement
- **Board lots**: Minimum 100 shares per transaction (Malaysian standard)
- **MYR currency**: 3-decimal precision for Malaysian Ringgit
- **Stop-loss automated**: 15% below cost basis (configurable)
- **10,000 MYR starting capital**: Initial Malaysian investment
- **Market hours**: 9:00-17:00 GMT+8 validation
- **Position limits**: Maximum 10 active positions, 500 MYR minimum cash reserve

## Key Development Workflows

### US System Daily Portfolio Updates

```python
# Run daily portfolio processing
python "Scripts and CSV Files/Trading_Script.py"
```

### US System Performance Charts

```python
# Create visualization comparing portfolio vs benchmarks
python "Scripts and CSV Files/Generate_Graph.py"
```

### Malaysian System Daily Updates

```bash
# Run KLSE daily processing (Typer CLI)
python KLSE_System/klse_trading_engine.py daily

# Alternative: comprehensive system runner
python run_klse_system.py --action daily
```

### Malaysian System Trading Commands

```bash
# Typer CLI commands for interactive trading
python KLSE_System/klse_trading_engine.py buy "AXIATA" 1000 --stop-loss 4.50
python KLSE_System/klse_trading_engine.py sell "MBMR" 500
python KLSE_System/klse_trading_engine.py summary
python KLSE_System/klse_trading_engine.py ticker "Genting Malaysia"
python KLSE_System/klse_trading_engine.py report
python KLSE_System/klse_trading_engine.py demo
```

### Malaysian System Analysis & Visualization

```bash
# Generate performance charts vs Malaysian benchmarks
python KLSE_System/klse_visualization.py

# Complete system demonstration
python run_klse_system.py --action demo

# Weekly analysis with AI prompts
python KLSE_System/klse_prompt_manager.py
```

### Dependencies

#### US System

Install required packages: `yfinance`, `pandas`, `matplotlib`, `numpy`

#### Malaysian System

Enhanced dependencies in `pyproject.toml`:

- Core: `pandas`, `numpy`, `yfinance`, `requests`, `beautifulsoup4`
- CLI: `typer`, `typing-extensions`
- Visualization: `matplotlib`, `seaborn`
- Data: `alpha-vantage` (optional for enhanced data)

```bash
# Install Malaysian system dependencies
pip install -e .
```

## File Organization Patterns

### Research Documentation

- **Weekly Deep Research (MD/PDF)**: AI's weekly strategy reassessments
- **Experiment Details/**: Trading prompts, Q&A, research methodology
- **Prompts.md**: Critical for understanding AI decision-making framework

### Data Files

- All CSV files in `Scripts and CSV Files/` directory
- Performance image stored in root directory (e.g., `(6-30 - 7-25) Results.png`)

## AI Decision Framework

### US System

- **Weekly deep research**: AI can research new positions and reassess portfolio
- **Daily updates**: Position monitoring with automated stop-loss execution
- **Prompt structure**: Specific prompts in `Experiment Details/Prompts.md` guide AI behavior
- **Thesis tracking**: Each week's research includes summary for next week's context

### Malaysian System

- **Dual-market strategy**: AI manages both US and Malaysian portfolios simultaneously
- **Local market context**: Malaysian economic indicators, BNM policy, sector dynamics
- **AI prompts system**: `KLSE_System/klse_prompt_manager.py` generates weekly Malaysian market prompts
- **Micro-cap database**: 17 seed stocks with AI scoring for systematic selection
- **Market-specific rules**: Board lots, Malaysian market hours, local regulations

## Critical Code Patterns

### Portfolio Processing

- Always check for empty `yfinance` data before price calculations
- TOTAL row aggregation is essential for performance tracking
- Stop-loss triggers generate both portfolio updates and trade log entries

### Data Handling

- CSV files are continuously appended, not overwritten
- Date-based deduplication prevents duplicate entries
- Portfolio positions can be modified between script runs

### Malaysian Market Specifics

#### Ticker Conversion

- Company names → yfinance format: Add `.KL` suffix (e.g., "AXIATA" → "AXIATA.KL")
- Use `get_yfinance_ticker()` method in trading engine
- i3investor.com scraping for company name/sector extraction

#### Board Lot Management

- All Malaysian trades must be in multiples of 100 shares
- Portfolio manager enforces board lot compliance automatically
- Cash calculations account for board lot constraints

#### Cash Persistence

- JSON config file (`klse_config.json`) stores current cash balance
- Cash balance persists across trading sessions
- Automatic cash injection when balance drops below minimum reserves

#### Error Handling Patterns

- Zero cost basis positions (bonus shares): Use `float('inf')` for infinite returns
- Type consistency: Always convert tickers to strings for API calls
- DataFrame updates: Use column-wise assignment to avoid dimension mismatches

## Performance Benchmarking

- S&P 500 (^SPX) is primary benchmark
- Russell 2000 (^RUT) for small-cap comparison
- All comparisons normalized to $100 starting investment
- Performance metrics include drawdown analysis and percentage returns

When working with this codebase, focus on maintaining data integrity in the CSV files and ensuring the daily portfolio processing workflow remains robust for the live trading experiment.
