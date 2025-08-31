#!/usr/bin/env python3
"""
Complete KLSE System Runner
Single script to run all KLSE system components
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

def run_command(command, description):
    """Run a command and show status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Complete KLSE System Runner')
    parser.add_argument('--action', choices=['full', 'trading', 'analysis', 'demo'], 
                       default='full', help='What to run')
    
    args = parser.parse_args()
    
    print("🇲🇾 KLSE COMPLETE SYSTEM RUNNER")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.action == 'full' or args.action == 'trading':
        # Run trading engine
        success = run_command(
            "python KLSE_System/klse_trading_engine.py --action daily",
            "KLSE Daily Trading Update"
        )
        
        if args.action == 'trading':
            return
    
    if args.action == 'full' or args.action == 'analysis':
        # Update micro-cap database
        run_command(
            "python KLSE_System/klse_microcap_database.py --action update",
            "KLSE Micro-Cap Database Update"
        )
        
        # Generate visualizations
        run_command(
            "python KLSE_System/klse_visualization.py --action all",
            "KLSE Visualization Generation"
        )
        
        # Show AI recommendations
        run_command(
            "python KLSE_System/klse_microcap_database.py --action recommend --limit 5",
            "KLSE AI Stock Recommendations"
        )
        
        if args.action == 'analysis':
            return
    
    if args.action == 'demo':
        # Run full demo
        print("🎯 Running KLSE Complete Demo...")
        
        commands = [
            ("python KLSE_System/klse_trading_engine.py --action demo", "Trading Engine Demo"),
            ("python KLSE_System/klse_microcap_database.py --action analyze", "Database Analysis"),
            ("python KLSE_System/klse_visualization.py --action all", "Visualization Demo")
        ]
        
        for command, description in commands:
            run_command(command, description)
            print()
    
    print("\n🎉 KLSE System Run Complete!")
    print("\n📊 Generated Files:")
    
    # Check for generated files
    files_to_check = [
        "KLSE_System/klse_portfolio.csv",
        "KLSE_System/klse_trades.csv", 
        "KLSE_System/klse_daily_updates.csv",
        "KLSE_System/klse_microcap_database.csv",
        "KLSE_System/charts/"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                file_count = len([f for f in os.listdir(file_path) if f.endswith('.png')])
                print(f"   ✅ {file_path}: {file_count} charts")
            else:
                print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}: Not found")

if __name__ == "__main__":
    main()
