#!/usr/bin/env python3
"""
Complete KLSE System Runner
Single script to run all KLSE system components
"""

import os
import sys
import subprocess
import csv
import time
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
# last_price_myr/last_price_at cache the most recent successful quote so the
# watchlist can fall back to it when a live fetch fails, the way `positions`
# falls back to current_price_myr in klse_portfolio.csv.
WATCHED_FIELDNAMES = ["date_added", "ticker", "display_name",
                      "interested_buy_price_myr", "notes",
                      "last_price_myr", "last_price_at"]
PORTFOLIO_FILE = "KLSE_System/klse_portfolio.csv"
TICKER_MAPPINGS_FILE = Path("ticker_mappings.json")


def ensure_watched_file():
    """Ensure watched file exists with header"""
    parent = Path(WATCHED_FILE).parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    if not Path(WATCHED_FILE).exists():
        with open(WATCHED_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Add display_name column to store friendly label like 'GAMUDA'
            writer.writerow(WATCHED_FIELDNAMES)


def load_ticker_mappings() -> dict:
    """Load cached counter-symbol-to-code mappings."""
    try:
        if TICKER_MAPPINGS_FILE.exists():
            with open(TICKER_MAPPINGS_FILE, encoding='utf-8') as f:
                return {k.upper(): str(v) for k, v in __import__('json').load(f).items()}
    except (OSError, ValueError):
        pass
    return {}


def _save_ticker_mapping(symbol: str, code: str) -> None:
    """Cache a counter symbol resolved from i3investor for later offline use."""
    mappings = load_ticker_mappings()
    mappings[symbol.upper()] = str(code)
    try:
        with open(TICKER_MAPPINGS_FILE, 'w', encoding='utf-8') as f:
            __import__('json').dump(mappings, f, indent=2)
            f.write('\n')
    except OSError:
        pass


def _lookup_ticker_mapping(counter: str) -> Optional[tuple[str, str]]:
    """Resolve a Bursa counter symbol or code through i3investor."""
    try:
        from KLSE_System.i3investor_scraper import I3InvestorScraper
        return I3InvestorScraper().resolve_ticker(counter)
    except (ImportError, OSError):
        return None


def _normalize_ticker(ticker: str) -> str:
    """Normalize user input into a yfinance-compatible ticker like '4723.KL' or 'GAMUDA.KL'.
    Attempts multiple resolution strategies:
     - cached ticker_mappings.json symbol or code
     - exact .KL provided -> use upper
     - match ticker or company name in klse_microcap_database.csv
     - i3investor lookup, cached for future use
     - fallback to upper + .KL
    """
    t = ticker.strip()
    mappings = load_ticker_mappings()
    up = t.upper()

    # Mapping like AXIATA -> 6888.
    if up in mappings:
        return f"{mappings[up]}.KL"

    # Preserve an already formatted ticker unless its numeric code can be resolved below.
    formatted_ticker = up if up.endswith('.KL') else None
    prefix = up.removesuffix('.KL')
    if formatted_ticker:
        return formatted_ticker

    # A cached symbol mapping also resolves its numeric code without another lookup.
    if prefix.isdigit() and prefix in {code.split('.')[0] for code in mappings.values()}:
        return f"{prefix}.KL"

    # try to find in microcap database by exact ticker or by company name containing the token
    db_path = Path('KLSE_System/klse_microcap_database.csv')
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

    # Unknown symbols and numeric codes are resolved online once, then cached.
    resolved = _lookup_ticker_mapping(prefix)
    if resolved:
        symbol, code = resolved
        _save_ticker_mapping(symbol, code)
        return f"{code}.KL"

    # fallback
    return prefix + '.KL'


def _derive_display_name_from_database(ticker: str) -> str:
    """Try to get a friendly display name (e.g., GAMUDA) from the microcap database.
    Falls back to the ticker prefix (before the dot).
    """
    # ticker expected in yfinance format like '4723.KL' or 'GAMUDA.KL'
    prefix = ticker.split('.')[0].upper()

    # Use a mapped symbol when the ticker was supplied as its numeric code.
    for symbol, code in load_ticker_mappings().items():
        if str(code).split('.')[0].upper() == prefix:
            return symbol

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


def add_watch_entry(ticker: str, interested_buy_price: float, notes: str = ""):
    """Add or update a watch entry (interested_buy_price is the price you'd like to buy at)"""
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
            # normalize missing display_name and ensure backward compatibility for price field
            if 'display_name' not in r:
                r['display_name'] = ''
            # migrate old key if present
            if 'interested_price_myr' in r and 'interested_buy_price_myr' not in r:
                r['interested_buy_price_myr'] = r.get('interested_price_myr')
            if r["ticker"].lower() == ticker_norm.lower():
                r["interested_buy_price_myr"] = f"{interested_buy_price}"
                r["date_added"] = now
                r["notes"] = notes
                r["display_name"] = display_name
                updated = True
            rows.append(r)
    if not updated:
        rows.append({"date_added": now, "ticker": ticker_norm, "display_name": display_name, "interested_buy_price_myr": f"{interested_buy_price}", "notes": notes})
    # Write back
    with open(WATCHED_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=WATCHED_FIELDNAMES, extrasaction="ignore")
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
            for key in ('last_price_myr', 'last_price_at'):
                if r.get(key) is None:
                    r[key] = ''
        return rows


def _log_price_failure(ticker: str, error) -> None:
    """Surface why a lookup failed instead of silently returning None."""
    typer.echo(f"\u26a0\ufe0f  Price lookup failed for {ticker}: {error}", err=True)


def get_current_price(ticker: str, retries: int = 3, backoff: float = 1.0):
    """Return latest close price using yfinance, or None on failure.

    Yahoo throttles per IP, so the `full` run - which fetches dozens of tickers
    through its subprocesses before reaching the watchlist - is far likelier to
    be rate-limited here than a standalone command. Retry with backoff, and try
    the quote endpoint separately from history(): the two calls fail
    independently, so the quote must not sit behind history()'s exception.
    """
    try:
        import yfinance as yf_local
    except Exception as exc:
        _log_price_failure(ticker, f"yfinance unavailable: {exc}")
        return None

    last_error = "no data"
    for attempt in range(retries):
        tk = None
        try:
            tk = yf_local.Ticker(ticker)
            hist = tk.history(period='1d')
            if hist is not None and not hist.empty:
                return float(hist['Close'].iloc[-1])
            last_error = "empty history"
        except Exception as exc:
            last_error = exc
        if tk is not None:
            try:
                info = tk.info or {}
                price = info.get('regularMarketPrice') or info.get('previousClose')
                if price is not None:
                    return float(price)
            except Exception as exc:
                last_error = exc
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))

    _log_price_failure(ticker, last_error)
    return None


def write_watched_counters(rows) -> None:
    """Rewrite WATCHED_FILE, upgrading legacy rows to the current columns."""
    ensure_watched_file()
    with open(WATCHED_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=WATCHED_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def record_watched_prices(prices: dict) -> None:
    """Cache freshly fetched prices in WATCHED_FILE for later fallback."""
    fresh = {t: p for t, p in (prices or {}).items() if t and p is not None}
    if not fresh:
        return
    rows = load_watched_counters()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed = False
    for r in rows:
        price = fresh.get(r.get('ticker'))
        if price is None:
            continue
        r['last_price_myr'] = f"{price:.3f}"
        r['last_price_at'] = now
        changed = True
    if changed:
        write_watched_counters(rows)


def resolve_watched_price(row) -> tuple:
    """Return (price, cached_at) for a watch row.

    A live quote wins and reports cached_at=None. Otherwise fall back to the
    last price cached in WATCHED_FILE so a transient Yahoo failure degrades to
    a stale-but-labelled number instead of N/A.
    """
    ticker = row.get('ticker')
    price = get_current_price(ticker) if ticker else None
    if price is not None:
        return price, None
    cached = _to_float(row.get('last_price_myr'))
    if cached is not None:
        return cached, row.get('last_price_at') or 'unknown'
    return None, None


def show_watched_section():
    watched = load_watched_counters()
    if not watched:
        typer.echo("\n🔭 Watched Counters: None")
        return
    typer.echo("\n🔭 Watched Counters:")
    fetched = {}
    for w in watched:
        ticker = w.get("ticker")
        display = w.get("display_name") or (ticker.split('.')[0] if ticker else "")
        # support both new and legacy column names
        try:
            interested = float(w.get("interested_buy_price_myr", w.get("interested_price_myr", '')))
        except Exception:
            interested = None
        current, cached_at = resolve_watched_price(w)
        if current is not None and cached_at is None:
            fetched[ticker] = current
        if current is None or interested is None:
            target = w.get('interested_buy_price_myr') or w.get('interested_price_myr')
            try:
                target = f"{float(target):.3f}"
            except (TypeError, ValueError):
                pass
            typer.echo(f"   • {display} ({ticker}) - target: {target} MYR - current: N/A")
        else:
            delta = current - interested
            pct = (delta / interested) * 100 if interested != 0 else 0
            sign = "+" if delta >= 0 else "-"
            stale = f" [cached {cached_at}]" if cached_at else ""
            typer.echo(f"   • {display} ({ticker}) - target: {interested:.3f} MYR - current: {current:.3f} MYR ({sign}{abs(delta):.3f} MYR, {sign}{abs(pct):.2f}%){stale}")
    record_watched_prices(fetched)

# --- End watched helpers ---

ALERTS_FILE = "KLSE_System/klse_watched_alerts.csv"


def ensure_alerts_file():
    parent = Path(ALERTS_FILE).parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    if not Path(ALERTS_FILE).exists():
        with open(ALERTS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["date","ticker","display_name","interested_buy_price_myr","current_price_myr","delta","pct"])
    import sys
    if sys.platform != 'darwin':
        return False
    try:
        subprocess.run(["osascript", "-e", f'display notification "{message}" with title "KLSE Watch Alert"'], check=False)
        return True
    except Exception:
        return False


def check_watched_targets(notify: bool = False, mark: bool = True) -> list:
    """Check watched counters and return list of alert dicts where current_price <= interested buy price.
    If mark is True append alerts to ALERTS_FILE. If notify True, send macOS notification (if supported).
    """
    hits = []
    fetched = {}
    watched = load_watched_counters()
    for w in watched:
        ticker = w.get('ticker')
        display = w.get('display_name') or (ticker.split('.')[0] if ticker else '')
        # support legacy name and new name
        try:
            interested = float(w.get('interested_buy_price_myr', w.get('interested_price_myr','')))
        except Exception:
            continue
        # Alerts stay live-only: a stale cached price must never fire a target hit.
        current = get_current_price(ticker) if ticker else None
        if current is None:
            continue
        fetched[ticker] = current
        # consider hit when current <= interested (target buy)
        if current <= interested:
            delta = current - interested
            pct = (delta / interested) * 100 if interested != 0 else 0
            hit = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ticker': ticker,
                'display_name': display,
                'interested_buy_price_myr': f"{interested}",
                'current_price_myr': f"{current}",
                'delta': f"{delta}",
                'pct': f"{pct}"
            }
            hits.append(hit)
            # notification
            if notify:
                msg = f"{display} ({ticker}) hit target {interested:.3f} MYR — current {current:.3f} MYR"
                # call notification helper if available, else fallback to subprocess.run
                nf = globals().get('_send_macos_notification')
                if callable(nf):
                    nf(msg)
                else:
                    try:
                        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "KLSE Watch Alert"'], check=False)
                    except Exception:
                        pass
    record_watched_prices(fetched)
    # write to alerts file
    if mark and hits:
        ensure_alerts_file()
        with open(ALERTS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for h in hits:
                writer.writerow([h['date'], h['ticker'], h['display_name'], h['interested_buy_price_myr'], h['current_price_myr'], h['delta'], h['pct']])
    return hits

@app.command("full")
def run_full_system(
    alpha_vantage_key: Annotated[
        Optional[str], 
        typer.Option("--alpha-vantage-key", "-k", help="Alpha Vantage API key")
    ] = None,
    alert: Annotated[bool, typer.Option("--alert", help="Check watched counters for hits and alert if targets hit")] = False,
    notify: Annotated[bool, typer.Option("--notify", "-n", help="Send macOS notifications for hits (only on macOS)")] = False
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

    # Optionally check and alert on hits
    if alert:
        hits = check_watched_targets(notify=notify, mark=True)
        if hits:
            typer.echo("\n⚠️  Watch Alerts generated. Use 'run_klse_system.py watch check' to review.")

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
    interested_buy_price: Annotated[float, typer.Argument(help="Interested buy price in MYR")],
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="Optional notes")] = None
):
    """Add or update a watched counter"""
    ticker_norm = _normalize_ticker(counter)
    add_watch_entry(ticker_norm, interested_buy_price, notes or "")
    typer.echo(f"✅ Added/Updated watch for {ticker_norm} at target {interested_buy_price:.3f} MYR")
    show_watched_section()


def show_watched_list():
    """Print a numbered list of watched counters with details"""
    rows = load_watched_counters()
    if not rows:
        typer.echo("\n🔭 Watched Counters: None")
        return
    typer.echo("\n🔭 Watched Counters:")
    fetched = {}
    for i, r in enumerate(rows, start=1):
        ticker = r.get('ticker')
        display = r.get('display_name') or (ticker.split('.')[0] if ticker else '')
        notes = r.get('notes','')
        try:
            interested = float(r.get('interested_buy_price_myr', r.get('interested_price_myr','')))
        except Exception:
            interested = None
        current, cached_at = resolve_watched_price(r)
        if current is not None and cached_at is None:
            fetched[ticker] = current
        if current is None or interested is None:
            target = r.get('interested_buy_price_myr') or r.get('interested_price_myr')
            typer.echo(f" {i:>2}) {display} ({ticker}) - target: {target} MYR - current: N/A - {notes}")
        else:
            delta = current - interested
            pct = (delta / interested) * 100 if interested != 0 else 0
            sign = "+" if delta >= 0 else "-"
            stale = f" [cached {cached_at}]" if cached_at else ""
            typer.echo(f" {i:>2}) {display} ({ticker}) - target: {interested:.3f} MYR - current: {current:.3f} MYR ({sign}{abs(delta):.3f} MYR, {sign}{abs(pct):.2f}%){stale} - {notes}")
    record_watched_prices(fetched)


@watch_app.command("list")
def watch_list():
    """List watched counters"""
    show_watched_list()


@watch_app.command("check")
def watch_check(
    notify: Annotated[bool, typer.Option("--notify", "-n", help="Send macOS notifications for hits")] = False,
    mark: Annotated[bool, typer.Option("--no-mark", "-m", help="Don't append hits to alerts file", show_default=True)] = True
):
    """Check watched counters and report hits (current price <= interested buy price)"""
    hits = check_watched_targets(notify=notify, mark=mark)
    if not hits:
        typer.echo("\n✅ No targets hit")
        return
    typer.echo("\n🚨 Targets Hit:")
    for h in hits:
        delta = float(h['delta'])
        pct = float(h['pct'])
        sign = "+" if delta >= 0 else "-"
        typer.echo(f" • {h['display_name']} ({h['ticker']}) - target: {float(h['interested_buy_price_myr']):.3f} MYR - current: {float(h['current_price_myr']):.3f} MYR ({sign}{abs(delta):.3f} MYR, {sign}{abs(pct):.2f}%)")
    typer.echo(f"\nLogged {len(hits)} hit(s) to {ALERTS_FILE} (if marking enabled)")


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
                writer = csv.DictWriter(f, fieldnames=WATCHED_FIELDNAMES, extrasaction="ignore")
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
                writer = csv.DictWriter(f, fieldnames=WATCHED_FIELDNAMES, extrasaction="ignore")
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
                r['interested_buy_price_myr'] = f"{new_price}"
            if new_notes is not None:
                r['notes'] = new_notes
            r['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(WATCHED_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=WATCHED_FIELDNAMES, extrasaction="ignore")
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
                r['interested_buy_price_myr'] = f"{new_price}"
            if new_notes is not None:
                r['notes'] = new_notes
            r['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(WATCHED_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=WATCHED_FIELDNAMES, extrasaction="ignore")
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


def load_portfolio_positions() -> list:
    """Read current holdings from the portfolio CSV (empty list if missing)."""
    path = Path(PORTFOLIO_FILE)
    if not path.exists():
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _position_counter_name(row: dict) -> str:
    """Short counter label for a holding, e.g. GAMUDA."""
    ticker = row.get('ticker', '')
    display = _derive_display_name_from_database(ticker) if ticker else ''
    # _derive_display_name_from_database falls back to the numeric code; prefer the
    # portfolio's own company name in that case.
    if display and not display.isdigit():
        return display
    company = (row.get('company_name') or '').strip()
    if company:
        return ''.join(ch for ch in company.split()[0].upper() if ch.isalnum())
    return display or ticker


def _to_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _aggregate_positions(rows: list) -> list:
    """Collapse repeated rows for the same ticker into one weighted-average holding.

    Buys now merge into the existing position, but legacy portfolio files may
    still hold a separate row per purchase; showing them as one line keeps the
    reported cost basis honest.
    """
    merged: dict = {}
    order = []
    for i, r in enumerate(rows):
        key = r.get('ticker') or f'__row{i}'
        if key not in merged:
            merged[key] = dict(r)
            order.append(key)
            continue

        base = merged[key]
        base_shares = _to_float(base.get('shares')) or 0.0
        new_shares = _to_float(r.get('shares')) or 0.0
        base_cost = _to_float(base.get('avg_cost_myr'))
        new_cost = _to_float(r.get('avg_cost_myr'))
        total_shares = base_shares + new_shares

        base['shares'] = total_shares
        if total_shares and base_cost is not None and new_cost is not None:
            base['avg_cost_myr'] = (base_shares * base_cost + new_shares * new_cost) / total_shares

    return [merged[k] for k in order]


def show_positions(live: bool = True):
    """Print holdings with quantity, cost, current price and % gain."""
    rows = _aggregate_positions(load_portfolio_positions())
    if not rows:
        typer.echo(f"\n📁 Portfolio: no positions found in {PORTFOLIO_FILE}")
        return

    typer.echo("\n📈 Portfolio Positions:")
    header = f"{'COUNTER':<12} {'CODE':<9} {'QTY':>8} {'BOUGHT':>10} {'CURRENT':>10} {'VALUE':>13} {'GAIN%':>9}"
    typer.echo(header)
    typer.echo("-" * len(header))

    total_cost = 0.0
    total_value = 0.0
    for r in rows:
        ticker = r.get('ticker', '')
        code = ticker.split('.')[0]
        counter = _position_counter_name(r)
        shares = _to_float(r.get('shares')) or 0.0
        cost = _to_float(r.get('avg_cost_myr'))
        current = get_current_price(ticker) if (live and ticker) else None
        if current is None:
            current = _to_float(r.get('current_price_myr'))

        qty_txt = f"{shares:,.0f}"
        cost_txt = f"{cost:.3f}" if cost is not None else "N/A"
        cur_txt = f"{current:.3f}" if current is not None else "N/A"
        if current is not None:
            value = shares * current
            value_txt = f"{value:,.2f}"
            total_value += value
        else:
            value_txt = "N/A"
        if cost is not None and current is not None and cost != 0:
            pct = (current - cost) / cost * 100
            gain_txt = f"{pct:+.2f}%"
        else:
            gain_txt = "N/A"
        if cost is not None:
            total_cost += shares * cost

        typer.echo(f"{counter:<12} {code:<9} {qty_txt:>8} {cost_txt:>10} {cur_txt:>10} {value_txt:>13} {gain_txt:>9}")

    typer.echo("-" * len(header))
    total_pct = (total_value - total_cost) / total_cost * 100 if total_cost else 0.0
    typer.echo(f"{'TOTAL':<12} {'':<9} {'':>8} {total_cost:>10,.2f} {'':>10} {total_value:>13,.2f} {total_pct:>+8.2f}%")
    typer.echo(f"\nPositions: {len(rows)} | Cost: {total_cost:,.2f} MYR | Value: {total_value:,.2f} MYR | P/L: {total_value - total_cost:+,.2f} MYR")


@app.command("positions")
def positions(
    live: Annotated[bool, typer.Option("--live/--cached", help="Fetch live prices via yfinance (default) or use prices stored in the portfolio CSV")] = True
):
    """Show portfolio holdings: counter (code), quantity, price bought, current price and % gain"""
    show_positions(live=live)


# Backward-compatible top-level command (keeps `run_klse_system.py watch GAMUDA 0.11` working)
@app.command("watch")
def watch_counter(
    counter: Annotated[str, typer.Argument(help="Stock ticker or symbol to watch (e.g., GAMUDA, JAKS, or 4723)")],
    interested_buy_price: Annotated[float, typer.Argument(help="Interested buy price in MYR")],
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="Optional notes")] = None
):
    """Legacy: add or update a watched counter (kept for backward compatibility)"""
    watch_add(counter, interested_buy_price, notes)

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
