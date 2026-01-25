import csv
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typer.testing import CliRunner
import run_klse_system as r
import pytest

runner = CliRunner()

@pytest.fixture(autouse=True)
def isolated_alerts(tmp_path, monkeypatch):
    klse_dir = tmp_path / 'KLSE_System'
    klse_dir.mkdir()
    watched = klse_dir / 'klse_watched.csv'
    alerts = klse_dir / 'klse_watched_alerts.csv'
    monkeypatch.setattr(r, 'WATCHED_FILE', str(watched))
    monkeypatch.setattr(r, 'ALERTS_FILE', str(alerts))
    # minimal db
    db = klse_dir / 'klse_microcap_database.csv'
    with db.open('w') as f:
        f.write('stock_code,ticker,company_name\n')
        f.write('4723,4723.KL,JAKS Resources\n')
    yield
    try:
        os.remove(str(watched))
    except Exception:
        pass
    try:
        os.remove(str(alerts))
    except Exception:
        pass


def test_watch_check_hits_and_marks(monkeypatch, tmp_path):
    monkeypatch.setattr(r, 'get_current_price', lambda t: 0.10)
    # add an entry where target = 0.11 (should not hit), and one with target 0.12 (should hit)
    runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.11', '--notes', 'nohit'])
    runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.12', '--notes', 'hit'])
    # run check without notifications but mark alerts
    res = runner.invoke(r.app, ['watch', 'check'])
    assert res.exit_code == 0
    # one should be logged
    assert 'Targets Hit' in res.output
    # alerts file created
    assert Path(r.ALERTS_FILE).exists()
    with open(r.ALERTS_FILE) as f:
        rows = list(csv.reader(f))
    assert len(rows) >= 2  # header + at least one hit


def test_watch_check_notify(monkeypatch):
    monkeypatch.setattr(r, 'get_current_price', lambda t: 0.10)
    runner.invoke(r.app, ['watch', 'add', 'JAKS', '0.12', '--notes', 'hit'])
    # pretend macOS and intercept subprocess.run
    monkeypatch.setattr(sys, 'platform', 'darwin')
    called = {}
    def fake_run(cmd, check=False):
        called['cmd'] = cmd
        return None
    monkeypatch.setattr(r.subprocess, 'run', fake_run)
    res = runner.invoke(r.app, ['watch', 'check', '--notify'])
    assert res.exit_code == 0
    assert 'Targets Hit' in res.output
    assert 'cmd' in called
