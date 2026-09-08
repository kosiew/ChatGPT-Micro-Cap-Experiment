"""Capital injections are recorded, and returns measure against capital paid in.

A buy that exceeds cash on hand tops the account up. That top-up is
contributed capital, not profit: measuring returns against the starting
balance alone books every injection as a gain.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'KLSE_System'))
from klse_portfolio_manager import KLSEPortfolioManager as PM


@pytest.fixture
def manager(tmp_path):
    """A manager wired to temp files, bypassing __init__'s network work."""
    m = PM.__new__(PM)
    m.starting_cash_myr = 100_000.0
    m.current_cash_myr = 1_000.0
    m.injected_capital_myr = 0.0
    m.capital_flow_file = str(tmp_path / 'flows.csv')
    m.config_file = str(tmp_path / 'config.json')
    m.portfolio = pd.DataFrame()
    return m


def test_contributed_capital_includes_injections(manager):
    assert manager.total_contributed_capital_myr == 100_000.0
    manager._record_capital_injection(25_000.0, 'buy')
    assert manager.total_contributed_capital_myr == 125_000.0


def test_injection_adds_cash_and_is_written_to_the_ledger(manager):
    manager._record_capital_injection(19_789.70, 'buy 51,900 5789.KL', '5789.KL')

    assert manager.current_cash_myr == pytest.approx(20_789.70)
    rows = pd.read_csv(manager.capital_flow_file)
    assert len(rows) == 1
    assert rows.at[0, 'type'] == 'INJECTION'
    assert rows.at[0, 'ticker'] == '5789.KL'
    assert rows.at[0, 'amount_myr'] == pytest.approx(19_789.70)
    assert rows.at[0, 'contributed_capital_myr'] == pytest.approx(119_789.70)


def test_injections_accumulate_in_the_ledger_and_config(manager):
    manager._record_capital_injection(10_000.0, 'first', 'A.KL')
    manager._record_capital_injection(5_000.0, 'second', 'B.KL')

    rows = pd.read_csv(manager.capital_flow_file)
    assert list(rows['total_injected_myr']) == [10_000.0, 15_000.0]
    assert json.load(open(manager.config_file))['injected_capital_myr'] == 15_000.0


def test_zero_or_negative_injection_is_not_recorded(manager):
    manager._record_capital_injection(0.0, 'no top-up needed')
    manager._record_capital_injection(-50.0, 'nonsense')
    assert manager.injected_capital_myr == 0.0
    assert not Path(manager.capital_flow_file).exists()


def test_injected_capital_is_not_counted_as_profit(manager):
    """The reported bug: fresh capital raised equity and read as a gain."""
    manager._record_capital_injection(39_872.70, 'two buys')
    equity = manager.total_contributed_capital_myr  # bought, nothing gained yet

    against_contributed = manager._safe_return_pct(
        equity - manager.total_contributed_capital_myr,
        manager.total_contributed_capital_myr)
    against_starting_only = manager._safe_return_pct(
        equity - manager.starting_cash_myr, manager.starting_cash_myr)

    assert against_contributed == pytest.approx(0.0)
    assert against_starting_only > 39.0  # the old, inflated figure


def test_injected_capital_survives_a_reload(manager, tmp_path):
    manager._record_capital_injection(7_500.0, 'buy')

    reloaded = PM.__new__(PM)
    reloaded.starting_cash_myr = 100_000.0
    reloaded.current_cash_myr = 0.0
    reloaded.injected_capital_myr = 0.0
    reloaded.config_file = manager.config_file
    reloaded._load_config()

    assert reloaded.injected_capital_myr == 7_500.0
    assert reloaded.total_contributed_capital_myr == 107_500.0
