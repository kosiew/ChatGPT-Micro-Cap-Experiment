import csv
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typer.testing import CliRunner
from KLSE_System import klse_trading_engine as k

runner = CliRunner()

def test_daily_outputs_company_name_for_stop_alerts(monkeypatch):
    # Craft a fake result that simulates two stop losses
    fake_result = {
        'status': 'success',
        'summary': {'stops_triggered': 2, 'total_equity': 10000.0, 'total_return_pct': 0.0, 'positions': 2},
        'stops_triggered': [
            {
                'ticker': '4677.KL',
                'company_name': 'ACME Corp',
                'stop_price': 2.0,
                'stop_loss': 2.432,
                'shares': 12,
                'pnl': -3.06
            },
            {
                'ticker': '5789.KL',
                'company_name': 'BlueSky Industries',
                'stop_price': 0.385,
                'stop_loss': 0.387,
                'shares': 91700,
                'pnl': -6419.00
            }
        ]
    }

    # Avoid importing/enforcing the full portfolio manager in tests
    monkeypatch.setattr(k.KLSETradingEngine, '__init__', lambda self, alpha_vantage_key=None: None)
    # Monkeypatch the engine's method to return our fake result
    monkeypatch.setattr(k.KLSETradingEngine, 'execute_daily_processing', lambda self: fake_result)

    res = runner.invoke(k.app, ['daily'])
    assert res.exit_code == 0
    # The output should contain company names rather than raw tickers
    assert 'ACME Corp' in res.output
    assert 'BlueSky Industries' in res.output
    # And ensure the raw tickers are not the primary label printed as separate lines
    # (they may appear in other contexts, but not as the main stop header)
    assert '\n⚠️  4677.KL' not in res.output
    assert '\n⚠️  5789.KL' not in res.output
