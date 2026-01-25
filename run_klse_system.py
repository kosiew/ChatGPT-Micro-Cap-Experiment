#!/usr/bin/env python3
"""
Complete KLSE System Runner
Single script to run all KLSE system components
"""

import os
import sys
import subprocess
import csv
from datetime import datetime
from typing import Annotated, Optional
from pathlib import Path
import typer

# yfinance will be imported lazily in get_current_price() to avoid heavy imports at module import time
# (avoids importing pandas etc. when running --help)

# Configuration
SHOW_AI_RECOMMENDATIONS = False  # Set to True to show rule-based AI recommendations
UPDATE_MICROCAP_DATABASE = False  # Set to True to update micro-cap database (updates stock prices in database)

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


# --- Watched counters helpers ---
WATCHED_FILE = "KLSE_System/klse_watched.csv"


def ensure_watched_file():
    """Ensure watched file exists with header"""
    parent = Path(WATCHED_FILE).parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    if not Path(WATCHED_FILE).exists():
        with open(WATCHED_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Add display_name column to store friendly label like 'GAMUDA'
            writer.writerow(["date_added","ticker","display_name","interested_price_myr","notes"])


def load_ticker_mappings() -> dict:
    """Load mappings from ticker_mappings.json if present"""
    try:
        p = Path('ticker_mappings.json')
        if p.exists():
            with open(p, encoding='utf-8') as f:
                return {k.upper(): v for k, v in __import__('json').load(f).items()}
    except Exception:
        pass
    return {}


def _normalize_ticker(ticker: str) -> str:
    """Normalize user input into a yfinance-compatible ticker like '4723.KL' or 'GAMUDA.KL'.
    Attempts multiple resolution strategies:
     - numeric code -> code.KL
     - ticker_mappings.json -> code
     - exact .KL provided -> use upper
     - match ticker or company name in klse_microcap_database.csv
     - fallback to upper + .KL
    """
    t = ticker.strip()
    mappings = load_ticker_mappings()
    up = t.upper()

    # numeric
    if t.isdigit():
        return f"{t}.KL"

    # mapping like AXIATA -> 6888
    if up in mappings:
        return f"{mappings[up]}.KL"

    # if already formatted
    if up.endswith('.KL'):
        return up

    # try to find in microcap database by exact ticker or by company name containing the token
    db_path = Path('KLSE_System/klse_microcap_database.csv')
    prefix = up
    if db_path.exists():
        try:
            with open(db_path, newline='', encoding='utf-8') as f:
                r = csv.DictReader(f)
                for row in r:
                    # match by ticker prefix
                    if row.get('ticker') and row.get('ticker').split('.')[0].upper() == prefix:
                        return row.get('ticker')
                    # match by stock_code equals prefix
                    if row.get('stock_code') and row.get('stock_code') == prefix:
                        return f"{prefix}.KL"
                    # match by company name containing the token
                    cname = row.get('company_name','').upper()
                    if prefix in cname.split():
                        return row.get('ticker') or f"{row.get('stock_code')}.KL"
        except Exception:
            pass

    # fallback
    return up + '.KL'


def _derive_display_name_from_database(ticker: str) -> str:
    """Try to get a friendly display name (e.g., GAMUDA) from the microcap database.
    Falls back to the ticker prefix (before the dot).
    """
    # ticker expected in yfinance format like '4723.KL' or 'GAMUDA.KL'
    prefix = ticker.split('.')[0].upper()
    db_path = Path('KLSE_System/klse_microcap_database.csv')
    if db_path.exists():
        try:
            with open(db_path, newline='', encoding='utf-8') as f:
                r = csv.DictReader(f)
                for row in r:
                    # match by stock_code or ticker (both can be present)
                    if row.get('stock_code') and row.get('stock_code') == prefix:
                        # try to return a short symbol derived from company name or ticker
                        cname = row.get('company_name','').strip()
                        if cname:
                            return ''.join(ch for ch in cname.split()[0].upper() if ch.isalnum())
                    if row.get('ticker') and row.get('ticker').split('.')[0].upper() == prefix:
                        cname = row.get('company_name','').strip()
                        if cname:
                            return ''.join(ch for ch in cname.split()[0].upper() if ch.isalnum())
        except Exception:
            pass
    # Fallback to prefix
    return prefix


def add_watch_entry(ticker: str, interested_price: float, notes: str = ""):
    """Add or update a watch entry"""
    ensure_watched_file()
    rows = []
    updated = False
    ticker_norm = _normalize_ticker(ticker)
    display_name = _derive_display_name_from_database(ticker_norm)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Read existing rows
    with open(WATCHED_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            # normalize missing display_name for compatibility with older files
            if 'display_name' not in r:
                r['display_name'] = ''
            if r["ticker"].lower() == ticker_norm.lower():
                r["interested_price_myr"] = f"{interested_price}"
                r["date_added"] = now
                r["notes"] = notes
                r["display_name"] = display_name
                updated = True
            rows.append(r)
    if not updated:
        rows.append({"date_added": now, "ticker": ticker_norm, "display_name": display_name, "interested_price_myr": f"{interested_price}", "notes": notes})
    # Write back
    with open(WATCHED_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["date_added","ticker","display_name","interested_price_myr","notes"])
        writer.writeheader()
        writer.writerows(rows)

def load_watched_counters():
    ensure_watched_file()
    with open(WATCHED_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        # ensure backwards compatibility
        for r in rows:
            if 'display_name' not in r:
                r['display_name'] = ''
        return rows


def get_current_price(ticker: str):
    """Return latest close price using yfinance or None on failure"""
    try:
        import yfinance as yf_local
    except Exception:
        return None
    try:
        tk = yf_local.Ticker(ticker)
        hist = tk.history(period='1d')
        if hist is not None and not hist.empty:
            return float(hist['Close'].iloc[-1])
        # fallback
        info = tk.info if hasattr(tk, 'info') else {}
        price = info.get('regularMarketPrice') if info else None
        return float(price) if price is not None else None
    except Exception:
        return None


def show_watched_section():
    watched = load_watched_counters()
    if not watched:
        typer.echo("\n🔭 Watched Counters: None")
        return
    typer.echo("\n🔭 Watched Counters:")
    for w in watched:
        ticker = w.get("ticker")
        display = w.get("display_name") or (ticker.split('.')[0] if ticker else "")
        try:
            interested = float(w.get("interested_price_myr", ''))
        except Exception:
            interested = None
        current = get_current_price(ticker) if ticker else None
        if current is None or interested is None:
            typer.echo(f"   • {display} ({ticker}) - target: {w.get('interested_price_myr')} MYR - current: N/A")
        else:
            delta = current - interested
            pct = (delta / interested) * 100 if interested != 0 else 0
            sign = "+" if delta >= 0 else "-"
            typer.echo(f"   • {display} ({ticker}) - target: {interested:.3f} MYR - current: {current:.3f} MYR ({sign}{abs(delta):.3f} MYR, {sign}{abs(pct):.2f}%)")

# --- End watched helpers ---

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
    
    # Update micro-cap database (optional)
    if UPDATE_MICROCAP_DATABASE:
        run_command(
            "python KLSE_System/klse_microcap_database.py --action update",
            "KLSE Micro-Cap Database Update"
        )
    else:
        typer.echo("ℹ️  Skipping micro-cap database update (UPDATE_MICROCAP_DATABASE=False)")
    
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
    
    # Show watched counters summary
    show_watched_section()

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
    
    # Update micro-cap database (optional)
    if UPDATE_MICROCAP_DATABASE:
        run_command(
            "python KLSE_System/klse_microcap_database.py --action update",
            "KLSE Micro-Cap Database Update"
        )
    else:
        typer.echo("ℹ️  Skipping micro-cap database update (UPDATE_MICROCAP_DATABASE=False)")
    
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


# Watch command group (subcommands: add, list, remove)
watch_app = typer.Typer(help="Manage watched counters")
app.add_typer(watch_app, name="watch")

@watch_app.command("add")
def watch_add(
    counter: Annotated[str, typer.Argument(help="Stock ticker or symbol to watch (e.g., GAMUDA, JAKS, or 4723)")],
    interested_put_price: Annotated[float, typer.Argument(help="Interested put price in MYR")],
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="Optional notes")] = None
):
    """Add or update a watched counter"""
    ticker_norm = _normalize_ticker(counter)
    add_watch_entry(ticker_norm, interested_put_price, notes or "")
    typer.echo(f"✅ Added/Updated watch for {ticker_norm} at target {interested_put_price:.3f} MYR")
    show_watched_section()


def show_watched_list():
    """Print a numbered list of watched counters with details"""
    rows = load_watched_counters()
    if not rows:
        typer.echo("\n🔭 Watched Counters: None")
        return
    typer.echo("\n🔭 Watched Counters:")
    for i, r in enumerate(rows, start=1):
        ticker = r.get('ticker')
        display = r.get('display_name') or (ticker.split('.')[0] if ticker else '')
        notes = r.get('notes','')
        try:
            interested = float(r.get('interested_price_myr',''))
        except Exception:
            interested = None
        current = get_current_price(ticker) if ticker else None
        if current is None or interested is None:
            typer.echo(f" {i:>2}) {display} ({ticker}) - target: {r.get('interested_price_myr')} MYR - current: N/A - {notes}")
        else:
            delta = current - interested
            pct = (delta / interested) * 100 if interested != 0 else 0
            sign = "+" if delta >= 0 else "-"
            typer.echo(f" {i:>2}) {display} ({ticker}) - target: {interested:.3f} MYR - current: {current:.3f} MYR ({sign}{abs(delta):.3f} MYR, {sign}{abs(pct):.2f}%) - {notes}")


@watch_app.command("list")
def watch_list():
    """List watched counters"""
    show_watched_list()


def remove_watch_entry(identifier: str) -> tuple[bool,str]:
    """Remove a watch entry by index (1-based) or by ticker/display_name.
    Returns (removed: bool, message: str)
    """
    rows = load_watched_counters()
    if not rows:
        return False, "No watched counters to remove"
    # try index
    try:
        idx = int(identifier)
        if 1 <= idx <= len(rows):
            removed = rows.pop(idx-1)
            # write back
            with open(WATCHED_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["date_added","ticker","display_name","interested_price_myr","notes"])
                writer.writeheader()
                writer.writerows(rows)
            return True, f"Removed {removed.get('display_name') or removed.get('ticker')}"
        # if numeric but out of range, fall through to try name match
    except ValueError:
        # not an integer index
        pass
    # try matching ticker or display_name
    ident = identifier.strip().lower()
    for r in rows:
        ticker = (r.get('ticker') or '').lower()
        display = (r.get('display_name') or '').lower()
        tprefix = ticker.split('.')[0] if ticker else ''
        if ident == ticker or ident == tprefix or ident == display or display.startswith(ident) or tprefix.startswith(ident):
            rows.remove(r)
            with open(WATCHED_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["date_added","ticker","display_name","interested_price_myr","notes"])
                writer.writeheader()
                writer.writerows(rows)
            return True, f"Removed {r.get('display_name') or r.get('ticker')}"
    return False, "No matching watch found"


def edit_watch_entry(identifier: str, new_price: float | None = None, new_notes: str | None = None) -> tuple[bool,str]:
    """Edit a watch entry by index or ticker/display_name. Update price and/or notes.
    Returns (updated: bool, message)
    """
    rows = load_watched_counters()
    if not rows:
        return False, "No watched counters to edit"
    # try index
    try:
        idx = int(identifier)
        if 1 <= idx <= len(rows):
            r = rows[idx-1]
            if new_price is not None:
                r['interested_price_myr'] = f"{new_price}"
            if new_notes is not None:
                r['notes'] = new_notes
            r['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(WATCHED_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["date_added","ticker","display_name","interested_price_myr","notes"])
                writer.writeheader()
                writer.writerows(rows)
            return True, f"Updated {r.get('display_name') or r.get('ticker')}"
        # if numeric but out of range, fall through to try name match
    except ValueError:
        # not an integer index
        pass
    # try matching by ticker/display_name
    ident = identifier.strip().lower()
    for r in rows:
        ticker = (r.get('ticker') or '').lower()
        display = (r.get('display_name') or '').lower()
        tprefix = ticker.split('.')[0] if ticker else ''
        if ident == ticker or ident == tprefix or ident == display or display.startswith(ident) or tprefix.startswith(ident):
            if new_price is not None:
                r['interested_price_myr'] = f"{new_price}"
            if new_notes is not None:
                r['notes'] = new_notes
            r['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(WATCHED_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["date_added","ticker","display_name","interested_price_myr","notes"])
                writer.writeheader()
                writer.writerows(rows)
            return True, f"Updated {r.get('display_name') or r.get('ticker')}"
    return False, "No matching watch found"

@watch_app.command("remove")
def watch_remove(
    identifier: Annotated[str, typer.Argument(help="Index (1-based) or ticker/display_name to remove")]
):
    """Remove a watched counter by index or ticker/display_name"""
    removed, msg = remove_watch_entry(identifier)
    if removed:
        typer.echo(f"✅ {msg}")
    else:
        typer.echo(f"⚠️  {msg}")
    # show remaining
    show_watched_list()


@watch_app.command("edit")
def watch_edit(
    identifier: Annotated[str, typer.Argument(help="Index or ticker/display_name to edit")],
    price: Annotated[Optional[float], typer.Option("--price", "-p", help="New interested price in MYR")] = None,
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="New notes (pass empty to clear)")] = None
):
    """Edit a watched counter's target price and/or notes"""
    updated, msg = edit_watch_entry(identifier, new_price=price, new_notes=notes)
    if updated:
        typer.echo(f"✅ {msg}")
    else:
        typer.echo(f"⚠️  {msg}")
    show_watched_list()


# Backward-compatible top-level command (keeps `run_klse_system.py watch GAMUDA 0.11` working)
@app.command("watch")
def watch_counter(
    counter: Annotated[str, typer.Argument(help="Stock ticker or symbol to watch (e.g., GAMUDA, JAKS, or 4723)")],
    interested_put_price: Annotated[float, typer.Argument(help="Interested put price in MYR")],
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="Optional notes")] = None
):
    """Legacy: add or update a watched counter (kept for backward compatibility)"""
    watch_add(counter, interested_put_price, notes)

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
