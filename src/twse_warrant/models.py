"""核心資料結構."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

Direction = Literal["call", "put", "all"]
Profile = Literal["stable", "aggressive"]


@dataclass
class Warrant:
    """單檔權證的完整欄位.

    來源: Yahoo / 群益 / TWSE 合併後的最大集合.
    """

    symbol: str                          # 權證代碼，例 "081234"
    name: str                            # 權證名稱
    underlying_symbol: str               # 標的代碼，例 "2330"
    underlying_name: str = ""            # 標的名稱，例 "台積電"
    direction: Direction = "call"        # call / put

    # 行情
    last_price: Optional[float] = None   # 成交價
    change: Optional[float] = None       # 漲跌
    change_pct: Optional[float] = None   # 漲跌幅 %
    volume: Optional[int] = None         # 成交量（張）
    trade_count: Optional[int] = None    # 成交筆數

    # 報價
    bid_price: Optional[float] = None    # 買價
    ask_price: Optional[float] = None    # 賣價
    bid_ask_spread_pct: Optional[float] = None  # 買賣價差比 %

    # 合約條件
    strike: Optional[float] = None       # 履約價
    exercise_ratio: Optional[float] = None  # 行使比例
    issue_date: Optional[date] = None    # 上市日期
    last_trade_date: Optional[date] = None  # 最後交易日
    maturity_date: Optional[date] = None    # 到期日
    days_to_expiry: Optional[int] = None    # 剩餘天數
    issued_units: Optional[int] = None      # 最新發行張數
    outstanding_units: Optional[int] = None  # 流通在外張數
    outstanding_pct: Optional[float] = None  # 流通在外比例 %

    # Greeks / IV
    iv_buy: Optional[float] = None       # 買價隱波 %
    iv_sell: Optional[float] = None      # 賣價隱波 %
    delta: Optional[float] = None
    theta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None

    # 衍生指標
    leverage: Optional[float] = None     # 實質槓桿
    moneyness_pct: Optional[float] = None  # 價內外程度 % (正=價內, 負=價外)

    issuer: Optional[str] = None         # 發行券商
    option_type: Optional[str] = None    # '歐式' / '美式'

    @property
    def iv_mid(self) -> Optional[float]:
        """買賣價隱波中位."""
        vals = [v for v in (self.iv_buy, self.iv_sell) if v is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    @property
    def equivalent_delta(self) -> Optional[float]:
        """教科書標準化 Delta (0~1 for call, -1~0 for put).

        台灣權證 API 給的 Delta 是 per-unit 的 dW/dS，需除以行使比例才是
        教科書版本。例如 FLD_DELTA=0.0021、行使比例=0.003 → 等效 Delta = 0.700.
        """
        if self.delta is None or self.exercise_ratio is None or self.exercise_ratio == 0:
            return None
        return self.delta / self.exercise_ratio

    @property
    def spread_to_leverage(self) -> Optional[float]:
        """差槓比 = 買賣價差比% / 實質槓桿.

        越低越好：用 1% 槓桿換來的價差成本越小。
        例：價差 2%、槓桿 5x → 0.40，比 價差 4%、槓桿 5x → 0.80 划算。
        """
        if (
            self.bid_ask_spread_pct is None
            or self.leverage is None
            or self.leverage == 0
        ):
            return None
        return self.bid_ask_spread_pct / self.leverage


@dataclass
class ScoredWarrant:
    """評分後的權證輸出."""

    warrant: Warrant
    profile: Profile
    total_score: float                                  # 0-100
    feature_scores: dict[str, float] = field(default_factory=dict)
    top_strengths: list[str] = field(default_factory=list)
    top_weaknesses: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def symbol(self) -> str:
        return self.warrant.symbol

    @property
    def name(self) -> str:
        return self.warrant.name


@dataclass
class AnalysisResult:
    """分析結果，可包含一或兩個 profile 的推薦."""

    underlying: str                                     # 標的代碼
    direction: Direction
    candidates: list[Warrant] = field(default_factory=list)   # 通過硬過濾後
    raw_count: int = 0                                  # 原始抓到幾檔
    recommendations: dict[Profile, list[ScoredWarrant]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)      # 給使用者的提示
    degraded: bool = False                              # 是否所有 hard filter 都失敗
    fetch_source: str = ""                              # 實際使用的 fetcher 名稱
