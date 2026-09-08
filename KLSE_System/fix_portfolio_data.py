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
        # Stops trail the high-water mark, so that - not the cost basis - is
        # what a stop must be checked against. Anchoring to cost here would
        # reset every trailing stop that has ratcheted up on a winner.
        trail_pct = float(row.get('trail_pct') or 15.0)
        highest = float(row.get('highest_price_myr') or 0) or cost_basis
        
        needs_correction = False
        
        # Check if stop loss is invalid
        if cost_basis <= 0:
            print(f"⚠️  {ticker} ({company})")
            print(f"   CRITICAL: Invalid cost basis: {cost_basis:.3f} MYR")
            print(f"   ❌ CANNOT AUTO-FIX: Manual review required")
            print(f"      Please provide correct cost basis for this position")
            print()
            continue
        
        if stop_loss >= highest or stop_loss <= 0:
            needs_correction = True
            correct_stop_loss = highest * (1 - trail_pct / 100)
            
            print(f"🔧 {ticker} ({company})")
            print(f"   High-Water Mark: {highest:.3f} MYR (cost basis {cost_basis:.3f} MYR)")
            print(f"   OLD Stop Loss: {stop_loss:.3f} MYR ❌")
            print(f"   NEW Stop Loss: {correct_stop_loss:.3f} MYR ✅ "
                  f"({trail_pct:.0f}% below the high-water mark)")
            
            # Apply correction
            df.at[idx, 'stop_loss_myr'] = round(correct_stop_loss, 3)
            corrections_made += 1
            print()
        
        elif highest > 0:
            # Check whether the stop still matches the configured trail
            stop_loss_ratio = stop_loss / highest
            expected_ratio = 1 - trail_pct / 100
            
            if abs(stop_loss_ratio - expected_ratio) > 0.05:
                correct_stop_loss = highest * expected_ratio
                
                print(f"⚠️  {ticker} ({company})")
                print(f"   High-Water Mark: {highest:.3f} MYR")
                print(f"   Current Stop Loss: {stop_loss:.3f} MYR ({stop_loss_ratio:.1%} of the high)")
                print(f"   Recommended: {correct_stop_loss:.3f} MYR ({expected_ratio:.0%} of the high)")
                print(f"   ℹ️  Does not match the {trail_pct:.0f}% trail - review recommended")
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
