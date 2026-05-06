# Auto-Audit Overnight Loop — Summary

**Target end**: 2026-05-07 06:00 Asia/Taipei
**Branch**: main (commit + push directly)
**Process**: every hour, review agent + implementation agent

| Round | Time (TW) | Status | Commit | Files | Notes |
|---|---|---|---|---|---|
| 1 | 2026-05-07 00:30 | ✅ success | `7f82baf` | streamlit_app.py | 等效Δ 顯示 + 情境表 tooltip + 重複風險警示 |
| 2 | 2026-05-07 01:45 | ⚠️ partial | `cd19da9` | streamlit_app.py | 候選表 default sort by 成交量↓；Delta-aware OTM 模型 reverted（test fixture Delta 不真實，需先 refactor）|
| 3 | 2026-05-07 03:05 | ✅ success | `8c17e63` | streamlit_app.py | Header 加標的現價/目標/預期漲跌幅 metric；3 卡片重複 caption 收斂為 1 條；底部 Mock 隨機走勢圖 gate Mock-only |
| 4 | 2026-05-07 04:25 | ✅ success | `0464e7a` | streamlit_app.py | 進階閾值 expander 中文化；call/put 方向 vs target 衝突警示；sidebar 加 2 條 divider |

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

### Round 3 — 2026-05-07 03:05
- Review proposed 3 small items, picked 全部 3 個（risk 都低）
- Item 1: Top-3 卡片內重複 3 次的「三檔風險情境報酬相同」caption → 改成單一 `st.info` 顯示在卡片區上方
- Item 2: 結果頁頂部加 3-column metric（反推標的現價、目標價、預期漲跌幅%），免捲動就看到情境關鍵資訊
- Item 3: 底部合成走勢圖（spot_path = 1100 + ...）gate 在 Mock 來源；yuanta/TWSE/CSV 不再顯示
- Skipped (留下輪): Delta-aware OTM 仍待 fixture refactor；put 方向的 risk_drops_pct 標籤誤導；yuanta 0 結果 raise → 友善 empty state
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-3/{review.md, implementation.md, screenshots*/}`

### Round 4 — 2026-05-07 04:25
- Review proposed 3 小範圍低風險的改進，全做
- Item 1: 進階：硬過濾閾值 expander 把 `stable`/`aggressive` 英文 slug 換成「穩健型」/「進攻型」中文（widget keys 保留英文以維持 state identity）
- Item 2: 情境模擬 metric 後加方向衝突警示——「call + 目標 < 現價」或「put + 目標 > 現價」時提示使用者考慮換方向
- Item 3: sidebar 加兩條 `st.divider()` 把版面分為標的/情境/進階/開始分析 四組
- Skipped (留下輪): Delta-aware OTM（仍待 fixture refactor）；put-side risk_drops_pct 語義；yuanta empty result 友善 empty state；README 補上等效Δ/情境模擬說明
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-4/{review.md, implementation.md, screenshots*/}`
