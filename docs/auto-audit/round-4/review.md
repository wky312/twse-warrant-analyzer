# Round 4 Review — 2026-05-07 04:20 (Asia/Taipei)

## Observations

- All R1–R3 changes are landed and visible (`screenshots/02-header-metrics.png`):
  - 反推標的現價 / 目標價 / 預期漲跌幅 metric strip sits cleanly between the data-source banner and the candidate table.
  - Candidate table is sorted by 成交量 desc (4851 → 3604 → 3169 → 3061 …).
  - Top-3 cards (`screenshots/05-cards.png`) carry **one** yellow info notice above them; no per-card duplicate caption.
  - Page bottom (`screenshots/06-bottom.png`) ends at the Delta-explanation expander — no synthetic random-walk chart in yuanta mode (`document.body.innerText.includes('標的股價 vs Top 推薦權證價') === false`).
- 32/32 tests still pass.
- **NEW finding — overrides expander leaks internal profile slugs** (`screenshots/07-overrides.png`): when 啟用自訂閾值 is checked, the expander renders two sections labelled `**stable**` and `**aggressive**`, plus 8 sliders prefixed `[stable] 剩餘天數 ≥ …` / `[aggressive] IV ≤ …`. Everywhere else in the UI those profiles are rendered in 中文 (e.g. landing page table uses 「低隱波穩健型」/「高槓桿進攻型」). The override expander is the only place a non-developer user is exposed to the raw English keys.
- **NEW finding — overrides expander has questionable utility**: per R0/R1 notes the recommendation tables `result.recommendations[profile]` are not rendered on the main page (only the candidates union + scenario table is shown). The 8 sliders only affect the hard-filter pre-screen (which DOES feed `result.candidates`), so they're not entirely dead — but the labelling implies they tune two separate "風格" outputs that the user never sees.
- **NEW finding — sidebar is inconsistently grouped**: scenario block has `st.markdown("---")` to separate it from the data-source/Top-N section, but no divider sits between Top-N and 啟用情境模擬, nor between the scenario block and 進階：硬過濾閾值. After a viewport resize the run button + override expander + scenario calendar visually merge into one column.
- **NEW finding — scenario sanity check missing**: `ScenarioInputs.target_price` is taken at face value. If a user picks 認購 (call) but enters target=2000 when 反推現價=2250 (a 11% drop instead of a rise), the engine produces 0 results because `require_profit_at_target` filters every candidate out — and the user gets the generic warning "沒有權證在這個情境下能獲利（過濾後無候選）。試著放寬目標、延長日期、或降低流動性條件。". It does NOT tell them their target is in the wrong direction. The new R3 metric strip already exposes 預期漲跌幅 (e.g. `+24.4%`); when the sign disagrees with `direction`, a one-line warning would short-circuit confusion. Same applies symmetrically to put + target > spot.
- README hasn't been touched since R0; no mention of 等效Δ, scenario simulation, or the 反推現價 metric. Out of scope for this round (≤ 50-line single-file rule), noting for backlog.
- 達標報酬% column still off-screen on a 1280px viewport (column 14 of 16). Not picked again — same UX call dilemma as R2 / R3.
- `import plotly.graph_objects as go` (line 7) and `import numpy as np` (line 4) are now only used inside the Mock-only chart block. After R3's gate this is fine — no actionable cleanup.

## Proposed Changes

### 1. Replace English profile slugs with Chinese labels in the overrides expander

- **File**: `src/streamlit_app.py:108-130` (the `with st.sidebar.expander("進階：硬過濾閾值（覆寫預設）"):` block)
- **Scope**: tiny (~8 lines edited, 0 added)
- **Risk**: very low — pure UI string change; `custom[p]` keying still uses the internal `Profile` slug.
- **Expected effect**: a Chinese-speaking user no longer sees `**stable**` / `[stable] IV ≤` /  `[aggressive] 成交量 ≥ …` in an otherwise all-中文 sidebar. UI feels professional and consistent with the landing-page reference table («低隱波穩健型 / 高槓桿進攻型»).
- **Steps**:
  1. Define a small label dict near line 33 (next to the `profiles` tuple):
     ```python
     PROFILE_LABELS_ZH: dict[Profile, str] = {
         "stable": "穩健型",
         "aggressive": "進攻型",
     }
     ```
  2. Inside the loop at line 112, replace `st.markdown(f"**{p}**")` with `st.markdown(f"**{PROFILE_LABELS_ZH[p]}**")`.
  3. Replace the 4 `f"[{p}] 剩餘天數 ≥"` / `f"[{p}] 成交量 ≥"` / `f"[{p}] 買賣價差比 ≤"` / `f"[{p}] IV ≤"` slider labels with `f"[{PROFILE_LABELS_ZH[p]}] 剩餘天數 ≥"` etc. Keep the `key=f"d_{p}"` etc. unchanged so Streamlit widget identity is preserved (no state loss).
  4. No new tests — UI strings only. Quick visual: open expander, expect to see headers 「穩健型」/「進攻型」 and slider labels `[穩健型] IV ≤`, `[進攻型] 成交量 ≥` etc.

### 2. Warn when scenario target direction disagrees with 認購/認售

- **File**: `src/streamlit_app.py:309-316` (right after the existing 反推現價 / 目標 / 預期漲跌幅 metric strip)
- **Scope**: small (~8 lines)
- **Risk**: very low — adds one `st.warning` based on already-computed `pct` and the existing `direction` variable; no logic in `scenario.py` changes.
- **Expected effect**:
  - If `direction == "call"` and `pct < 0` (i.e. user picked 認購 but the target is below current spot), surface
    `「目標價 {target} 低於反推現價 {spot}（-X.X%）。認購權證在標的下跌時通常虧損 — 您是否想改選認售？」`
  - Symmetric for `direction == "put"` and `pct > 0`.
  - The warning also explains why the scenario table afterwards is empty (current generic empty-state message just blames filters).
- **Steps**:
  1. After line 315 (the 3-column `mc1.metric / mc2.metric / mc3.metric` block) add:
     ```python
     if direction == "call" and pct < 0:
         st.warning(
             f"目標價 {scenario_target:.0f} 低於反推現價 {spot_now:.1f}（{pct:+.1f}%）。"
             f"認購權證在標的下跌時通常虧損 — 您是否想改選「認售 (put)」？"
         )
         elif_done = True
     elif direction == "put" and pct > 0:
         st.warning(
             f"目標價 {scenario_target:.0f} 高於反推現價 {spot_now:.1f}（{pct:+.1f}%）。"
             f"認售權證在標的上漲時通常虧損 — 您是否想改選「認購 (call)」？"
         )
     ```
     (Drop the `elif_done = True` line; only included to flag the symmetric pairing.)
  2. No tests touched — `scenario.py` already returns the right (empty) results; this is purely a UI-side guard.
  3. Quick visual: 認購 + target=2000 + 60d → expect a yellow warning bar before the candidate table; 認購 + target=2800 → no warning (default flow unaffected).

### 3. Add `st.divider()` between Top-N and 啟用情境模擬 in the sidebar (visual grouping)

- **File**: `src/streamlit_app.py:61-65` (between `top_n = st.sidebar.slider(...)` and `st.sidebar.markdown("---")`)
- **Scope**: tiny (~1 line — replace the existing `st.sidebar.markdown("---")` at line 64 with `st.sidebar.divider()` and add one before line 108 for the 進階 expander)
- **Risk**: very low — purely visual.
- **Expected effect**: sidebar reads as four clear groups: 標的設定 / 情境模擬 / 進階閾值 / 開始分析. Today the only divider sits before scenario; the override expander runs straight into the run button (`screenshots/07-overrides.png` — IV slider directly abuts 開始分析 in red).
- **Steps**:
  1. Replace line 64 `st.sidebar.markdown("---")` with `st.sidebar.divider()`. (cosmetic but uses the modern Streamlit primitive.)
  2. Insert `st.sidebar.divider()` immediately before line 108 `with st.sidebar.expander("進階：硬過濾閾值（覆寫預設）"):`.
  3. No tests touched.
  4. Quick visual: sidebar should now have a thin grey rule before 🎯 啟用情境模擬, AND another before 進階：硬過濾閾值.

## Skipped (next time)

- **Delta-aware OTM downside** (R1#3 / R2 reverted / R3 deferred) — still highest-impact but blocked on `tests/test_scenario.py:_call()` fixture refactor (per R3 review). One-shot plan: (a) change `_call(... delta=0.5 ...)` → `_call(..., equivalent_delta=0.5, ...)` and recompute per-unit `delta = equivalent_delta * ratio` inside `_call`; (b) re-baseline 8 affected assertions (most will be unaffected since they target ITM); (c) THEN add `eq_delta * (S_target - S_now) * ratio` term to `_project_warrant_price` for `intrinsic_target == 0` branch. Not picked because step (a) alone has too many failure modes for an overnight low-supervision round.
- **Put-side `risk_drops_pct` semantics**: `(0.0, -5.0, -10.0)` is misleading for puts (drops help puts). Need direction-aware tuple + dynamic column names (跌5%報酬% → 漲5%報酬% for puts). Touches `SCENARIO_COLUMN_CONFIG` keys + `risk_returns.get(...)` lookups; cross-cuts ~12 lines and risks breaking column-config tooltips. Hold for a dedicated round.
- **`YuantaFetcher` raises on empty result** instead of returning `[]` and letting `analyze_warrants` produce the friendly "目前無認售權證掛牌" notice. Two-file fix (fetcher + streamlit error handler) — out of single-file scope.
- **README freshness** (no mention of 等效Δ / scenario / 反推現價). Touches non-code surface; defer to a docs-only round if one is scheduled.
- **達標報酬% column reorder** to push it left of 損益兩平 / 天期. Pure UX call; same dilemma as R2 / R3.
- **Color-coding 漲跌幅% / 達標報酬%** — Streamlit `column_config` still has no per-cell color in this version.
