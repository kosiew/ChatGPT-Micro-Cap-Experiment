"""Chart statistics exclude capital paid in.

Money paid into the account raises equity without being a gain. Raw
day-over-day changes therefore read an injection as a large positive return,
which also inflates volatility and the win rate and distorts the drawdown.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'KLSE_System'))
from klse_visualization import KLSEVisualizationEngine as V


@pytest.fixture
def engine(tmp_path):
    e = V.__new__(V)
    e.capital_flow_file = str(tmp_path / 'flows.csv')
    return e


def _series(*equity):
    dates = pd.date_range('2026-01-01', periods=len(equity)).strftime('%Y-%m-%d')
    return pd.DataFrame({'date': list(dates), 'total_equity_myr': list(equity)})


def _flows(engine, **by_date):
    pd.DataFrame([
        {'date': d.replace('_', '-'), 'amount_myr': amount}
        for d, amount in by_date.items()
    ]).to_csv(engine.capital_flow_file, index=False)


def test_injection_is_not_a_gain(engine):
    """The reported bug: equity jumps by exactly the cash paid in."""
    _flows(engine, **{'2026_01_02': 50.0})
    returns = engine._daily_returns_excluding_flows(_series(100.0, 150.0))
    assert returns[1] == pytest.approx(0.0)


def test_real_gains_still_register_on_an_injection_day(engine):
    """Equity up 60 on a day 50 was paid in is a real 10% gain."""
    _flows(engine, **{'2026_01_02': 50.0})
    returns = engine._daily_returns_excluding_flows(_series(100.0, 160.0))
    assert returns[1] == pytest.approx(10.0)


def test_days_without_flows_are_untouched(engine):
    returns = engine._daily_returns_excluding_flows(_series(100.0, 110.0, 99.0))
    assert returns[1] == pytest.approx(10.0)
    assert returns[2] == pytest.approx(-10.0)


def test_growth_index_ignores_injected_capital(engine):
    """A pure injection must leave the growth curve flat."""
    _flows(engine, **{'2026_01_03': 1_000.0})
    growth = engine._growth_index(_series(100.0, 110.0, 1_110.0), base_value=100.0)
    assert growth[1] == pytest.approx(110.0)
    assert growth[2] == pytest.approx(110.0)


def test_no_flow_file_falls_back_to_plain_returns(engine):
    assert engine.load_capital_flows() == {}
    returns = engine._daily_returns_excluding_flows(_series(100.0, 120.0))
    assert returns[1] == pytest.approx(20.0)


def test_multiple_flows_on_the_same_day_are_summed(engine):
    pd.DataFrame([
        {'date': '2026-01-02', 'amount_myr': 30.0},
        {'date': '2026-01-02', 'amount_myr': 20.0},
    ]).to_csv(engine.capital_flow_file, index=False)
    assert engine.load_capital_flows() == {'2026-01-02': 50.0}
    returns = engine._daily_returns_excluding_flows(_series(100.0, 150.0))
    assert returns[1] == pytest.approx(0.0)


def test_drawdown_measures_the_fall_from_a_running_peak(engine):
    """Not max-minus-min: an injection late in the series must not enlarge it."""
    _flows(engine, **{'2026_01_04': 900.0})
    growth = engine._growth_index(_series(100.0, 120.0, 90.0, 990.0), base_value=100.0)
    peak = np.maximum.accumulate(growth)
    max_drawdown = float(np.where(peak > 0, (peak - growth) / peak, 0).max()) * 100
    assert max_drawdown == pytest.approx(25.0)  # 120 -> 90
