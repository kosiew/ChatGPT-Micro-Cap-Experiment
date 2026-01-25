import csv
import os
import sys
from pathlib import Path
# ensure project root is on sys.path for imports when running tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typer.testing import CliRunner
import run_klse_system as r

import pytest

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_watched(tmp_path, monkeypatch):
    # point WATCHED_FILE and microcap DB to tmp paths
    klse_dir = tmp_path / 'KLSE_System'
    klse_dir.mkdir()
    watched = klse_dir / 'klse_watched.csv'
    # set module variable
    monkeypatch.setattr(r, 'WATCHED_FILE', str(watched))
    # create a minimal microcap db to allow name resolution
    db = klse_dir / 'klse_microcap_database.csv'
    with db.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['stock_code','ticker','company_name','sector','subsector','current_price','market_cap_myr','avg_volume','is_microcap','meets_criteria','currency','last_updated','data_source'])
        writer.writerow(['4723','4723.KL','JAKS Resources','Industrial','Construction','0.11','288889664.0','815200','True','True','MYR','2025-09-30T21:51:12.123628','yfinance'])
    monkeypatch.setattr(r.Path, 'cwd', lambda: tmp_path)
    yield
    # cleanup
    try:
        os.remove(str(watched))
    except Exception:
        pass


def test_add_and_load(monkeypatch):
    # avoid yfinance import during test output by mocking get_current_price
    monkeypatch.setattr(r, 'get_current_price', lambda t: 0.10)
    result = runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.11', '--notes', 'test'])
    assert result.exit_code == 0
    rows = r.load_watched_counters()
    assert len(rows) == 1
    assert rows[0]['ticker'] == '4723.KL'
    assert rows[0]['display_name'] == 'JAKS'
    assert rows[0]['interested_buy_price_myr'] == '0.11'
    assert rows[0]['notes'] == 'test'


def test_list_shows_entries(monkeypatch):
    monkeypatch.setattr(r, 'get_current_price', lambda t: 0.1)
    runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.11', '--notes', 'test'])
    res = runner.invoke(r.app, ['watch', 'list'])
    assert res.exit_code == 0
    assert 'JAKS' in res.output
    assert '0.110' in res.output or '0.11' in res.output


def test_edit_by_index_and_by_name(monkeypatch):
    monkeypatch.setattr(r, 'get_current_price', lambda t: 0.1)
    runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.11', '--notes', 'test'])
    # edit by index
    res = runner.invoke(r.app, ['watch', 'edit', '1', '--price', '0.15', '--notes', 'updated'])
    assert res.exit_code == 0
    rows = r.load_watched_counters()
    assert rows[0]['interested_buy_price_myr'] == '0.15'
    assert rows[0]['notes'] == 'updated'
    # edit by name
    res2 = runner.invoke(r.app, ['watch', 'edit', 'jaks', '--price', '0.2'])
    assert res2.exit_code == 0
    rows = r.load_watched_counters()
    assert rows[0]['interested_buy_price_myr'] == '0.2'


def test_remove_by_index_and_name(monkeypatch):
    monkeypatch.setattr(r, 'get_current_price', lambda t: 0.1)
    runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.11', '--notes', 'test'])
    runner.invoke(r.app, ['watch', 'add', 'AXIATA', '1.0'])
    rows = r.load_watched_counters()
    assert len(rows) == 2
    # remove by index
    res = runner.invoke(r.app, ['watch', 'remove', '1'])
    assert res.exit_code == 0
    rows = r.load_watched_counters()
    assert len(rows) == 1
    # remove by name (AXIATA may map to a number if ticker_mappings not present; remove by display_name works if set)
    # For simplicity, use the remaining entry's display_name
    ident = rows[0]['display_name'] or rows[0]['ticker']
    res2 = runner.invoke(r.app, ['watch', 'remove', ident])
    assert res2.exit_code == 0
    rows = r.load_watched_counters()
    assert len(rows) == 0
