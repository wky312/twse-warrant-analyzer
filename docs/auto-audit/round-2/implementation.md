# Round 2 Implementation Report

## Summary
- **Successes**: 1 (Item B — sort candidate table by 成交量 desc)
- **Failures**: 1 (Item A — Delta-aware downside model)
- **Blockers**: Test fixture in `tests/test_scenario.py` uses unrealistic `delta=0.5` for all synthetic warrants, which makes the proposed Delta-shadow formula physically too aggressive for the synthetic test data. Reverted per user instruction.

## Item A: Delta-aware downside model — FAILED, REVERTED

### Status
Failed pytest. Reverted via `git checkout -- src/twse_warrant/analyzers/scenario.py tests/test_scenario.py`.

### What was tried
Implemented exactly as the user specified:
```python
if intrinsic_target > 0:
    return intrinsic_target + time_value_target
eq_delta = w.equivalent_delta
if eq_delta is None:
    return time_value_target
delta_shadow = eq_delta * (spot_target - spot_now) * ratio
return max(time_value_target + delta_shadow, 0.0)
```

Added the `test_otm_downside_is_monotone` test verbatim.

### Failures observed
Two test failures (1 new, 1 regression):

1. **`test_otm_downside_is_monotone` (new test)** — failed with:
   ```
   expected monotone decrease, got -29.28932188134524/-100.0/-100.0
   ```
   Root cause: `_call()` test helper hardcodes `delta=0.5`, so `equivalent_delta = 0.5 / 0.005 = 100`. The formula `eq_delta × ΔS × ratio` simplifies to `delta × ΔS = 0.5 × ΔS`. For -5%/-10% drops, `delta_shadow = 0.5 × (-112.5) = -56.25` and `0.5 × (-225) = -112.5`. Both are far more negative than `time_value_target ≈ 0.354`, so `max(time_value_target + delta_shadow, 0)` clamps to 0 in both cases → r5 == r10 == -100% (not strictly monotone).

2. **`test_evaluate_scenarios_filters_and_sorts` (existing, regressed)** — failed with:
   ```
   AssertionError: assert 'C' not in ['C', 'B', 'A']
   ```
   Root cause: Synthetic warrant C has `strike=3000, spot_now=2250, delta=0.5`. Under the new formula at `target=2800` (still OTM): `delta_shadow = 0.5 × (2800 - 2250) = 275`. This makes `expected_W ≈ 275` versus `last_price=0.3`, generating a huge "profit" → C now passes the `require_profit_at_target` filter and the test breaks.

### Why this happened
The test `_call()` factory uses an unrealistic `delta=0.5` (per-unit dW/dS). Real Yuanta data per the model docstring uses `delta ≈ 0.0021` for a typical warrant. The proposed formula is mathematically correct (`dW = delta × dS`) but the synthetic fixture data is not consistent with the model's expected magnitude.

### Recommendation for next round
Either:
- (a) Update `_call()` to compute `delta` from `eq_delta × ratio` with a realistic `eq_delta` (e.g. 0.5), so `delta = 0.5 × 0.005 = 0.0025`. Existing tests would need recalibration.
- (b) Use Theta-aware decay or a `(eq_delta × ΔS)` term clamped to a fraction of current price to limit blow-up.
- (c) Adopt a regime-aware blend: deep OTM → smaller Delta-shadow weight.

## Item B: Sort candidate table by 成交量 desc — SUCCESS

### Status
Pass. 32/32 pytest. AST OK. Streamlit HTTP 200. Visually verified.

### File diff
`src/streamlit_app.py`:
```diff
 if result.candidates:
     df = pd.DataFrame([warrant_to_row(w) for w in result.candidates])
+    if "成交量" in df.columns:
+        df = df.sort_values("成交量", ascending=False, na_position="last").reset_index(drop=True)
     st.dataframe(
         df, use_container_width=True, hide_index=True,
         column_config=PINNED_COLUMNS,
     )
```

### Visual verification
Screenshot `01-candidates-sorted.png` shows 成交量 column descending: 3604 → 3169 → 3061 → 2735 → 2654 → 2415 → 2368 → 2271 → 2125. Confirmed sorted.

## pytest count
**32 passed in 0.06s** (unchanged baseline — Item A reverted, no new test added).

Expected was 33; actual is 32 because Item A's new test was reverted along with the failed implementation per user instructions.

## Screenshots
- `/Users/KunYang/Claude/twse-warrant-analyzer/docs/auto-audit/round-2/screenshots-after/01-candidates-sorted.png` — candidate table sorted by 成交量 desc
- `/Users/KunYang/Claude/twse-warrant-analyzer/docs/auto-audit/round-2/screenshots-after/02-scenario-table.png` — scenario table
- `/Users/KunYang/Claude/twse-warrant-analyzer/docs/auto-audit/round-2/screenshots-after/03-top3-cards.png` — Top-3 cards (risk rows still IDENTICAL since Item A reverted)

## Anomalies
- Top-3 cards still show identical risk numbers across 平盤/-5%/-10% (e.g. -21.7%/-21.7%/-21.7% for #1, -21.1%/-21.1%/-21.1% for #2). The existing warning paragraph "三檔風險情境報酬相同：標的在所有下跌情境皆深度價外，模型目前只反映時間價值衰減（Delta-aware OTM 模型留待後續輪次補強）" remains accurate — the audit signal that motivated Item A is still present and unfixed.
- The Streamlit log path is `/tmp/twse_warrant_streamlit.log`.
