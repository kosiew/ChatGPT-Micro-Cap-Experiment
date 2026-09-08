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


# --- Injections must match what is actually spent, and only when a buy commits ---

@pytest.fixture
def buyer(tmp_path, monkeypatch):
    """A manager able to run the buy paths against temp files, no network."""
    m = PM.__new__(PM)
    m.starting_cash_myr = 100_000.0
    m.current_cash_myr = 1_000.0
    m.injected_capital_myr = 0.0
    m.BOARD_LOT_SIZE = 100
    m.MICROCAP_THRESHOLD_MYR = 300_000_000
    m.DEFAULT_TRAIL_PCT = 15.0
    m.capital_flow_file = str(tmp_path / 'flows.csv')
    m.config_file = str(tmp_path / 'config.json')
    m.portfolio_file = str(tmp_path / 'portfolio.csv')
    m.trade_log_file = str(tmp_path / 'trades.csv')
    m.portfolio = pd.DataFrame(columns=[
        'date_added', 'ticker', 'company_name', 'shares', 'avg_cost_myr',
        'stop_loss_myr', 'highest_price_myr', 'trail_pct', 'sector',
        'current_price_myr', 'market_value_myr'])
    monkeypatch.setattr(m, '_get_stock_data', lambda t: {'price': 2.0, 'source': 'test'},
                        raising=False)
    monkeypatch.setattr(m, '_save_portfolio', lambda: None, raising=False)
    monkeypatch.setattr(m, '_log_trade', lambda *a, **k: None, raising=False)
    return m


def test_buy_within_cash_on_hand_injects_nothing(buyer):
    result = buyer.add_stock_by_quantity('T.KL', 100, price=2.0)  # costs 200 of 1,000
    assert result['success'] is True
    assert buyer.injected_capital_myr == 0.0
    assert buyer.current_cash_myr == pytest.approx(800.0)
    assert not Path(buyer.capital_flow_file).exists()


def test_buy_exceeding_cash_injects_only_the_shortfall(buyer):
    buyer.add_stock_by_quantity('T.KL', 1000, price=2.0)  # costs 2,000, cash is 1,000
    assert buyer.injected_capital_myr == pytest.approx(1_000.0)
    assert buyer.current_cash_myr == pytest.approx(0.0)


def test_a_rejected_buy_records_no_injection(buyer):
    """Injecting before validation left capital paid in against a position
    that was never opened."""
    result = buyer.add_stock_by_quantity('T.KL', 1000, price=2.0, stop_loss_pct=0.0)
    assert result['success'] is False
    assert buyer.injected_capital_myr == 0.0
    assert buyer.current_cash_myr == pytest.approx(1_000.0)


def test_target_weight_buy_injects_the_rounded_cost_not_the_target(buyer, monkeypatch):
    """Board lots round the purchase down; injecting against the target value
    paid in up to a board lot more than was ever spent."""
    monkeypatch.setattr(buyer, '_calculate_portfolio_value', lambda: 10_000.0, raising=False)
    monkeypatch.setattr(buyer, '_get_stock_data',
                        lambda t: {'price': 3.0, 'source': 'test', 'market_cap': 0},
                        raising=False)
    # 25% of 10,000 = 2,500 target; at 3.00 that is 8 lots = 800 shares = 2,400
    assert buyer.add_stock('T.KL', target_weight_pct=25.0) is True
    assert buyer.injected_capital_myr == pytest.approx(1_400.0)  # 2,400 - 1,000 cash
    assert buyer.injected_capital_myr != pytest.approx(1_500.0)  # not 2,500 - 1,000


def test_target_too_small_for_one_board_lot_injects_nothing(buyer, monkeypatch):
    monkeypatch.setattr(buyer, '_calculate_portfolio_value', lambda: 100.0, raising=False)
    monkeypatch.setattr(buyer, '_get_stock_data',
                        lambda t: {'price': 3.0, 'source': 'test', 'market_cap': 0},
                        raising=False)
    assert buyer.add_stock('T.KL', target_weight_pct=1.0) is False
    assert buyer.injected_capital_myr == 0.0


def test_a_sale_credits_cash_and_is_not_a_capital_injection(buyer):
    """Proceeds are the portfolio's own money coming back, not new capital."""
    buyer.portfolio = pd.DataFrame([{
        'date_added': '2026-01-01', 'ticker': 'T.KL', 'company_name': 'T',
        'shares': 1000, 'avg_cost_myr': 1.0, 'stop_loss_myr': 1.7,
        'highest_price_myr': 2.0, 'trail_pct': 15.0, 'sector': 'Test',
        'current_price_myr': 2.0, 'market_value_myr': 2000.0,
    }])
    result = buyer.sell_stock_by_quantity('T.KL', 400, price=2.0)

    assert result['success'] is True
    assert buyer.current_cash_myr == pytest.approx(1_800.0)  # 1,000 + 800 proceeds
    assert buyer.injected_capital_myr == 0.0
    assert buyer.total_contributed_capital_myr == 100_000.0
    assert buyer.portfolio.iloc[0]['shares'] == 600


def test_cash_from_a_sale_removes_the_need_to_inject(buyer):
    """Selling first should fund the next buy instead of paying in new money."""
    buyer.portfolio = pd.DataFrame([{
        'date_added': '2026-01-01', 'ticker': 'T.KL', 'company_name': 'T',
        'shares': 1000, 'avg_cost_myr': 1.0, 'stop_loss_myr': 1.7,
        'highest_price_myr': 2.0, 'trail_pct': 15.0, 'sector': 'Test',
        'current_price_myr': 2.0, 'market_value_myr': 2000.0,
    }])
    buyer.sell_stock_by_quantity('T.KL', 1000, price=2.0)   # +2,000 -> 3,000 cash
    buyer.add_stock_by_quantity('U.KL', 1000, price=2.0)    # costs 2,000

    assert buyer.injected_capital_myr == 0.0
    assert buyer.current_cash_myr == pytest.approx(1_000.0)
