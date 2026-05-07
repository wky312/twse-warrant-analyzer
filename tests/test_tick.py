"""TW tick size tests."""
import pytest

from twse_warrant.utils.tick import (
    adjacent_ticks,
    round_to_tick,
    tick_size,
)


@pytest.mark.parametrize("price,expected", [
    (0.5, 0.01),
    (9.99, 0.01),
    (10.0, 0.05),
    (49.99, 0.05),
    (50.0, 0.10),
    (99.99, 0.10),
    (100.0, 0.50),
    (499.99, 0.50),
    (500.0, 1.00),
    (999.99, 1.00),
    (1000.0, 5.00),
    (2310.0, 5.00),
])
def test_tick_size(price, expected):
    assert tick_size(price) == expected


def test_round_to_tick_nearest():
    # 權證 0.776 → tick 0.01 → nearest 0.78
    assert round_to_tick(0.776, "nearest") == 0.78
    # 0.774 → 0.77
    assert round_to_tick(0.774, "nearest") == 0.77
    # 25 → tick 0.05 → nearest 25.00
    assert round_to_tick(25.03, "nearest") == 25.05
    # 2312 → tick 5 → nearest 2310
    assert round_to_tick(2312, "nearest") == 2310
    assert round_to_tick(2313, "nearest") == 2315


def test_round_to_tick_down():
    assert round_to_tick(0.776, "down") == 0.77
    assert round_to_tick(2314, "down") == 2310
    assert round_to_tick(99.99, "down") == 99.90


def test_round_to_tick_up():
    assert round_to_tick(0.771, "up") == 0.78
    assert round_to_tick(2306, "up") == 2310
    assert round_to_tick(99.91, "up") == 100.00


def test_adjacent_ticks():
    # 0.776 兩側 tick: 0.77 / 0.78
    assert adjacent_ticks(0.776) == (0.77, 0.78)
    # 2312：兩側 2310 / 2315
    assert adjacent_ticks(2312) == (2310, 2315)
    # 剛好在 tick 上 (e.g. 2310) → both = 2310
    assert adjacent_ticks(2310) == (2310, 2310)


def test_zero_or_negative():
    assert round_to_tick(0, "nearest") == 0.0
    assert round_to_tick(-1, "nearest") == 0.0
