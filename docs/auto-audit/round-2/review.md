# Round 2 Review — 2026-05-07 01:35 (Asia/Taipei)

## Observations

- Round 1 changes are landed and visible in the live UI: candidate table shows `等效Δ`, bubble chart spreads bubbles across 0.2~1.0, scenario table headers are tooltipped, and all three Top-3 cards display the new "三檔風險情境報酬相同" caption (screenshot `04b-cards.png`).
- The three Top-3 cards (`+179.6%`, `+178.9%`, `+177.9%`) still report identical numbers across 平盤 / 跌5% / 跌10% (e.g. `-21.7% / -21.7% / -21.7%` for #1 and `-29.0% / -29.0% / -29.0%` for #3). This is the Round 1 SKIPPED Item 3 (Delta-aware downside) and the user's primary remaining frustration. With spot ≈ 2250 and strikes 2317~2700 (call), even a 0% drop keeps the warrant deep OTM at target day, so `intrinsic_target = 0` and only `time_value_now × sqrt(t_remain/T)` survives — independent of `drop_pct`.
- Same identical-row caption is repeated on **every** card (3 times in a row). Mildly noisy but acceptable for now.
- Bottom Mock chart `📈 標的股價 vs Top 推薦權證價（示意）` plots a random walk around y≈1100 even when the real underlying is TSMC at ~2250 (screenshot `06-bottom-chart.png`). The caption admits "Mock 模式為合成走勢", but the chart is rendered in real-data (`yuanta`) runs too, where the y-axis number is meaningless. Either gate it to Mock-only or reseed around `spot_now`.
- Candidate table has **no default sort** — rows appear in upstream fetch order (065720, 063742, 065929, ...). Users typically want it sorted by 成交量 desc (liquidity) or 達標報酬% if scenario active. Streamlit's `st.dataframe` does not auto-sort; need to pre-sort the DataFrame.
- Scenario table is wide (16 cols). On a 1280px viewport `達標報酬%` is below the fold horizontally — users must scroll right to see the headline KPI. Cannot easily fix with column_config, would need a column reorder. Skipped this round.
- `成交量` (candidate table) vs `成交量(張)` (scenario table) — minor unit-suffix inconsistency, cosmetic, skipped.
- Sign-coloring (red/green) for `漲跌幅%` / `達標報酬%` would help, but Streamlit `column_config.NumberColumn` doesn't support per-cell color. Would need `pd.Styler` and lose pinned-column behaviour. Skipped (same reason as Round 1).
- `expected_warrant_price` for #1 card ("現價 2.1 → 預期 5.87") with breakeven 2587 (target 2800, BE distance +213) is plausible. The math itself is fine; it's only the **risk** branch that's underspecified.
- 32 unit tests still pass post-Round-1 (per `implementation.md`); any new logic in `scenario.py` must extend that count, not break it.

## Proposed Changes

### 1. Make scenario downside model Delta-aware (when target spot is OTM)

- **File**: `src/twse_warrant/analyzers/scenario.py:50-77` (`_project_warrant_price`)
- **Scope**: small (≤30 lines, one function)
- **Risk**: medium — but isolatable: the new branch only fires when `intrinsic_target == 0` AND `equivalent_delta` is available; existing tests use ITM/ATM targets so they go through the unchanged `intrinsic_target > 0` path.
- **Expected effect**:
  - On the Top-3 cards, the three risk rows (平盤 / 跌5% / 跌10%) become **monotonically worse** as drops deepen, instead of all showing the same number.
  - The Round 1 "三檔風險情境報酬相同" caption naturally stops appearing for these calls (still appears for genuinely too-deep-OTM cases — that's correct).
  - The 達標 (positive) branch is unchanged because the target price is by definition above strike for filtered candidates (`require_profit_at_target=True`).
- **Steps**:
  1. In `_project_warrant_price`, after computing `intrinsic_target` and `decay_factor`, when **`intrinsic_target == 0`** (i.e. OTM at the projected spot), add a delta-shadow term:
     ```python
     # OTM at projected spot → time value alone misses Δ × ΔS sensitivity
     time_value_target = time_value_now * decay_factor
     eq_delta = w.equivalent_delta  # may be None
     if eq_delta is not None and ratio:
         # per-warrant Δ × ΔS ; clamp so the warrant price never goes negative
         delta_shadow = eq_delta * (spot_target - spot_now) * ratio
         # cap downside at -time_value_target so price ≥ 0
         delta_shadow = max(delta_shadow, -time_value_target)
         return max(time_value_target + delta_shadow, 0.0)
     return time_value_target
     ```
  2. Keep the ITM branch (`intrinsic_target > 0`) untouched: `return intrinsic_target + time_value_now * decay_factor` exactly as today, so all 8 existing scenario tests pass unchanged.
  3. Carefully gate the new term behind `equivalent_delta is not None` (synthetic test `_call` already sets `delta=0.5`, `ratio=0.005` → `equivalent_delta=100`, so the branch will fire — but those tests target ITM scenarios and never hit it).
  4. Add **one new test** `test_otm_downside_is_monotone` in `tests/test_scenario.py`:
     - Build a deep-OTM call: `strike=2700, ratio=0.005, last=0.5, days=120, spot_now=2250` (i.e. K is 20% above spot).
     - Run `evaluate_scenario` with `target_price=2400` (still OTM) and `risk_drops_pct=(0.0, -5.0, -10.0)`.
     - Assert `risk_returns[0.0] > risk_returns[-5.0] > risk_returns[-10.0]` (strictly decreasing).
     - Assert all three are ≥ -100% (price floor enforced by `max(..., 0.0)` clamp).
  5. Run full suite: `python -m pytest tests/ -q` → expect **33 passed**.
  6. Restart Streamlit; verify on `localhost:8765` that the Top-3 cards' three risk rows now show **distinct** percentages (e.g. -19% / -23% / -27% instead of -21.7% × 3) and the Round 1 caption only shows on edge cases.

### 2. Sort candidate table by 成交量 desc by default

- **File**: `src/streamlit_app.py:360-365` (the `df = pd.DataFrame([warrant_to_row(w) for w in result.candidates])` block)
- **Scope**: tiny (~3 lines)
- **Risk**: very low — purely cosmetic ordering; users can still re-sort by clicking column headers.
- **Expected effect**: the most-liquid warrants sit at the top of the candidate table, which is what 99% of users actually want to look at first. Current ordering is upstream fetch order (essentially symbol order), which surfaces low-volume noise first.
- **Steps**:
  1. After `df = pd.DataFrame([...])`, add:
     ```python
     if "成交量" in df.columns:
         df = df.sort_values("成交量", ascending=False, na_position="last").reset_index(drop=True)
     ```
  2. No test needed (UI-only ordering, no logic changes).
  3. Verify visually: top row should now be the highest-`成交量` warrant; today's screenshot 03 had `065720` at top with vol=3604 — coincidentally already the max, so re-test by clicking analyze and confirming the order is **stable** under cache.

## Skipped (next time)

- Repeating "三檔風險情境報酬相同" caption on every card — reduce to single warning above the 3-card section. Cosmetic.
- Reorder scenario-table columns so `達標報酬%` sits closer to 權證代碼 (currently 13th column, off-screen). Needs UX call on which columns to demote.
- Replace bottom Mock chart with real underlying K-line, OR gate it behind `Mock` source only. Useful but requires fetcher work (out of scope).
- Color-code `漲跌幅%` / `達標報酬%` — would need `pd.Styler` and lose pinned columns. Wait until a Streamlit version supports per-cell color in `column_config`.
- Add a 4th risk column 跌 15% to differentiate even further; only useful after Item 1 lands.
