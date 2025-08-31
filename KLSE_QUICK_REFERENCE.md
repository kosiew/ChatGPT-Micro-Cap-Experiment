# 🚀 KLSE Quick Reference Card

## Daily (2 mins after market close)
```bash
python KLSE_System/klse_trading_engine.py --action daily
```

## Weekly (Sunday mornings)
```bash
# Performance analysis
python run_klse_system.py --action analysis

# AI prompts for strategy review
python KLSE_System/klse_prompt_manager.py
```

## Quick Status Check (anytime)
```bash
python KLSE_System/klse_trading_engine.py --action report
```

## System Demo (testing)
```bash
python run_klse_system.py --action demo
```

## File Locations
- **Portfolio:** `KLSE_System/klse_portfolio.csv`
- **Trades:** `KLSE_System/klse_trades.csv`
- **Charts:** `KLSE_System/charts/`
- **Database:** `KLSE_System/klse_microcap_database.csv`

## Key Features
- ✅ 100% Malaysian stock data coverage
- ✅ Automated stop-loss execution
- ✅ Board lot compliance (100 shares minimum)
- ✅ MYR currency handling
- ✅ Malaysian market hours (9AM-5PM GMT+8)
- ✅ AI prompts with local market context

---
*For full details see: KLSE_WORKFLOWS.md*
