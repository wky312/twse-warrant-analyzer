# Round 1 Review — 2026-05-07 00:20 (Asia/Taipei)

## Observations

- Sidebar layout is clean. Inputs (symbol, direction, source, top N, scenario block, advanced overrides) are well grouped, and the scenario expand/collapse is a nice touch.
- Result header banner ("資料來源：yuanta | 原始候選：905 檔") + structured info notes for excluded counts are informative.
- Candidate table pins 權證代碼/權證名稱 to the left (good) and shows wide column set, but the **`Delta` column is the raw per-unit value (e.g. 0.004)**, while the per-warrant detail card shows both "原始 Delta (per unit)" and "等效 Delta (教科書 0~1)". The candidate table never surfaces the textbook 0~1 form, which is the human-readable one most traders expect.
- Bubble chart "候選分佈：IV × |Delta|" plots raw `abs(w.delta)`. With per-unit deltas ~0.001~0.07, every bubble is squashed near y=0 and the axis is hard to read. Same fix as above (use `equivalent_delta`).
- The "🥇 達標報酬率前 3 強" cards show three risk-scenario rows ("平盤不動", "跌 5%", "跌 10%") that all return the same number (e.g. all -21.7%). Mathematically this is because the scenario engine projects price by `intrinsic + time_value × sqrt(t_remain/T)`; for OTM calls all three risk spots stay below strike → intrinsic=0, identical results. **It is not a bug per se but the UX is misleading**: the user thinks "great, downside is bounded at -21.7% even on a 10% drop" without realizing the model is not Delta-aware below strike. Either remove the redundancy or add a disclaimer.
- Top-level recommendations table by profile is computed (`result.recommendations`) but the UI never renders it on the main page. Only candidate table + detail card + scenario cards are shown. Profile-based recommendations are effectively dead UI for now (intentional?). Skipped — not in scope for a low-risk round.
- Header in candidate table uses 「成交價隱波%」 but detail panel uses 「買價隱波 / 賣價隱波」 (no mid label). Minor inconsistency, low priority.
- Scenario cards use ⚠️ on every risk row, even when 平盤不動 produces a positive result it would still display ⚠️. Currently all are negative so it doesn't matter, but the icon should reflect sign.
- "📈 標的股價 vs Top 推薦權證價（示意）" is a synthetic random walk (caption admits Mock). For real fetcher modes this chart adds no value. Skipped — out of scope.
- Tests pass (32/32) and are well organized; any change should ship with at least one test if it touches scenario.py.

## Proposed Changes

### 1. Use 等效 Delta (textbook 0~1) in candidate table & bubble chart

- **File**: `src/streamlit_app.py:151` and `src/streamlit_app.py:341`
- **Scope**: small (~6 lines)
- **Risk**: low — `equivalent_delta` is already a property on `Warrant`, computed safely (returns None when `exercise_ratio` is 0/None).
- **Expected effect**:
  - Candidate table column "Delta" shows ~0.4~0.8 (textbook range) instead of ~0.004, matching the detail panel and what users intuitively understand.
  - Bubble chart Y-axis spreads bubbles across 0~1 instead of crushing them near 0.
- **Steps**:
  1. In `warrant_to_row`, change `"Delta": w.delta` → `"等效Δ": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else None`. Rename the column header to match the scenario table ("等效Δ") for consistency.
  2. In the bubble chart block, replace `"abs_Delta": abs(w.delta) if w.delta else 0` with `"abs_Delta": abs(w.equivalent_delta) if w.equivalent_delta is not None else 0` and update the chart `labels={..., "abs_Delta": "|等效Δ| (0~1)"}` and title to clarify.
  3. No new tests needed (no logic change in `models.py` or analyzers).

### 2. Add tooltip/help to confusing scenario column headers and clarify identical risk rows

- **File**: `src/streamlit_app.py:401-447`
- **Scope**: small (~15 lines)
- **Risk**: low — purely UI strings.
- **Expected effect**:
  - Scenario table columns "等效Δ", "達標權證價", "達標報酬%", "平盤報酬%" become discoverable via Streamlit `column_config` `help=...`.
  - The 3-strong cards add a one-line caption when the three risk-drop returns are identical, e.g. "三檔風險情境報酬相同：標的在所有下跌情境皆深度價外，模型僅反映時間價值衰減" so the user understands why -10% drop ≠ deeper loss.
- **Steps**:
  1. Build a richer `column_config` dict (extend `PINNED_COLUMNS`) with `NumberColumn(format="%.1f%%", help="...")` etc. for the scenario `st.dataframe` call only.
  2. In the per-card render loop, after computing the three `risk_returns`, if `len(set(round(v,1) for v in vals)) == 1`, append a `st.caption` explaining it.

### 3. Make scenario downside model Delta-aware (when below strike)

- **File**: `src/twse_warrant/analyzers/scenario.py:50-77` (modify `_project_warrant_price`)
- **Scope**: medium (~25 lines + 1 new test)
- **Risk**: medium — touches a heavily tested path; needs careful preservation of existing test expectations. Existing tests use cases where target is at or above strike, so adding a delta-shadow component on the OTM side should not flip current test outcomes (they all use spot=spot_now or spot=target≥strike).
- **Expected effect**:
  - When the projected spot is below strike (OTM call) or above strike (OTM put), instead of pure time-value decay, blend in a small `delta × ΔS` contribution capped at `time_value_now`. So 平盤/跌5%/跌10% give visibly different (and more realistic) returns.
- **Steps**:
  1. In `_project_warrant_price`, after computing `intrinsic_target` and `decay_factor`, when `intrinsic_target == 0` (OTM at target), compute `extrinsic_at_target = time_value_now * decay_factor + (w.equivalent_delta or 0) * (S_target - spot_now) * w.exercise_ratio`. Clamp the result to be ≥ 0.
  2. Carefully gate behind `w.equivalent_delta is not None` so existing tests (which set `delta=0.5` and `exercise_ratio` such that equivalent_delta=100) still produce the legacy result for ITM cases (where `intrinsic_target > 0` and the new branch is skipped).
  3. Add a test `test_otm_downside_differentiated`: build a deep-OTM call, run scenario at three drops, assert returns are strictly monotone (drop 0% > drop 5% > drop 10%).
  4. Run `pytest tests/` — verify 32 + 1 = 33 pass.

## Skipped (next time)

- Surface profile-based Top-N recommendations in the main UI (currently computed but invisible). Larger UX decision, defer.
- Replace synthetic random-walk price chart with a real underlying history pull. Requires new fetcher work, out of scope.
- Unify "成交價隱波%" / "買價隱波" / "賣價隱波" terminology — cosmetic, low value.
- Add color (red/green) formatting to `漲跌幅%` and `達標報酬%` columns. Streamlit `column_config` does not support per-cell color directly; would need DataFrame Styler which then loses pinned-column behaviour. Not worth this round.
