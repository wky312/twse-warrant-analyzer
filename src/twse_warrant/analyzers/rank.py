"""核心評分與排名."""
from __future__ import annotations

from typing import Optional

from twse_warrant.analyzers.filters import (
    FilterThresholds,
    PROFILE_FILTERS,
    apply_filters,
    detect_lite_mode,
)
from twse_warrant.analyzers.normalize import (
    higher_better,
    lower_better,
    target,
    target_median,
)
from twse_warrant.analyzers.profiles import (
    FEATURE_LABELS_ZH,
    PROFILE_WEIGHTS,
)
from twse_warrant.models import (
    AnalysisResult,
    Direction,
    Profile,
    ScoredWarrant,
    Warrant,
)


def _abs(x: Optional[float]) -> Optional[float]:
    return abs(x) if x is not None else None


def _score_features(
    warrants: list[Warrant],
    profile: Profile,
    *,
    lite_mode: bool = False,
) -> list[dict[str, float]]:
    """Returns list of feature_score dicts (one per warrant), aligned with input order.

    lite_mode=True 時，缺 Greeks 的特徵全給 50 分（中性），權重結構不變.
    """
    if not warrants:
        return []

    # Extract feature values per warrant
    iv = [w.iv_mid or 0.0 for w in warrants]
    delta_abs = [abs(w.delta) if w.delta is not None else 0.0 for w in warrants]
    leverage = [w.leverage if w.leverage is not None else 0.0 for w in warrants]
    days = [float(w.days_to_expiry or 0) for w in warrants]
    volume = [float(w.volume or 0) for w in warrants]
    spread = [w.bid_ask_spread_pct if w.bid_ask_spread_pct is not None else 0.0 for w in warrants]
    outstanding = [
        w.outstanding_pct if w.outstanding_pct is not None else 0.0 for w in warrants
    ]
    trades = [float(w.trade_count or 0) for w in warrants]

    if lite_mode:
        # 缺 Greeks → 不計分；但保留 volume / spread / outstanding / trades
        n = len(warrants)
        scores_iv = [50.0] * n
        scores_delta = [50.0] * n
        scores_leverage = [50.0] * n
        scores_days = [50.0] * n
        scores_volume = higher_better(volume)
        scores_spread = lower_better(spread)
        scores_outstanding = (
            lower_better(outstanding) if any(o > 0 for o in outstanding) else [50.0] * n
        )
        scores_trades = higher_better(trades)
        return [
            {
                "iv": scores_iv[i], "delta": scores_delta[i],
                "leverage": scores_leverage[i], "days": scores_days[i],
                "volume": scores_volume[i], "spread": scores_spread[i],
                "outstanding": scores_outstanding[i], "trades": scores_trades[i],
            }
            for i in range(n)
        ]

    if profile == "stable":
        scores_iv = lower_better(iv)
        scores_delta = target(delta_abs, 0.5)
        scores_leverage = target(leverage, 5.0)
        scores_days = target(days, 90.0)
        scores_volume = higher_better(volume)
        scores_spread = lower_better(spread)
        scores_outstanding = lower_better(outstanding)
        scores_trades = higher_better(trades)
    else:  # aggressive
        scores_iv = target_median(iv)
        scores_delta = target(delta_abs, 0.7)
        scores_leverage = higher_better(leverage)
        scores_days = target(days, 45.0)
        scores_volume = higher_better(volume)
        scores_spread = lower_better(spread)
        scores_outstanding = lower_better(outstanding)
        scores_trades = higher_better(trades)

    out: list[dict[str, float]] = []
    for i in range(len(warrants)):
        out.append({
            "iv": scores_iv[i],
            "delta": scores_delta[i],
            "leverage": scores_leverage[i],
            "days": scores_days[i],
            "volume": scores_volume[i],
            "spread": scores_spread[i],
            "outstanding": scores_outstanding[i],
            "trades": scores_trades[i],
        })
    return out


def _build_warnings(w: Warrant, profile: Profile) -> list[str]:
    out: list[str] = []
    if w.days_to_expiry is not None and w.days_to_expiry < 21:
        out.append(f"近月到期，剩餘天數僅 {w.days_to_expiry} 天")
    if w.bid_ask_spread_pct is not None and w.bid_ask_spread_pct > 2.5:
        out.append(f"買賣價差偏寬 ({w.bid_ask_spread_pct:.2f}%)")
    if w.outstanding_pct is not None and w.outstanding_pct > 70.0:
        out.append(f"券商存量偏低 ({w.outstanding_pct:.1f}%)，造市可能轉弱")
    if w.moneyness_pct is not None and abs(w.moneyness_pct) > 12.0:
        side = "價內" if w.moneyness_pct > 0 else "價外"
        out.append(f"{side}偏深 ({abs(w.moneyness_pct):.1f}%)，需大幅波動才會獲利")
    if profile == "stable" and w.iv_mid is not None and w.iv_mid > 60.0:
        out.append(f"隱波偏高 ({w.iv_mid:.1f}%)，時間價值衰減快")
    if w.volume is not None and w.volume < 100:
        out.append(f"成交量偏低 ({w.volume} 張)，進出可能滑價")
    return out


def _strengths_weaknesses(
    feature_scores: dict[str, float],
    warrant: Warrant,
) -> tuple[list[str], list[str]]:
    """挑出前 2 強與最弱 1 項，組成中文敘述."""
    sorted_features = sorted(feature_scores.items(), key=lambda kv: kv[1], reverse=True)
    top2 = sorted_features[:2]
    bottom1 = sorted_features[-1:]

    def describe(feature: str, score: float) -> str:
        label = FEATURE_LABELS_ZH.get(feature, feature)
        actual = _feature_actual_str(feature, warrant)
        return f"{label}{actual}（評分 {score:.0f}）"

    strengths = [describe(f, s) for f, s in top2 if s > 50]
    weaknesses = [describe(f, s) for f, s in bottom1 if s < 50]
    return strengths, weaknesses


def _feature_actual_str(feature: str, w: Warrant) -> str:
    if feature == "iv" and w.iv_mid is not None:
        return f" {w.iv_mid:.1f}%"
    if feature == "delta" and w.delta is not None:
        return f" {w.delta:.2f}"
    if feature == "leverage" and w.leverage is not None:
        return f" {w.leverage:.1f} 倍"
    if feature == "days" and w.days_to_expiry is not None:
        return f" {w.days_to_expiry} 天"
    if feature == "volume" and w.volume is not None:
        return f" {w.volume:,} 張"
    if feature == "spread" and w.bid_ask_spread_pct is not None:
        return f" {w.bid_ask_spread_pct:.2f}%"
    if feature == "outstanding" and w.outstanding_pct is not None:
        return f" {w.outstanding_pct:.1f}%"
    if feature == "trades" and w.trade_count is not None:
        return f" {w.trade_count:,} 筆"
    return ""


def score_warrants(
    warrants: list[Warrant],
    profile: Profile,
    *,
    lite_mode: bool | None = None,
) -> list[ScoredWarrant]:
    """純函數：吃通過 hard filter 的 warrants，回傳已排序的 ScoredWarrant 清單.

    lite_mode=None 時自動偵測；若 >80% 缺 Greeks 則為 lite.
    """
    if lite_mode is None:
        lite_mode = detect_lite_mode(warrants)
    feature_dicts = _score_features(warrants, profile, lite_mode=lite_mode)
    weights = PROFILE_WEIGHTS[profile]

    out: list[ScoredWarrant] = []
    for w, fs in zip(warrants, feature_dicts):
        total = sum(weights[k] * fs[k] for k in weights)
        strengths, weaknesses = _strengths_weaknesses(fs, w)
        warnings = _build_warnings(w, profile)
        out.append(
            ScoredWarrant(
                warrant=w,
                profile=profile,
                total_score=round(total, 2),
                feature_scores={k: round(v, 1) for k, v in fs.items()},
                top_strengths=strengths,
                top_weaknesses=weaknesses,
                warnings=warnings,
            )
        )
    out.sort(key=lambda x: x.total_score, reverse=True)
    return out


def analyze_warrants(
    warrants: list[Warrant],
    underlying: str,
    direction: Direction,
    profiles: list[Profile],
    top_n: int = 5,
    overrides: dict[Profile, FilterThresholds] | None = None,
    fetch_source: str = "",
) -> AnalysisResult:
    """主入口：吃原始 warrants，回傳 AnalysisResult."""
    overrides = overrides or {}

    # 篩同方向
    if direction != "all":
        oriented = [w for w in warrants if w.direction == direction]
    else:
        oriented = list(warrants)

    result = AnalysisResult(
        underlying=underlying,
        direction=direction,
        raw_count=len(oriented),
        fetch_source=fetch_source,
    )

    if not oriented:
        result.notes.append(
            f"標的 {underlying} 目前無 {('認購' if direction=='call' else '認售' if direction=='put' else '')} 權證掛牌"
        )
        return result

    is_lite = detect_lite_mode(oriented)
    if is_lite:
        result.notes.append(
            "資料來源未提供 Greeks（IV/Delta/履約價/到期日）。"
            "推薦改採 lite 模式：僅依成交量、買賣價差、成交筆數計分；"
            "若需完整評分請改用 CSV 上傳或 Playwright fetcher。"
        )

    candidates_union: dict[str, Warrant] = {}
    for profile in profiles:
        thresh = overrides.get(profile, PROFILE_FILTERS[profile])
        passed, excluded_greeks, _ = apply_filters(
            oriented, profile, thresh, lite_mode=is_lite
        )

        if not passed:
            # Degraded：回傳成交量 Top 3
            top_vol = sorted(oriented, key=lambda w: (w.volume or 0), reverse=True)[:3]
            result.degraded = True
            result.notes.append(
                f"[{profile}] 無權證符合過濾條件，改回傳成交量 Top 3"
            )
            scored_fallback = score_warrants(top_vol, profile, lite_mode=is_lite)
            result.recommendations[profile] = scored_fallback
            for w in top_vol:
                candidates_union[w.symbol] = w
            continue

        scored = score_warrants(passed, profile, lite_mode=is_lite)
        if len(scored) < 5:
            result.notes.append(
                f"[{profile}] 標的權證稀少，僅 {len(scored)} 檔通過過濾"
            )
            result.recommendations[profile] = scored
        else:
            result.recommendations[profile] = scored[:top_n]

        for w in passed:
            candidates_union[w.symbol] = w

        if excluded_greeks > 0:
            result.notes.append(
                f"[{profile}] {excluded_greeks} 檔因缺 Greeks/IV 被排除"
            )

    result.candidates = list(candidates_union.values())
    return result
