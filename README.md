# 台股權證分析工具 (twse-warrant-analyzer)

輸入個股代碼（例：2330），撈出該標的所有上市認購/認售權證，並依風格推薦：
- **低隱波穩健型**：低 IV、窄價差、中長天期
- **高槓桿進攻型**：高槓桿、高 Delta、高成交量

## 安裝

```bash
cd /Users/KunYang/Claude/twse-warrant-analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 使用方式

### Streamlit UI（建議）

```bash
streamlit run src/streamlit_app.py
```

輸入標的 → 選方向（認購/認售）→ 選資料來源 → （可選）啟用情境模擬 + 目標價 + 目標日期 → 看候選清單（依成交量排序）+ IV × |等效Δ| 散點圖 +（情境模式）達標報酬表 + Top-3 卡片

#### 情境模擬（建議搭配 Yuanta）

於側欄勾選「🎯 啟用情境模擬」，輸入目標標的價與目標日期（或天數）後重新分析，將額外得到：
- 反推標的現價 / 目標價 / 預期漲跌幅 metric 列
- 達標時的權證價、報酬率、損益兩平、平盤 / 跌 5% / 跌 10% 風險情境
- 達標報酬率 Top-3 卡片
- 方向衝突警示：若認購搭配下跌目標、或認售搭配上漲目標，會提示換方向

計算邏輯：`權證達標價 = 目標日內含值 + 現有時間價值 × √(剩餘天數 / 現在天期)`

### Python API

```python
from twse_warrant import analyze
from twse_warrant.fetchers.mock import MockFetcher
from twse_warrant.fetchers.csv_fetcher import CSVFetcher

# 用 mock 資料 demo
result = analyze(
    "2330",
    direction="call",
    profiles=("stable", "aggressive"),
    fetchers=[MockFetcher(count=40, seed=42)],
    top_n=5,
)

for profile, recs in result.recommendations.items():
    print(f"=== {profile} ===")
    for s in recs:
        print(f"{s.warrant.symbol} {s.warrant.name} | score {s.total_score:.1f}")
        print(f"  優勢：{', '.join(s.top_strengths)}")
        for w in s.warnings:
            print(f"  ⚠ {w}")
```

### 自備 CSV 資料

從券商網站 / Yahoo 手動匯出表格 → 存成 CSV → 上傳到 Streamlit 或：

```python
result = analyze(
    "2330", direction="call",
    fetchers=[CSVFetcher("path/to/2330_warrants.csv")],
)
```

CSV 必需欄位：`權證代碼`。其他欄位（成交價、IV、Delta…）有對應的話自動讀取，缺則為 `None`。
中英欄名都支援；參考 `src/twse_warrant/fetchers/csv_fetcher.py` 的 `COLUMN_ALIASES`。
- 表頭顯示「等效Δ」（教科書 0~1 Delta），由原始 per-unit Delta ÷ 行使比例算得，方便跨權證比較跟漲能力。

## 架構

```
fetcher (mock / csv / yahoo* / yuanta*) → orchestrator → list[Warrant]
                                                              ↓
                              analyzer (filter → normalize → rank)
                                                              ↓
                                                    AnalysisResult
                                                              ↓
                                          UI (Streamlit / FastAPI / ...)
```

`*` = scaffold，見下方「資料來源狀態」。

### 模組

| 模組 | 用途 |
|---|---|
| `twse_warrant.models` | `Warrant`、`ScoredWarrant`、`AnalysisResult` dataclass |
| `twse_warrant.fetchers` | 資料來源（base / mock / csv / yahoo / yuanta / orchestrator） |
| `twse_warrant.analyzers.filters` | 硬過濾閾值（per profile） |
| `twse_warrant.analyzers.normalize` | 0-100 正規化（lower/higher/target/target_median） |
| `twse_warrant.analyzers.profiles` | 兩個 profile 的權重表 |
| `twse_warrant.analyzers.rank` | 評分、排名、優劣勢、警示 |
| `twse_warrant.api.analyze` | 對外 API（fetch + analyze 一條龍） |

## 推薦演算法重點

兩個 profile 的權重表（總和 1.0）：

| 特徵 | 穩健型 | 進攻型 |
|---|---|---|
| IV (買賣中位) | **0.28** | 0.04 |
| 買賣價差比 | 0.18 | 0.13 |
| 剩餘天數 | 0.14 | 0.10 |
| 成交量 | 0.13 | 0.15 |
| \|Delta\| | 0.10 | 0.18 |
| 實質槓桿 | 0.07 | **0.30** |
| 流通在外比例 | 0.06 | 0.03 |
| 成交筆數 | 0.04 | 0.07 |

> Streamlit UI 主畫面顯示通過硬過濾的「候選清單」聯集 + 散點圖 +（情境模式）達標報酬表，兩個 profile 的權重表只在過濾與評分階段使用，不再單獨顯示推薦表。

詳細 filter 閾值與正規化細節請見 plan: `/Users/KunYang/.claude/plans/image-1-image-2-noble-finch.md`

## 資料來源狀態

| Fetcher | 狀態 | 提供欄位 |
|---|---|---|
| `YuantaFetcher` ⭐ | ✅ **推薦** | 元大權證網 `/ws/GetWarData.ashx`：完整 IV/Delta/Theta/履約價/行使比例/到期日/流通在外/實質槓桿/價內外 |
| `TWSEFetcher` | ✅ 可用 | 證交所每日全市場權證行情（`MI_INDEX?type=0999/0999P`）；缺 Greeks → 自動進 lite mode |
| `MockFetcher` | ✅ 可用 | 合成資料 demo |
| `CSVFetcher` | ✅ 可用 | 讀手動匯出的 CSV，欄位中英文彈性對應 |
| `YahooFetcher` | ⚠️ scaffold | Yahoo 個股權證頁是 React JS 渲染，需 Playwright |

**Lite mode**：當 >80% 權證缺 Greeks（如 TWSE 來源）時自動啟用，跳過 IV/Delta/天期/槓桿
評分，僅用成交量、買賣價差、成交筆數、流通比例打分；穩健 vs 進攻的差別會縮小但仍存在。

### 加上 Playwright 抓真資料（未來工作）

`fuhwa-fund-dashboard` 已示範 Playwright 模式。可參考其 `scripts/scrape-nav.ts`，
寫個 `src/twse_warrant/fetchers/playwright_fetcher.py` 開瀏覽器渲染 Yahoo / 元大頁面後取資料。

## 測試

```bash
pytest tests/
```

32 個單元測試覆蓋 filter、normalize、rank、CSV 解析。

## 部署選項

設計刻意把 core 與 UI 解耦，未來可：
- **Streamlit Cloud**：直接 deploy `src/streamlit_app.py`
- **Vercel**：包 `fastapi_app.py` 用 FastAPI 暴露 `/analyze` REST
- **Lovable / 其他**：呼叫 FastAPI endpoint
- **CLI / 排程**：直接 import `analyze()` 寫 script
