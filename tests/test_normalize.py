from twse_warrant.analyzers.normalize import (
    higher_better,
    lower_better,
    target,
    target_median,
)


def test_higher_better_basic():
    assert higher_better([10, 20, 30]) == [0.0, 50.0, 100.0]


def test_lower_better_basic():
    assert lower_better([10, 20, 30]) == [100.0, 50.0, 0.0]


def test_higher_better_all_same_returns_50():
    assert higher_better([5, 5, 5]) == [50.0, 50.0, 50.0]


def test_target_distance():
    # target=20, values 10/20/30 → distances 10/0/10, max=10 → scores 0/100/0
    assert target([10, 20, 30], 20) == [0.0, 100.0, 0.0]


def test_target_outside_range():
    # target=5 (below all), values 10/20/30 → distances 5/15/25, span=25 → 80/40/0
    out = target([10, 20, 30], 5)
    assert out[0] == 80.0
    assert out[1] == 40.0
    assert out[2] == 0.0


def test_target_median_uses_middle():
    out = target_median([10, 20, 30, 40, 50])
    # Median is 30, distances 20/10/0/10/20, span=20 → 0/50/100/50/0
    assert out[2] == 100.0
    assert out[0] == 0.0
    assert out[4] == 0.0


def test_empty_list_safe():
    assert higher_better([]) == []
    assert lower_better([]) == []
    assert target([], 5) == []
