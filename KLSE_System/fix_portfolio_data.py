#!/usr/bin/env python3
"""
Portfolio Data Correction Tool
Fixes corrupted stop loss values in KLSE portfolio CSV
"""

import pandas as pd
import os
from datetime import datetime

def fix_portfolio_data():
    """Fix corrupted stop loss values in portfolio"""
    
    portfolio_file = "KLSE_System/klse_portfolio.csv"
    backup_file = f"KLSE_System/klse_portfolio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not os.path.exists(portfolio_file):
        print(f"❌ Portfolio file not found: {portfolio_file}")
        return
    
    # Backup original file
    df = pd.read_csv(portfolio_file)
    df.to_csv(backup_file, index=False)
    print(f"✅ Backup created: {backup_file}")
    print()
    
    print("=" * 80)
    print("PORTFOLIO DATA CORRECTION")
    print("=" * 80)
    print()
    
    corrections_made = 0
    
    for idx, row in df.iterrows():
        ticker = row['ticker']
        cost_basis = row['avg_cost_myr']
        stop_loss = row['stop_loss_myr']
        company = row.get('company_name', ticker)
        
        needs_correction = False
        
        # Check if stop loss is invalid
        if cost_basis <= 0:
            print(f"⚠️  {ticker} ({company})")
            print(f"   CRITICAL: Invalid cost basis: {cost_basis:.3f} MYR")
            print(f"   ❌ CANNOT AUTO-FIX: Manual review required")
            print(f"      Please provide correct cost basis for this position")
            print()
            continue
        
        if stop_loss >= cost_basis or stop_loss <= 0:
            needs_correction = True
            correct_stop_loss = cost_basis * 0.85  # 15% below cost
            
            print(f"🔧 {ticker} ({company})")
            print(f"   Cost Basis: {cost_basis:.3f} MYR")
            print(f"   OLD Stop Loss: {stop_loss:.3f} MYR ❌")
            print(f"   NEW Stop Loss: {correct_stop_loss:.3f} MYR ✅ (15% below cost)")
            
            # Apply correction
            df.at[idx, 'stop_loss_myr'] = round(correct_stop_loss, 3)
            corrections_made += 1
            print()
        
        elif cost_basis > 0:
            # Check if stop loss ratio is suspicious
            stop_loss_ratio = stop_loss / cost_basis
            
            if stop_loss_ratio < 0.70 or stop_loss_ratio > 0.95:
                correct_stop_loss = cost_basis * 0.85
                
                print(f"⚠️  {ticker} ({company})")
                print(f"   Cost Basis: {cost_basis:.3f} MYR")
                print(f"   Current Stop Loss: {stop_loss:.3f} MYR ({stop_loss_ratio:.1%} of cost)")
                print(f"   Recommended: {correct_stop_loss:.3f} MYR (85% of cost)")
                print(f"   ℹ️  Outside normal range (70-95%) - review recommended")
                print()
    
    if corrections_made > 0:
        # Save corrected data
        df.to_csv(portfolio_file, index=False)
        print("=" * 80)
        print(f"✅ CORRECTIONS APPLIED: {corrections_made} position(s) fixed")
        print(f"   Updated file: {portfolio_file}")
        print(f"   Backup saved: {backup_file}")
        print("=" * 80)
    else:
        print("=" * 80)
        print("ℹ️  No automatic corrections applied")
        print("   Some positions require manual review")
        print("=" * 80)
    
    # Show summary
    print()
    print("SUMMARY:")
    print(f"  Total positions: {len(df)}")
    print(f"  Auto-corrected: {corrections_made}")
    print(f"  Needs manual review: Check positions with cost_basis=0 or suspicious ratios")
    print()

if __name__ == "__main__":
    fix_portfolio_data()
