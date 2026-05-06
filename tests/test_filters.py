from twse_warrant.analyzers.filters import PROFILE_FILTERS, apply_filters


def test_stable_profile_keeps_good_warrants(sample_warrants):
    passed, excluded, _ = apply_filters(sample_warrants, "stable")
    symbols = {w.symbol for w in passed}
    # 應保留：70001A, 70002B (但 70002B IV=55 OK), 70003C
    # 應過濾：70004D(IV高), 70005E(天期短), 70006F(量少), 70007G(價差寬), 70008H(無Delta)
    assert "70001A" in symbols
    assert "70003C" in symbols
    assert "70004D" not in symbols
    assert "70005E" not in symbols
    assert "70006F" not in symbols
    assert "70007G" not in symbols
    assert "70008H" not in symbols
    assert excluded == 1  # 70008H 缺 delta


def test_aggressive_profile_more_lenient(sample_warrants):
    passed, _, _ = apply_filters(sample_warrants, "aggressive")
    symbols = {w.symbol for w in passed}
    # aggressive 容忍剩餘天數 14、IV 120、價差 5%
    # 70005E (25天) 應通過，70004D (IV 81) 也應通過
    assert "70005E" in symbols
    assert "70004D" in symbols
    # 但 70006F 量太少、70008H 缺 delta 仍應被擋
    assert "70006F" not in symbols
    assert "70008H" not in symbols


def test_filter_thresholds_constants():
    assert PROFILE_FILTERS["stable"].min_days_to_expiry == 30
    assert PROFILE_FILTERS["aggressive"].min_days_to_expiry == 14
    assert PROFILE_FILTERS["stable"].max_iv == 80.0
