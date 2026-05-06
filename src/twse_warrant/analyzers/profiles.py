"""兩種推薦風格的權重表."""
from __future__ import annotations

from twse_warrant.models import Profile

# 權重總和 = 1.0
PROFILE_WEIGHTS: dict[Profile, dict[str, float]] = {
    "stable": {
        "iv": 0.28,
        "spread": 0.18,
        "days": 0.14,
        "volume": 0.13,
        "delta": 0.10,
        "leverage": 0.07,
        "outstanding": 0.06,
        "trades": 0.04,
    },
    "aggressive": {
        "leverage": 0.30,
        "delta": 0.18,
        "volume": 0.15,
        "spread": 0.13,
        "days": 0.10,
        "trades": 0.07,
        "iv": 0.04,
        "outstanding": 0.03,
    },
}

FEATURE_LABELS_ZH: dict[str, str] = {
    "iv": "隱含波動度",
    "spread": "買賣價差比",
    "days": "剩餘天數",
    "volume": "成交量",
    "delta": "Delta",
    "leverage": "實質槓桿",
    "outstanding": "流通在外比例",
    "trades": "成交筆數",
}
