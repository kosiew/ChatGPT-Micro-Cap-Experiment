#!/usr/bin/env python3
"""
Complete KLSE System Runner
Single script to run all KLSE system components
"""

import os
import sys
import subprocess
from datetime import datetime
from typing import Annotated, Optional
import typer

# Configuration
SHOW_AI_RECOMMENDATIONS = False  # Set to True to show rule-based AI recommendations

app = typer.Typer(
    name="klse-system",
    help="🇲🇾 Complete KLSE System Runner - Manage Malaysian stock trading and analysis",
    rich_markup_mode="rich"
)

def run_command(command: str, description: str) -> bool:
    """Run a command and show status"""
    typer.echo(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            typer.echo(f"✅ {description} completed successfully")
            if result.stdout.strip():
                typer.echo(result.stdout)
            return True
        else:
            typer.echo(f"❌ {description} failed: {result.stderr}", err=True)
            return False
    except Exception as e:
        typer.echo(f"❌ {description} error: {e}", err=True)
        return False

def show_header():
    """Display system header"""
    typer.echo("🇲🇾 KLSE COMPLETE SYSTEM RUNNER")
    typer.echo("=" * 50)
    typer.echo(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    typer.echo()

def show_generated_files():
    """Show status of generated files"""
    typer.echo("\n🎉 KLSE System Run Complete!")
    typer.echo("\n📊 Generated Files:")
    
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
                typer.echo(f"   ✅ {file_path}: {file_count} charts")
            else:
                typer.echo(f"   ✅ {file_path}")
        else:
            typer.echo(f"   ❌ {file_path}: Not found")

@app.command("full")
def run_full_system(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Run the complete KLSE system (trading + analysis + visualizations)"""
    show_header()
    
    # Run trading engine
    success = run_command(
        f"python KLSE_System/klse_trading_engine.py daily{' --alpha-vantage-key ' + alpha_vantage_key if alpha_vantage_key else ''}",
        "KLSE Daily Trading Update"
    )
    
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
    
    # Show AI recommendations (optional - rule-based only)
    if SHOW_AI_RECOMMENDATIONS:
        run_command(
            "python KLSE_System/klse_microcap_database.py --action recommend --limit 5",
            "KLSE AI Stock Recommendations"
        )
    else:
        typer.echo("ℹ️  Skipping rule-based AI recommendations (SHOW_AI_RECOMMENDATIONS=False)")
    
    show_generated_files()

@app.command("trading")
def run_trading_only(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Run only the trading engine (daily processing)"""
    show_header()
    
    success = run_command(
        f"python KLSE_System/klse_trading_engine.py daily{' --alpha-vantage-key ' + alpha_vantage_key if alpha_vantage_key else ''}",
        "KLSE Daily Trading Update"
    )
    
    show_generated_files()

@app.command("analysis")
def run_analysis_only():
    """Run only analysis and visualizations (no trading)"""
    show_header()
    
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
    
    # Show AI recommendations (optional - rule-based only)
    if SHOW_AI_RECOMMENDATIONS:
        run_command(
            "python KLSE_System/klse_microcap_database.py --action recommend --limit 5",
            "KLSE AI Stock Recommendations"
        )
    else:
        typer.echo("ℹ️  Skipping rule-based AI recommendations (SHOW_AI_RECOMMENDATIONS=False)")
    
    show_generated_files()

@app.command("demo")
def run_demo():
    """Run complete system demo with all components"""
    show_header()
    typer.echo("🎯 Running KLSE Complete Demo...")
    
    commands = [
        ("python KLSE_System/klse_trading_engine.py demo", "Trading Engine Demo"),
        ("python KLSE_System/klse_microcap_database.py --action analyze", "Database Analysis"),
        ("python KLSE_System/klse_visualization.py --action all", "Visualization Demo")
    ]
    
    for command, description in commands:
        run_command(command, description)
        typer.echo()
    
    show_generated_files()

@app.command("status")
def show_status():
    """Show current system status and generated files"""
    show_header()
    show_generated_files()

@app.command("summary")
def show_summary(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Show trading portfolio summary"""
    show_header()
    
    success = run_command(
        f"python KLSE_System/klse_trading_engine.py summary{' --alpha-vantage-key ' + alpha_vantage_key if alpha_vantage_key else ''}",
        "Portfolio Summary"
    )

@app.command("buy")
def buy_stock(
    ticker: Annotated[str, typer.Argument(help="Stock ticker (e.g., gamuda, 1155)")],
    shares: Annotated[int, typer.Argument(help="Number of shares to buy")],
    price: Annotated[float, typer.Argument(help="Price per share in MYR")],
    stop_loss: Annotated[float, typer.Option("--stop-loss", "-s", help="Stop loss percentage")] = 15.0,
    reason: Annotated[str, typer.Option("--reason", "-r", help="Reason for purchase")] = "Manual buy",
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Buy shares of a stock"""
    command = f"python KLSE_System/klse_trading_engine.py buy {ticker} {shares} {price}"
    if stop_loss != 15.0:
        command += f" --stop-loss {stop_loss}"
    if reason != "Manual buy":
        command += f" --reason '{reason}'"
    if alpha_vantage_key:
        command += f" --alpha-vantage-key {alpha_vantage_key}"
    
    run_command(command, f"Buying {shares} shares of {ticker}")

@app.command("sell")
def sell_stock(
    ticker: Annotated[str, typer.Argument(help="Stock ticker to sell")],
    shares: Annotated[int, typer.Argument(help="Number of shares to sell")],
    price: Annotated[float, typer.Argument(help="Price per share in MYR")],
    reason: Annotated[str, typer.Option("--reason", "-r", help="Reason for sale")] = "Manual sale",
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Sell shares of a stock"""
    command = f"python KLSE_System/klse_trading_engine.py sell {ticker} {shares} {price}"
    if reason != "Manual sale":
        command += f" --reason '{reason}'"
    if alpha_vantage_key:
        command += f" --alpha-vantage-key {alpha_vantage_key}"
    
    run_command(command, f"Selling {shares} shares of {ticker}")

@app.command("build")
def build_database(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None
):
    """Build initial micro-cap database from seed stocks (first-time setup)"""
    show_header()
    typer.echo("🏗️  Building KLSE Micro-Cap Database from Seed Stocks...")
    typer.echo("This will create:")
    typer.echo("   - KLSE_System/klse_microcap_database.csv")
    typer.echo("   - KLSE_System/klse_microcap_analysis.csv")
    typer.echo("   - KLSE_System/klse_sectors.json")
    typer.echo()
    
    command = "python KLSE_System/klse_microcap_database.py --action build"
    if alpha_vantage_key:
        command += f" --alpha-vantage-key {alpha_vantage_key}"
    
    success = run_command(command, "Building Database")
    
    if success:
        typer.echo("\n✅ Database built successfully!")
        typer.echo("You can now run: python run_klse_system.py full")
    
    show_generated_files()

if __name__ == "__main__":
    app()
