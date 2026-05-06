# Auto-Audit Overnight Loop — Summary

**Target end**: 2026-05-07 06:00 Asia/Taipei
**Branch**: main (commit + push directly)
**Process**: every hour, review agent + implementation agent

| Round | Time (TW) | Status | Commit | Files | Notes |
|---|---|---|---|---|---|
| 1 | 2026-05-07 00:30 | ✅ success | `7f82baf` | streamlit_app.py | 等效Δ 顯示 + 情境表 tooltip + 重複風險警示 |
| 2 | 2026-05-07 01:45 | ⚠️ partial | `cd19da9` | streamlit_app.py | 候選表 default sort by 成交量↓；Delta-aware OTM 模型 reverted（test fixture Delta 不真實，需先 refactor）|

## Round details

### Round 1 — 2026-05-07 00:30
- Review proposed 3 items, picked 1+2 (small/low-risk)
- Item A: 候選表 Delta → 等效Δ；bubble chart 同步
- Item B: 情境表 12 欄加 tooltip；三檔風險相同時加 caption
- Skipped #3 (Delta-aware OTM model) — medium risk，留下輪
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-1/{review.md, implementation.md, screenshots/, screenshots-after/}`

### Round 2 — 2026-05-07 01:45
- Review picked 2 items (Round 1 skipped #3 + new sort)
- Item A (Delta-aware OTM downside): **REVERTED**。公式正確但測試 fixture `_call()` 用 `delta=0.5`（不真實，實際 per-unit Δ ~0.002），導致：
  - 新 test 因 delta_shadow 太大被 clamp 到 -100% 不嚴格遞減
  - 既有 test_evaluate_scenarios_filters_and_sorts 因虛擬 delta 過大讓「不該獲利」的 case 變獲利
  - 解法：先 refactor test fixture 用 `equivalent_delta × ratio` 反推真實 per-unit delta，再開 Item A
- Item B (default sort 成交量↓): ✅ 成功。候選表最高量在頂端，使用者仍可點 header 自排
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-2/{review.md, implementation.md, screenshots*/}`
