"""Trailing stop loss: the stop trails the high-water mark, not the cost basis."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'KLSE_System'))
from klse_portfolio_manager import KLSEPortfolioManager as PM


def _manager(high=1.0, cost=1.0, shares=100, trail=15.0):
    """A manager with one position, bypassing __init__ and its file/network work."""
    m = PM.__new__(PM)
    m.DEFAULT_TRAIL_PCT = 15.0
    m.portfolio = pd.DataFrame([{
        'ticker': 'T.KL', 'shares': shares, 'avg_cost_myr': cost,
        'highest_price_myr': high, 'trail_pct': trail,
        'stop_loss_myr': PM._trailing_stop_price(high, trail),
        'current_price_myr': high, 'market_value_myr': high * shares,
    }])
    return m


def test_stop_rises_with_a_new_high():
    m = _manager(high=1.0)
    assert m._ratchet_trailing_stop(0, 2.0) is True
    assert m.portfolio.at[0, 'highest_price_myr'] == 2.0
    assert m.portfolio.at[0, 'stop_loss_myr'] == pytest.approx(1.70)


def test_stop_never_falls_back():
    """The defining property: a lower price must not loosen the stop."""
    m = _manager(high=1.0)
    m._ratchet_trailing_stop(0, 2.0)
    for price in (1.9, 1.5, 0.4):
        assert m._ratchet_trailing_stop(0, price) is False
    assert m.portfolio.at[0, 'highest_price_myr'] == 2.0
    assert m.portfolio.at[0, 'stop_loss_myr'] == pytest.approx(1.70)


def test_stop_locks_in_gains_above_cost():
    """A winner's stop sits above cost - the point of trailing rather than
    anchoring to the average purchase price."""
    m = _manager(high=1.0, cost=1.0)
    m._ratchet_trailing_stop(0, 5.0)
    stop = m.portfolio.at[0, 'stop_loss_myr']
    assert stop == pytest.approx(4.25)
    assert stop > m.portfolio.at[0, 'avg_cost_myr']


def test_trail_percentage_is_per_position():
    m = _manager(high=1.0, trail=20.0)
    m._ratchet_trailing_stop(0, 2.0)
    assert m.portfolio.at[0, 'stop_loss_myr'] == pytest.approx(1.60)


def test_topping_up_below_the_high_does_not_lower_the_stop():
    m = _manager(high=2.0)
    assert m._merge_into_existing_position('T.KL', 100, 1.20, 15.0) is True
    assert m.portfolio.at[0, 'highest_price_myr'] == 2.0
    assert m.portfolio.at[0, 'stop_loss_myr'] == pytest.approx(1.70)


def test_topping_up_above_the_high_raises_the_stop():
    m = _manager(high=2.0)
    m._merge_into_existing_position('T.KL', 100, 2.50, 15.0)
    assert m.portfolio.at[0, 'highest_price_myr'] == 2.5
    assert m.portfolio.at[0, 'stop_loss_myr'] == pytest.approx(2.125)


def test_consolidation_takes_the_max_high_not_the_average():
    """Averaging high-water marks would lower the peak and loosen the stop."""
    m = _manager()
    m.portfolio = pd.DataFrame([
        {'ticker': 'T.KL', 'shares': 100, 'avg_cost_myr': 1.0, 'highest_price_myr': 3.0,
         'trail_pct': 15.0, 'stop_loss_myr': 2.55, 'current_price_myr': 2.0,
         'market_value_myr': 200},
        {'ticker': 'T.KL', 'shares': 100, 'avg_cost_myr': 2.0, 'highest_price_myr': 2.0,
         'trail_pct': 15.0, 'stop_loss_myr': 1.70, 'current_price_myr': 2.0,
         'market_value_myr': 200},
    ])
    m._consolidate_position_rows('T.KL')
    assert len(m.portfolio) == 1
    assert m.portfolio.iloc[0]['highest_price_myr'] == 3.0
    assert m.portfolio.iloc[0]['stop_loss_myr'] == pytest.approx(2.55)


def test_seed_uses_todays_price_floored_at_cost(monkeypatch):
    """Conversion seeds the high-water mark from today's price, not a
    historical peak, and never below the entry price."""
    m = PM.__new__(PM)
    m.DEFAULT_TRAIL_PCT = 15.0

    monkeypatch.setattr(m, '_get_stock_data', lambda t: {'price': 3.0}, raising=False)
    assert m._seed_high_water_mark(
        {'ticker': 'T.KL', 'avg_cost_myr': 1.0, 'current_price_myr': 9.9}) == 3.0

    # A loser floors at cost, so the converted stop is never looser than the
    # cost-based one it replaces.
    monkeypatch.setattr(m, '_get_stock_data', lambda t: {'price': 0.5}, raising=False)
    assert m._seed_high_water_mark(
        {'ticker': 'T.KL', 'avg_cost_myr': 1.0, 'current_price_myr': 0.5}) == 1.0


def test_conversion_adds_columns_and_derives_stops(monkeypatch):
    m = PM.__new__(PM)
    m.DEFAULT_TRAIL_PCT = 15.0
    monkeypatch.setattr(m, '_get_stock_data', lambda t: {'price': 2.0}, raising=False)

    legacy = pd.DataFrame([{  # no highest_price_myr / trail_pct columns
        'date_added': '2025-08-31', 'ticker': 'T.KL', 'shares': 100,
        'avg_cost_myr': 1.0, 'stop_loss_myr': 0.85, 'current_price_myr': 2.0,
    }])
    out = m._ensure_trailing_columns(legacy)
    assert out.at[0, 'trail_pct'] == 15.0
    assert out.at[0, 'highest_price_myr'] == 2.0
    assert out.at[0, 'stop_loss_myr'] == pytest.approx(1.70)


def test_validator_accepts_a_stop_above_cost():
    """The old validator rejected stop >= cost; a ratcheted trailing stop is
    exactly that and must pass."""
    m = PM.__new__(PM)
    m.DEFAULT_TRAIL_PCT = 15.0
    winner = pd.DataFrame([{
        'ticker': 'T.KL', 'company_name': 'T', 'shares': 100, 'avg_cost_myr': 1.0,
        'highest_price_myr': 5.0, 'trail_pct': 15.0, 'stop_loss_myr': 4.25,
    }])
    assert m._validate_before_save(winner)['valid'] is True
    # and the on-load validator reports no error for it
    m._validate_portfolio_data(winner.copy())
