# 🔄 KLSE Trading System - Workflows & Frequencies

## Overview
This guide provides clear workflows for operating the KLSE (Malaysian) trading system with recommended frequencies and automated options.

---

## 🗓️ **DAILY WORKFLOWS**

### 1. Daily Portfolio Update
**Frequency:** Every trading day  
**Time:** After Malaysian market close (5:00 PM GMT+8)  
**Duration:** 2-3 minutes

```bash
# Single command - full daily update
python KLSE_System/klse_trading_engine.py --action daily
```

**What it does:**
- Updates all position prices
- Checks stop-loss triggers (auto-sells if needed)
- Calculates daily PnL and portfolio value
- Logs all trades and performance
- Updates daily performance CSV

**Output files updated:**
- `KLSE_System/klse_daily_updates.csv`
- `KLSE_System/klse_performance_log.csv`
- `KLSE_System/klse_portfolio.csv` (if stop-losses triggered)
- `KLSE_System/klse_trades.csv` (if trades executed)

---

### 2. Quick Portfolio Status Check
**Frequency:** As needed during trading day  
**Duration:** 30 seconds

```bash
# Generate current report
python KLSE_System/klse_trading_engine.py --action report
```

**What it shows:**
- Current portfolio value and return
- Active positions and PnL
- Available cash and position slots
- Market status (open/closed)

---

## 📊 **WEEKLY WORKFLOWS**

### 3. Weekly Performance Analysis
**Frequency:** Every Sunday  
**Time:** Weekend preparation for next week  
**Duration:** 5-10 minutes

```bash
# Complete weekly analysis
python run_klse_system.py --action analysis
```

**What it does:**
- Updates micro-cap database with latest prices
- Generates performance charts vs KLCI benchmarks
- Creates sector allocation analysis
- Shows top AI stock recommendations

**Output files generated:**
- `KLSE_System/charts/klse_performance_*.png`
- `KLSE_System/charts/klse_allocation_*.png`
- Updated `KLSE_System/klse_microcap_database.csv`

---

### 4. AI Strategy Review (Malaysian Focus)
**Frequency:** Weekly (Sundays)  
**Duration:** AI decision session (30-60 minutes)

```bash
# Generate Malaysian market-focused AI prompts
python KLSE_System/klse_prompt_manager.py
```

**Complete AI Workflow:**
1. **Generate Prompts:** Run the command above to get ready-to-use prompts
2. **Copy Generated Prompts:** The script outputs prompts ready for ChatGPT
3. **Paste into ChatGPT:** Use the generated prompts directly 
4. **Get AI Decisions:** ChatGPT analyzes with Malaysian market context
5. **Execute Trades:** Implement AI recommendations through trading engine

**Sample Generated Prompts Include:**
- Current portfolio status (your 13 positions, MYR 203,889 value)
- Malaysian market conditions and BNM policy updates
- Sector analysis (telecommunications, banking, real estate, etc.)
- Risk management with 5% stop-loss strategy
- Board lot compliance for KLSE trading
- Economic indicators and currency considerations

**AI Decision Types:**
- BUY: New micro-cap positions under MYR 300M market cap
- SELL: Exit underperforming positions
- HOLD: Maintain current positions with stop-loss adjustments
- REBALANCE: Sector allocation optimization

---

## 🔄 **BI-WEEKLY WORKFLOWS**

### 5. System Health Check
**Frequency:** Every 2 weeks  
**Duration:** 5 minutes

```bash
# Check both US and KLSE system status
python trading_system_manager.py --action status

# Compare performance between systems
python trading_system_manager.py --action compare
```

**What it checks:**
- Data source reliability and performance
- File integrity and backup status
- System switching capabilities
- Performance comparison US vs Malaysian systems

---

## 🗃️ **MONTHLY WORKFLOWS**

### 6. Database Maintenance
**Frequency:** Monthly (1st Sunday)  
**Duration:** 10-15 minutes

```bash
# Update full micro-cap database
python KLSE_System/klse_microcap_database.py --action update

# Rebuild stock universe for AI
python KLSE_System/klse_microcap_database.py --action universe
```

**What it does:**
- Refreshes all 17 seed stocks data
- Recalculates AI scoring for all stocks
- Updates sector classifications
- Generates fresh stock universe for AI selection

---

### 7. System Backup
**Frequency:** Monthly  
**Duration:** 2 minutes

```bash
# Backup KLSE system data
python trading_system_manager.py --action backup --system KLSE
```

**What it backs up:**
- All portfolio and trade history
- Configuration files
- Generated charts and analysis
- Database files

---

## ⚡ **AUTOMATED WORKFLOWS**

### 8. Complete System Demo (Testing)
**Frequency:** As needed for testing  
**Duration:** 5 minutes

```bash
# Full system demonstration
python run_klse_system.py --action demo
```

**What it does:**
- Runs trading engine demo
- Updates database analysis
- Generates all visualizations
- Shows comprehensive system status

---

### 9. Dual System Management
**Frequency:** As needed

```bash
# Switch between US and Malaysian systems
python trading_system_manager.py --action switch --system KLSE
python trading_system_manager.py --action switch --system US

# Run both systems simultaneously
python trading_system_manager.py --action dual-update
```

---

## 📋 **WORKFLOW PRIORITY MATRIX**

### 🔴 **CRITICAL (Must Do)**
| Workflow | Frequency | Command |
|----------|-----------|---------|
| Daily Portfolio Update | Daily | `python KLSE_System/klse_trading_engine.py --action daily` |
| AI Strategy Review | Weekly | `python KLSE_System/klse_prompt_manager.py` + AI session |

### 🟡 **IMPORTANT (Should Do)**
| Workflow | Frequency | Command |
|----------|-----------|---------|
| Weekly Performance Analysis | Weekly | `python run_klse_system.py --action analysis` |
| System Health Check | Bi-weekly | `python trading_system_manager.py --action status` |

### 🟢 **OPTIONAL (Nice to Have)**
| Workflow | Frequency | Command |
|----------|-----------|---------|
| Database Maintenance | Monthly | `python KLSE_System/klse_microcap_database.py --action update` |
| System Backup | Monthly | `python trading_system_manager.py --action backup --system KLSE` |
| Quick Status Check | As needed | `python KLSE_System/klse_trading_engine.py --action report` |

---

## 🕒 **RECOMMENDED SCHEDULE**

### **Daily (2-3 minutes)**
- **5:30 PM GMT+8:** Run daily portfolio update after market close

### **Weekly (30-60 minutes)**
- **Sunday 10:00 AM:** Weekly performance analysis
- **Sunday 11:00 AM:** AI strategy review session with Malaysian prompts

### **Bi-weekly (5 minutes)**
- **1st & 3rd Sunday:** System health check and performance comparison

### **Monthly (15 minutes)**
- **1st Sunday:** Database maintenance and system backup

---

## 🚀 **QUICK START COMMANDS**

```bash
# Today's essential: Daily update after market close
python KLSE_System/klse_trading_engine.py --action daily

# This weekend: Weekly analysis + AI prompts
python run_klse_system.py --action analysis
python KLSE_System/klse_prompt_manager.py

# Right now: Check current status
python KLSE_System/klse_trading_engine.py --action report

# Initial setup: Run baseline analysis (first time only)
python run_klse_system.py --action demo
```

## 📋 **AI PROMPT WORKFLOW**

### Step 1: Generate Current Context
```bash
python KLSE_System/klse_prompt_manager.py
```

### Step 2: Copy Output to ChatGPT
The script generates ready-to-use prompts like:

**Portfolio Review Prompt:**
```
You are managing a Malaysian equity portfolio worth MYR 203,889 with 13 positions...
[Current holdings with stop-losses, market context, sector analysis]
Based on Malaysian market conditions, recommend BUY/SELL/HOLD decisions...
```

**Deep Research Prompt:**
```
Research Malaysian micro-cap stocks (market cap < MYR 300M) considering:
- Bursa Malaysia regulations and board lot requirements
- Bank Negara Malaysia monetary policy
- Sector trends in telecommunications, banking, real estate...
```

### Step 3: Get AI Recommendations
Paste prompts into ChatGPT and get specific trading decisions

### Step 4: Execute Decisions
Use trading engine to implement AI recommendations

---

## ⚠️ **IMPORTANT NOTES**

1. **Market Hours:** Malaysian market (9:00 AM - 5:00 PM GMT+8)
2. **Weekends:** No daily updates needed, perfect for weekly analysis
3. **Holidays:** Check Malaysian public holidays, skip daily updates
4. **AI Sessions:** Use Malaysian market prompts for context-aware decisions
5. **Data Reliability:** System has redundant data sources, 100% reliability achieved

---

## 🎯 **MINIMAL VIABLE ROUTINE**

If you only want to do the absolute minimum:

```bash
# Once per day (after market close)
python KLSE_System/klse_trading_engine.py --action daily

# Once per week (Sunday) - Analysis + AI Session
python run_klse_system.py --action analysis
python KLSE_System/klse_prompt_manager.py
# Copy generated prompts → Paste into ChatGPT → Get trading decisions
```

**Complete Weekly AI Session (15 minutes):**
1. **Generate prompts** (30 seconds)
2. **Copy to ChatGPT** (30 seconds) 
3. **AI analysis** (10 minutes)
4. **Execute decisions** (4 minutes)

This covers 80% of the system's value with minimal time investment!

---

*Last Updated: August 31, 2025*  
*System Status: Production Ready* 🚀
