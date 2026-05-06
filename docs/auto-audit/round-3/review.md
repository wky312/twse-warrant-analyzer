# Round 3 Review — 2026-05-07 03:00 (Asia/Taipei)

## Observations

- R1 + R2 changes are landed and visible: candidate table top row sorted by 成交量↓ (3604 → 3169 → 3061 …), 等效Δ column present on the candidate table, bubble chart spreads bubbles from |等效Δ| 0.2~0.7, scenario table tooltips configured, Top-3 cards each carry the "三檔風險情境報酬相同" caption (screenshots `02-results-top.png`, `03-candidates.png`, `04-scenario.png`, `04b-scenario-table.png`, `05-cards.png`).
- Top-3 cards still show identical risk numbers across 平盤 / 跌5% / 跌10% (#1: -21.7% × 3, #2: -21.1% × 3, #3: -29.0% × 3). This is the still-unresolved Delta-aware OTM gap that R2 reverted; touching it again requires the test fixture refactor first (see "Skipped" below).
- The identical-risk caption is rendered **once per card**, so it appears 3 times in a row (snapshot e526 / e601 / e676). The repetition was flagged as "Skipped (next time)" in R2 — moving it to a single notice above the cards is a cheap, user-visible win.
- Bottom "📈 標的股價 vs Top 推薦權證價（示意）" chart hard-codes `spot_path = 1100 + …` while the real 2330 spot is 2250. In real-data mode the chart is meaningless: the y-axis number doesn't even match the underlying. Caption admits "Mock 模式為合成走勢" but the chart still renders for `yuanta` runs (screenshot `06-charts.png`). Cleanest small fix: gate the chart behind Mock-source only OR center the synthetic walk on `spot_now`.
- **New finding from put flow (`07-put-scenario.png`)**: 認售 + 2330 + target=1800 produces `分析失敗：All fetchers failed. Last error: yuanta returned 0 warrants`. This is a "no put warrants for this underlying" condition surfaced as an exception rather than a friendly empty state. The exception comes from `YuantaFetcher` raising when the filtered list is empty; the analyze-loop already has a `if not oriented: notes.append(...)` branch in `rank.py:234-238` that would have produced a clean "目前無認售權證掛牌" notice — but that branch is dead because the fetcher errors out before `analyze_warrants` runs. UX-wise, "no warrants in this direction" should not look like a system failure.
- Result-page header is currently 3 nested `st.success` / `st.info` blocks (資料來源 / [stable] 排除 / [aggressive] 排除). It does NOT surface 標的現價 or scenario 預期漲跌幅 — those only appear inside the scenario section, far below the candidate table. Bringing 反推現價 to the top would let the user spot scenarios like "target ≪ spot" before scrolling.
- 達標報酬% column is still 13th in the scenario table (off-screen on a 1280px viewport). R2 noted this and skipped because it requires a column-order decision; not picked this round either to keep risk low.
- `ScenarioInputs.risk_drops_pct` defaults to `(0.0, -5.0, -10.0)` — meaningful only for **call** holders. For **put** scenarios the same triplet describes drops in the underlying, which actually *help* the put. The labels in the cards / scenario table (`平盤`, `跌5%`, `跌10%`) become misleading because for a put a 10% drop in spot is a tailwind, not a risk. Put-side risk should be `(0.0, +5.0, +10.0)` or relabelled as "標的±N%". This is a real correctness bug for put flows but cannot be reliably reproduced today (no put data for 2330 from yuanta) — flagging for backlog.
- `import numpy as np` and `import plotly.graph_objects as go` are imported only inside the bottom Mock chart block. Acceptable, but if the Mock chart is gated/dropped, the `np` import becomes dead.
- Tests still 32/32 passing in `0.04s` after R2.

## Proposed Changes

### 1. Collapse the 3× repeated identical-risk caption into a single notice above the Top-3 cards

- **File**: `src/streamlit_app.py:484-511` (the `for i, r in enumerate(scen_results[:3], 1)` block)
- **Scope**: small (~10 lines)
- **Risk**: very low — purely UI rearrangement, no logic change
- **Expected effect**:
  - Replaces three identical caption paragraphs (one per card) with one shared notice rendered once above the 3-card section, only when **all three** Top cards have identical risk-row triplets.
  - Cards become visually cleaner; the warning is still discoverable.
- **Steps**:
  1. Before the `for i, r in enumerate(scen_results[:3], 1):` loop, compute
     `top3 = scen_results[:3]` and check whether **every** card in `top3` has `risk_flat == risk_5 == risk_10`. If yes, render the caption once via `st.info(...)` (or `st.caption`) above the loop.
  2. Inside the loop, keep computing `risk_flat / risk_5 / risk_10` for the three columns but **drop** the per-card `if risk_flat == risk_5 == risk_10: st.caption(...)` block.
  3. No tests needed (UI-only).
  4. Visual verification: re-run 2330 認購 target=2800/60-day → expect a single yellow info bar above #1 card, and no caption duplicated under each card.

### 2. Surface 標的現價 + 預期漲跌幅 in the result-page header (when scenario enabled)

- **File**: `src/streamlit_app.py:294-296` (right after `st.success(f"資料來源…")` / `st.info(note)` block)
- **Scope**: small (~12 lines, single file)
- **Risk**: very low — `spot_now` reverse-derivation already exists at line 372-379; we just need to lift it earlier, OR copy the same logic up-top.
- **Expected effect**:
  - Top of results gets a 3-column `st.metric` row: 標的現價 (反推) | 目標價 (if scenario) | 預期漲跌幅 %.
  - User immediately sees whether the target is realistic (e.g. +24.4% in 60 days) without scrolling past the candidate table to find the scenario section's caption.
  - Removes the duplicate caption at line 420 if we centralize the metrics.
- **Steps**:
  1. Move `spot_now` computation (lines 372-379) up to right after `result = …` (before line 294's `st.success`).
  2. After the data-source success banner, if `scenario_enabled and spot_now is not None`, render:
     ```python
     mc1, mc2, mc3 = st.columns(3)
     mc1.metric("反推標的現價", f"{spot_now:.1f}")
     mc2.metric(f"目標價 ({scenario_days} 天後)", f"{scenario_target:.0f}")
     pct = (scenario_target / spot_now - 1) * 100.0
     mc3.metric("預期漲跌幅", f"{pct:+.1f}%")
     ```
  3. Drop the now-redundant `st.caption(f"反推標的現價 …")` at line 420.
  4. No new tests needed.
  5. Visual: re-run default flow; new header strip should appear between "資料來源：yuanta | 原始候選：905 檔" and the [stable] excluded-Greeks notice.

### 3. Gate the bottom synthetic random-walk chart behind Mock-source only

- **File**: `src/streamlit_app.py:549-571`
- **Scope**: small (~3 lines; one `if` wrap)
- **Risk**: very low — nothing else depends on this chart.
- **Expected effect**:
  - In real-data modes (yuanta / TWSE / CSV) the misleading "spot at 1100 vs real spot 2250" chart simply doesn't render.
  - In Mock mode, behaviour unchanged (chart still rendered, caption still says "合成走勢").
  - Page becomes shorter and more honest in real-data flows.
- **Steps**:
  1. Wrap the entire block (lines 549-571, the section starting `top_for_chart: list[ScoredWarrant] = []` through the final `st.plotly_chart(...)`) in `if source == "合成樣本 (Mock)":`.
  2. Move `import numpy as np` to the top of the file with other imports (or leave as-is inside the gated block; either works). If imports are tidied, ensure `pyflakes`/Streamlit reload still passes.
  3. No tests touched.
  4. Visual: yuanta run should now end at the Delta-explanation expander; Mock run should still show the dual-axis line chart.

## Skipped (next time)

- **Delta-aware OTM downside (R1#3 / R2 reverted)** — still the highest-impact item but blocked on test-fixture refactor. The 2-step plan: (a) update `_call()` in `tests/test_scenario.py` so `delta = realistic_eq_delta × ratio` (e.g. `delta = 0.5 × 0.005 = 0.0025`) and recalibrate the 8 affected assertions; (b) THEN add the `eq_delta × ΔS × ratio` term to `_project_warrant_price` for `intrinsic_target == 0` branch with a `max(..., 0.0)` clamp. Skipped this round because step (a) alone touches existing test expectations and is a medium-risk job that deserves dedicated attention.
- **Put-side `risk_drops_pct` semantics**: `(0.0, -5.0, -10.0)` is a real bug for put flows (drops are the put's tailwind, not risk). Fix is to make the tuple direction-aware in `streamlit_app.py:426`: pass `(0.0, +5.0, +10.0)` when `direction == "put"` and relabel column headers to "漲5%報酬%" / "漲10%報酬%". Not picked this round because we couldn't reproduce a put scenario live (yuanta returned 0 puts for 2330) and the change touches column-name strings used in `SCENARIO_COLUMN_CONFIG` keys.
- **Empty-fetcher → friendly notice**: `YuantaFetcher` should not raise when 0 warrants match the symbol/direction filter; instead `analyze_warrants` already has a graceful "目前無 X 權證掛牌" branch that's currently bypassed. Needs a fetcher-side fix (return `[]` instead of `raise`). Out-of-scope for a single-file ≤50-line change — would touch the fetcher class and the streamlit error handler.
- **達標報酬% column reorder** to push it left of `價內外% / 天期` etc. Pure UX call, no clear winner without a usage study.
- Color-coding 漲跌幅% / 達標報酬% — same Streamlit limitation as R1/R2 (column_config has no per-cell color).
