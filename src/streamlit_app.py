"""Streamlit MVP UI for 台股權證分析."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from datetime import datetime, timedelta

from twse_warrant import analyze
from twse_warrant.analyzers.scenario import ScenarioInputs, evaluate_scenario, evaluate_scenarios
from twse_warrant.fetchers.csv_fetcher import CSVFetcher
from twse_warrant.fetchers.mock import MockFetcher
from twse_warrant.fetchers.twse import TWSEFetcher
from twse_warrant.fetchers.yuanta import YuantaFetcher
from twse_warrant.models import AnalysisResult, Profile, ScoredWarrant, Warrant


st.set_page_config(page_title="台股權證分析", layout="wide", page_icon="📈")


# --- Sidebar 輸入 ---
st.sidebar.title("📈 台股權證分析")

symbol = st.sidebar.text_input("標的股票代碼", value="2330", help="例：2330（台積電）、2454（聯發科）")

direction_label = st.sidebar.radio("權證方向", ["認購 (call)", "認售 (put)"], horizontal=True)
direction = "call" if direction_label.startswith("認購") else "put"

# 後端仍跑兩個 profile（保留邏輯，但 UI 不顯示推薦表）
profiles: tuple[Profile, ...] = ("stable", "aggressive")

source = st.sidebar.selectbox(
    "資料來源",
    [
        "元大權證網（推薦：含完整 Greeks）",
        "TWSE 證交所（真實當日資料，無 Greeks）",
        "合成樣本 (Mock)",
        "上傳 CSV",
    ],
    help=(
        "元大：完整資料含 IV/Delta/履約/到期，**強烈建議**；"
        "TWSE：每日行情但缺 Greeks（lite mode）；"
        "Mock：合成 demo；CSV：自備"
    ),
)
csv_file = None
twse_date = None
if source == "上傳 CSV":
    csv_file = st.sidebar.file_uploader("上傳權證 CSV", type=["csv"])
elif source.startswith("TWSE"):
    # 預設前一個交易日（避免今天還沒收盤）
    default_d = datetime.now() - timedelta(days=1)
    while default_d.weekday() >= 5:  # skip Sat/Sun
        default_d -= timedelta(days=1)
    twse_date_obj = st.sidebar.date_input("資料日期", value=default_d.date())
    twse_date = twse_date_obj.strftime("%Y%m%d")

top_n = st.sidebar.slider("Top N 推薦", 3, 10, 5)

# --- 情境模擬 ---
st.sidebar.markdown("---")
scenario_enabled = st.sidebar.checkbox("🎯 啟用情境模擬", value=False,
    help="給定目標標的價 + 目標日期，找出達標時報酬率最高、且風險可控的權證")
scenario_target = None
scenario_days = None
scenario_target_date = None
scenario_min_vol = 100
scenario_max_spread = 2.5
if scenario_enabled:
    scenario_target = st.sidebar.number_input(
        "目標標的價",
        min_value=1.0, value=2800.0, step=10.0,
        help="您預期標的會到達的價格"
    )
    today = datetime.now().date()
    mode = st.sidebar.radio(
        "目標時間表達方式", ["📅 指定日期", "🔢 指定天數"],
        horizontal=True,
        help="日期 = 行事曆上某一天（如下次法說會前）；天數 = 從今天起算 N 天"
    )
    if mode == "📅 指定日期":
        scenario_target_date = st.sidebar.date_input(
            "目標達成日期",
            value=today + timedelta(days=60),
            min_value=today + timedelta(days=1),
            max_value=today + timedelta(days=365),
            help="預期標的在此日期前後達到目標價"
        )
        scenario_days = (scenario_target_date - today).days
        st.sidebar.caption(f"= 距今 **{scenario_days}** 個日曆日")
    else:
        scenario_days = int(st.sidebar.number_input(
            "目標天期（日曆天）",
            min_value=1, max_value=365, value=60,
            help="從今天起算的日曆天數，含週末"
        ))
        scenario_target_date = today + timedelta(days=scenario_days)
        st.sidebar.caption(f"= **{scenario_target_date.strftime('%Y-%m-%d')}**")

    with st.sidebar.expander("情境過濾設定"):
        scenario_min_vol = st.slider("最低成交量（張）", 0, 1000, 100)
        scenario_max_spread = st.slider("最大買賣價差比 %", 0.5, 10.0, 2.5)

# 進階閾值
with st.sidebar.expander("進階：硬過濾閾值（覆寫預設）"):
    use_overrides = st.checkbox("啟用自訂閾值")
    custom = {}
    if use_overrides:
        for p in profiles:
            st.markdown(f"**{p}**")
            from twse_warrant.analyzers.filters import (
                FilterThresholds,
                PROFILE_FILTERS,
            )
            base = PROFILE_FILTERS[p]
            min_days = st.slider(f"[{p}] 剩餘天數 ≥", 1, 180, base.min_days_to_expiry, key=f"d_{p}")
            min_vol = st.slider(f"[{p}] 成交量 ≥", 0, 1000, base.min_volume, key=f"v_{p}")
            max_spr = st.slider(f"[{p}] 買賣價差比 ≤", 0.5, 10.0, base.max_bid_ask_spread_pct, key=f"s_{p}")
            max_iv = st.slider(f"[{p}] IV ≤", 30.0, 200.0, base.max_iv, key=f"i_{p}")
            custom[p] = FilterThresholds(
                min_days_to_expiry=min_days,
                min_volume=min_vol,
                max_bid_ask_spread_pct=max_spr,
                max_outstanding_pct=base.max_outstanding_pct,
                max_abs_moneyness_pct=base.max_abs_moneyness_pct,
                max_iv=max_iv,
            )

run = st.sidebar.button("🔍 開始分析", type="primary", use_container_width=True)


# --- 主畫面 ---
def warrant_to_row(w: Warrant) -> dict:
    return {
        "權證代碼": w.symbol,
        "權證名稱": w.name,
        "認購售": "認購" if w.direction == "call" else "認售",
        "成交價": w.last_price,
        "漲跌": w.change,
        "漲跌幅%": w.change_pct,
        "成交量": w.volume,
        "履約價": w.strike,
        "行使比例": w.exercise_ratio,
        "剩餘天數": w.days_to_expiry,
        "價內外%": w.moneyness_pct,
        "買賣價差比%": w.bid_ask_spread_pct,
        "實質槓桿": w.leverage,
        "成交價隱波%": w.iv_mid,
        "等效Δ": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else None,
        "流通在外比例%": w.outstanding_pct,
    }


def render_recommendation_card(s: ScoredWarrant, idx: int) -> None:
    title = f"#{idx} {s.warrant.name}（{s.warrant.symbol}）"
    cols = st.columns([1, 3])
    with cols[0]:
        st.metric("總分", f"{s.total_score:.1f}")
        st.write(f"成交價 **{s.warrant.last_price}** ({s.warrant.change_pct:+.2f}%)")
        st.write(f"履約價 {s.warrant.strike}")
        st.write(f"剩餘 **{s.warrant.days_to_expiry}** 天")
        st.write(f"槓桿 **{s.warrant.leverage:.1f}** 倍")
        if s.warrant.iv_mid is not None:
            st.write(f"IV {s.warrant.iv_mid:.1f}%")
    with cols[1]:
        st.markdown(f"### {title}")
        if s.top_strengths:
            st.markdown("**✅ 優勢：** " + " / ".join(s.top_strengths))
        if s.top_weaknesses:
            st.markdown("**⚠️ 弱項：** " + " / ".join(s.top_weaknesses))
        if s.warnings:
            for w in s.warnings:
                st.warning(w)
    st.divider()


def render_basic_info(w: Warrant) -> None:
    """圖二的「基本資料」區."""
    cols = st.columns(2)
    left = {
        "上市日期": w.issue_date,
        "最後交易日": w.last_trade_date,
        "到期日期": w.maturity_date,
        "發行型態": "歐式" + ("認購" if w.direction == "call" else "認售"),
        "最新發行張數": f"{w.issued_units:,}" if w.issued_units else "-",
        "流通在外張數/比例": f"{w.outstanding_units} / {w.outstanding_pct:.2f}%" if w.outstanding_pct else "-",
        "最新履約價": w.strike,
        "最新行使比例": w.exercise_ratio,
    }
    right = {
        "買價隱波": f"{w.iv_buy:.2f}%" if w.iv_buy else "-",
        "賣價隱波": f"{w.iv_sell:.2f}%" if w.iv_sell else "-",
        "原始 Delta (per unit)": w.delta,
        "等效 Delta (教科書 0~1)": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else "-",
        "Theta": w.theta,
        "剩餘天數": w.days_to_expiry,
        "價內外程度": f"{w.moneyness_pct:.2f}% ({'價內' if (w.moneyness_pct or 0)>0 else '價外'})" if w.moneyness_pct is not None else "-",
        "實質槓桿": w.leverage,
        "買賣價差比": f"{w.bid_ask_spread_pct:.2f}%" if w.bid_ask_spread_pct else "-",
    }
    with cols[0]:
        for k, v in left.items():
            st.text(f"{k:<10} {v}")
    with cols[1]:
        for k, v in right.items():
            st.text(f"{k:<10} {v}")


# --- 執行 ---
if not run:
    st.markdown("""
# 台股權證分析

1. 在左側輸入標的股票代碼
2. 選擇方向（認購/認售）與推薦風格
3. 選擇資料來源（Mock 或上傳 CSV）
4. 點選「開始分析」

#### 兩種推薦風格

| 風格 | 重點權重 |
|---|---|
| **低隱波穩健型** | IV(28%) + 買賣價差(18%) + 剩餘天數(14%) |
| **高槓桿進攻型** | 槓桿(30%) + Delta(18%) + 成交量(15%) |

#### 資料來源比較

| 來源 | 特點 |
|---|---|
| **元大權證網** ⭐ | 真實資料 + 完整 Greeks (IV/Delta/Theta/履約價/行使比例/到期/流通在外/實質槓桿/價內外) — 推薦 |
| **TWSE 證交所** | 全市場每日行情；缺 Greeks → lite 模式 |
| **合成 Mock** | 假資料 demo |
| **上傳 CSV** | 自備完整資料 |
""")
    st.stop()

# --- 快取：避免重複 fetch ---
@st.cache_data(ttl=300, show_spinner=False)
def _cached_analyze_yuanta(symbol: str, direction: str, profiles_key: tuple, top_n: int) -> AnalysisResult:
    return analyze(
        underlying=symbol, direction=direction, profiles=profiles_key,
        fetchers=[YuantaFetcher()], top_n=top_n,
    )

@st.cache_data(ttl=300, show_spinner=False)
def _cached_analyze_twse(symbol: str, direction: str, profiles_key: tuple, top_n: int, twse_date: str) -> AnalysisResult:
    return analyze(
        underlying=symbol, direction=direction, profiles=profiles_key,
        fetchers=[TWSEFetcher(date=twse_date)], top_n=top_n,
    )


with st.spinner(f"抓取 {symbol} 權證並分析..."):
    try:
        if source == "上傳 CSV":
            if not csv_file:
                st.error("請先上傳 CSV 檔")
                st.stop()
            result = analyze(
                underlying=symbol, direction=direction, profiles=profiles,
                fetchers=[CSVFetcher(csv_file.read().decode("utf-8"))],
                top_n=top_n, overrides=custom or None,
            )
        elif source.startswith("TWSE"):
            if custom:
                # 有自訂閾值不能用 cache（避免複雜化），重新跑
                result = analyze(
                    underlying=symbol, direction=direction, profiles=profiles,
                    fetchers=[TWSEFetcher(date=twse_date)], top_n=top_n,
                    overrides=custom,
                )
            else:
                result = _cached_analyze_twse(symbol, direction, tuple(profiles), top_n, twse_date)
        elif source.startswith("元大"):
            if custom:
                result = analyze(
                    underlying=symbol, direction=direction, profiles=profiles,
                    fetchers=[YuantaFetcher()], top_n=top_n, overrides=custom,
                )
            else:
                result = _cached_analyze_yuanta(symbol, direction, tuple(profiles), top_n)
        else:  # Mock
            result = analyze(
                underlying=symbol, direction=direction, profiles=profiles,
                fetchers=[MockFetcher(count=40, seed=42)],
                top_n=top_n, overrides=custom or None,
            )
    except Exception as e:
        st.error(f"分析失敗：{e}")
        st.stop()

st.success(f"資料來源：{result.fetch_source}　|　原始候選：{result.raw_count} 檔")
for note in result.notes:
    st.info(note)

# --- 凍結欄位設定（權證代碼/名稱固定在最左） ---
PINNED_COLUMNS = {
    "權證代碼": st.column_config.TextColumn("權證代碼", pinned=True),
    "權證名稱": st.column_config.TextColumn("權證名稱", pinned=True),
}

# --- 情境表 tooltip 設定（擴充自 PINNED_COLUMNS） ---
SCENARIO_COLUMN_CONFIG = {
    **PINNED_COLUMNS,
    "等效Δ": st.column_config.NumberColumn(
        "等效Δ",
        help="教科書 0~1 Delta（已除以行使比例）；認購正、認售負",
    ),
    "IV%": st.column_config.NumberColumn(
        "IV%",
        help="隱含波動度（買價/賣價隱波取中位）；越高代表權證越貴",
    ),
    "槓桿": st.column_config.NumberColumn(
        "槓桿",
        help="實質槓桿（券商計算的 effective gearing）",
    ),
    "履約價": st.column_config.NumberColumn(
        "履約價",
        help="權證的履約價",
    ),
    "價內外%": st.column_config.NumberColumn(
        "價內外%",
        help="目前價內(+) 或價外(-) 的百分比",
    ),
    "天期": st.column_config.NumberColumn(
        "天期",
        help="權證剩餘日曆天數",
    ),
    "損益兩平": st.column_config.NumberColumn(
        "損益兩平",
        help="標的需漲(call)/跌(put)到此價才回本",
    ),
    "達標權證價": st.column_config.NumberColumn(
        "達標權證價",
        help="若達目標日標的到目標價，預期權證的價格",
    ),
    "達標報酬%": st.column_config.NumberColumn(
        "達標報酬%",
        help="達標時相對現價的報酬",
    ),
    "平盤報酬%": st.column_config.NumberColumn(
        "平盤報酬%",
        help="若標的不動到目標日，預期權證價變化",
    ),
    "跌5%報酬%": st.column_config.NumberColumn(
        "跌5%報酬%",
        help="若標的下跌 5% 到目標日的報酬",
    ),
    "跌10%報酬%": st.column_config.NumberColumn(
        "跌10%報酬%",
        help="若標的下跌 10% 到目標日的報酬",
    ),
}


# --- 候選清單 ---
st.subheader(f"🗂️ 候選清單（通過硬過濾，{len(result.candidates)} 檔）")
if result.candidates:
    df = pd.DataFrame([warrant_to_row(w) for w in result.candidates])
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config=PINNED_COLUMNS,
    )
else:
    st.warning("無候選權證")

# --- 反推現價供情境模擬使用 ---
spot_now: float | None = None
for w in result.candidates:
    if w.strike and w.moneyness_pct is not None and w.exercise_ratio:
        if w.direction == "call":
            spot_now = w.strike * (1 + w.moneyness_pct / 100.0)
        else:
            spot_now = w.strike * (1 - w.moneyness_pct / 100.0)
        break

# --- 互動：點選任一檔看基本資料 ---
if result.candidates:
    st.subheader("🔎 個別權證基本資料")
    options = {f"{w.symbol} {w.name}": w for w in result.candidates}
    pick = st.selectbox("選擇權證", list(options.keys()))
    if pick:
        render_basic_info(options[pick])

# --- 視覺化 ---
if len(result.candidates) >= 3:
    st.subheader("📊 候選分佈：IV × |等效Δ|")
    df = pd.DataFrame([{
        "symbol": w.symbol,
        "name": w.name,
        "IV": w.iv_mid,
        "abs_Delta": abs(w.equivalent_delta) if w.equivalent_delta is not None else 0,
        "成交量": w.volume or 0,
        "槓桿": w.leverage or 0,
    } for w in result.candidates])
    fig = px.scatter(
        df, x="IV", y="abs_Delta", size="成交量", color="槓桿",
        hover_name="name", hover_data=["symbol"],
        labels={"IV": "隱含波動度 %", "abs_Delta": "|等效Δ| (0~1)"},
        title="氣泡大小=成交量，顏色=槓桿（等效Δ = 教科書 0~1 Delta）",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 情境模擬 ---
if scenario_enabled and result.candidates:
    st.divider()
    st.subheader(
        f"🎯 情境模擬：到 {scenario_target_date.strftime('%Y-%m-%d')} 達 {scenario_target:.0f} "
        f"（距今 {scenario_days} 日）"
    )

    if spot_now is None:
        st.warning("無法反推標的現價（缺履約價/價內外）。請改用 Yuanta 來源。")
    else:
        st.caption(f"反推標的現價：{spot_now:.1f}　|　預期漲跌幅：{(scenario_target/spot_now-1)*100:+.1f}%")

        scen_inputs = ScenarioInputs(
            target_price=float(scenario_target),
            days_to_target=int(scenario_days),
            spot_now=spot_now,
            risk_drops_pct=(0.0, -5.0, -10.0),
        )
        scen_batch = evaluate_scenarios(
            result.candidates,
            scen_inputs,
            require_alive_at_target=True,
            require_profit_at_target=True,
            min_volume=int(scenario_min_vol),
            max_spread_pct=float(scenario_max_spread),
        )
        scen_results = scen_batch.results

        # 過濾統計
        ex_msg_parts = []
        if scen_batch.excluded_too_short:
            ex_msg_parts.append(f"到期早於目標日 **{scen_batch.excluded_too_short}** 檔")
        if scen_batch.excluded_low_volume:
            ex_msg_parts.append(f"成交量不足 {scen_batch.excluded_low_volume} 檔")
        if scen_batch.excluded_wide_spread:
            ex_msg_parts.append(f"價差過寬 {scen_batch.excluded_wide_spread} 檔")
        if scen_batch.excluded_no_profit:
            ex_msg_parts.append(f"達標仍虧損 {scen_batch.excluded_no_profit} 檔")
        if ex_msg_parts:
            st.caption("已過濾：" + "　|　".join(ex_msg_parts))

        if not scen_results:
            st.warning("沒有權證在這個情境下能獲利（過濾後無候選）。試著放寬目標、延長日期、或降低流動性條件。")
        else:
            st.success(f"✅ 通過情境過濾：{len(scen_results)} 檔　|　按達標報酬率排序")

            scen_rows = []
            for r in scen_results[:20]:
                w = r.warrant
                scen_rows.append({
                    "權證代碼": w.symbol,
                    "權證名稱": w.name,
                    "成交價": w.last_price,
                    "等效Δ": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else None,
                    "IV%": round(w.iv_mid or 0, 1),
                    "槓桿": w.leverage,
                    "履約價": w.strike,
                    "行使比例": round(w.exercise_ratio, 4) if w.exercise_ratio is not None else None,
                    "價內外%": round(w.moneyness_pct, 1) if w.moneyness_pct is not None else None,
                    "天期": w.days_to_expiry,
                    "成交量(張)": w.volume,
                    "損益兩平": round(r.breakeven or 0, 0),
                    "達標權證價": round(r.expected_warrant_price or 0, 2),
                    "達標報酬%": round(r.expected_return_pct or 0, 1),
                    "平盤報酬%": round(r.risk_returns.get(0.0, 0) or 0, 1),
                    "跌5%報酬%": round(r.risk_returns.get(-5.0, 0) or 0, 1),
                    "跌10%報酬%": round(r.risk_returns.get(-10.0, 0) or 0, 1),
                })
            scen_df = pd.DataFrame(scen_rows)
            st.dataframe(
                scen_df, use_container_width=True, hide_index=True,
                column_config=SCENARIO_COLUMN_CONFIG,
            )

            st.markdown("##### 🥇 達標報酬率前 3 強")
            for i, r in enumerate(scen_results[:3], 1):
                w = r.warrant
                cols = st.columns([1, 2, 2])
                with cols[0]:
                    st.metric(f"#{i} 達標報酬", f"{r.expected_return_pct:+.1f}%")
                    st.write(f"**{w.symbol}**")
                    st.write(w.name)
                with cols[1]:
                    st.write(f"履約 **{w.strike:.0f}** | 天期 **{w.days_to_expiry}** 天")
                    st.write(f"現價 {w.last_price} → 預期 **{r.expected_warrant_price:.2f}**")
                    st.write(f"損益兩平 **{r.breakeven:.0f}**　(目標距 BE: {scenario_target - r.breakeven:+.0f})")
                risk_flat = round(r.risk_returns.get(0.0, 0) or 0, 1)
                risk_5 = round(r.risk_returns.get(-5.0, 0) or 0, 1)
                risk_10 = round(r.risk_returns.get(-10.0, 0) or 0, 1)
                with cols[2]:
                    st.write(f"⚠️ 平盤不動：**{risk_flat:+.1f}%**")
                    st.write(f"⚠️ 跌 5%：**{risk_5:+.1f}%**")
                    st.write(f"⚠️ 跌 10%：**{risk_10:+.1f}%**")
                if risk_flat == risk_5 == risk_10:
                    st.caption(
                        "⚠️ 三檔風險情境報酬相同：標的在所有下跌情境皆深度價外，"
                        "模型目前只反映時間價值衰減（Delta-aware OTM 模型留待後續輪次補強）"
                    )
                if r.notes:
                    for n in r.notes:
                        st.caption(f"・{n}")
                st.divider()

            with st.expander("ℹ️ 計算邏輯與 Delta 說明"):
                st.markdown("""
**等效 Delta（表格中的「等效Δ」）**

台灣權證 API（含元大）回傳的 Delta 是「**每單位權證**」的 dW/dS，數值很小（如 0.0021）。
要看教科書版本（0~1 之間），需除以行使比例：
```
等效 Delta = 原始 Delta / 行使比例
```
例：原始 Δ=0.0021、行使比例=0.003 → 等效 Δ = **0.700**（深價內，符合直覺）

| 等效 Δ 範圍 | 跟漲能力 | 適合用途 |
|---|---|---|
| 0.1 ~ 0.3 | 慢，深價外 | 高槓桿賭大波動 |
| 0.4 ~ 0.6 | 平衡，ATM | 一般進攻 |
| 0.7 ~ 0.9 | 接近股票 | 低槓桿穩健、像槓桿 ETF |

---

**內含值（intrinsic）**：
- 認購：`max(目標價 - 履約價, 0) × 行使比例`
- 認售：`max(履約價 - 目標價, 0) × 行使比例`

**達標時權證價**（含剩餘時間價值）：
```
expected_W = intrinsic(目標價) + 現有時間價值 × √(剩餘天數 / 現在天期)
```
時間價值用 √t 衰減（Black-Scholes 近似）。若目標日 ≥ 到期日，純用內含值。

**損益兩平（BE）**：
- 認購：`履約價 + 權證成交價 / 行使比例`
- 認售：`履約價 - 權證成交價 / 行使比例`

**篩選邏輯**：達標時需有正報酬、成交量 ≥ 設定值、買賣價差比 ≤ 設定值。
""")

# --- 走勢圖（Mock）---
top_for_chart: list[ScoredWarrant] = []
for p in profiles:
    top_for_chart.extend(result.recommendations.get(p, [])[:1])

if top_for_chart:
    st.subheader("📈 標的股價 vs Top 推薦權證價（示意）")
    st.caption("⚠️ Mock 模式為合成走勢；接上實際 fetcher 後可換實際歷史 K 線")
    import numpy as np
    days = 30
    rng = np.random.default_rng(42)
    spot_path = 1100 + np.cumsum(rng.normal(0, 8, days))
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=spot_path, name=f"{symbol} 標的", yaxis="y1"))
    for s in top_for_chart:
        warrant_path = (s.warrant.last_price or 2.0) * (1 + np.cumsum(rng.normal(0, 0.04, days)))
        fig.add_trace(go.Scatter(y=warrant_path, name=s.warrant.name, yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="標的股價"),
        yaxis2=dict(title="權證價", overlaying="y", side="right"),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
