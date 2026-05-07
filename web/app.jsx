/* global React, ReactDOM, useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakToggle, TweakColor */
const { TopBar, PageHead, InputRow, KpiRow, TopCards, FilterStatus } = window.WAComponents;
const { ScenarioTable, CandidateTable, BSCalculator } = window.WAComponents2;
const { ScatterChart, DetailPanel, LogicExpander } = window.WAComponents3;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "density": "cozy",
  "heatmap": "strong",
  "showCandidates": true,
  "accent": "#ff5630"
}/*EDITMODE-END*/;

function App() {
  const [form, setForm] = React.useState({ topN: 5 });
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const data = window.WARRANT_DATA;

  // density
  React.useEffect(() => {
    const root = document.documentElement;
    if (t.density === 'compact') {
      root.style.setProperty('--row-pad', '6px 12px');
    } else if (t.density === 'comfortable') {
      root.style.setProperty('--row-pad', '12px 14px');
    } else {
      root.style.setProperty('--row-pad', '9px 12px');
    }
    document.body.dataset.density = t.density;
    document.body.dataset.heatmap = t.heatmap;
    root.style.setProperty('--accent', t.accent);
    root.style.setProperty('--accent-hover', t.accent);
  }, [t.density, t.heatmap, t.accent]);

  return (
    <div className="app">
      <TopBar />
      <main className="container">
        <PageHead />
        <InputRow form={form} setForm={setForm} />

        <div className="section">
          <KpiRow />
        </div>

        <FilterStatus />

        <div className="section">
          <div className="section-head">
            <div>
              <h2 className="section-title">
                🎯 情境模擬
                <span className="badge">2026-07-06 達 2,800 · 距今 60 日</span>
              </h2>
              <p className="section-sub">通過情境過濾的 78 檔，按達標報酬率排序。前 3 強顯示在卡片區。</p>
            </div>
          </div>

          <TopCards rows={data.scenario} />
        </div>

        <div className="section">
          <div className="section-head">
            <div>
              <h2 className="section-title">
                完整情境表
                <span className="badge">前 20 / 78 檔</span>
              </h2>
              <p className="section-sub">凍結左二欄；報酬欄位為熱力圖 — 越紅越強。</p>
            </div>
          </div>
          <ScenarioTable rows={data.scenario} />
        </div>

        <div className="section">
          <div className="section-head">
            <div>
              <h2 className="section-title">合理價計算機</h2>
              <p className="section-sub">Black-Scholes 推算合理價並對齊 tick；7 列敏感度表覆蓋 ±3× 步長。</p>
            </div>
          </div>
          <BSCalculator rows={data.scenario} />
        </div>

        {t.showCandidates && (
          <div className="section">
            <div className="section-head">
              <div>
                <h2 className="section-title">
                  🗂️ 候選清單
                  <span className="badge">通過硬過濾 239 檔</span>
                </h2>
                <p className="section-sub">未經情境過濾，全市場符合流動性與價差條件的候選池。</p>
              </div>
            </div>
            <CandidateTable rows={data.candidates} />
          </div>
        )}

        <div className="section">
          <div className="section-head">
            <div>
              <h2 className="section-title">📊 候選分佈</h2>
              <p className="section-sub">x 軸：IV %；y 軸：|等效Δ|；氣泡大小 = 成交量；顏色 = 槓桿（Viridis）。</p>
            </div>
          </div>
          <ScatterChart rows={data.candidates} />
        </div>

        <div className="section">
          <DetailPanel rows={data.candidates} />
        </div>

        <LogicExpander />

        <div className="footer">
          <span>台股權證分析 · 此頁為設計稿，數據為模擬</span>
          <span>v0.4 · 資料來源：元大 / Yuanta</span>
        </div>
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection label="顯示">
          <TweakRadio label="密度" value={t.density} options={['compact', 'cozy', 'comfortable']} onChange={v => setTweak('density', v)} />
          <TweakRadio label="熱力圖" value={t.heatmap} options={['subtle', 'strong', 'off']} onChange={v => setTweak('heatmap', v)} />
          <TweakToggle label="候選清單" value={t.showCandidates} onChange={v => setTweak('showCandidates', v)} />
        </TweakSection>
        <TweakSection label="主題">
          <TweakColor label="Accent" value={t.accent} options={['#ff5630', '#1d2540', '#d92d20', '#1849a9', '#7c3aed']} onChange={v => setTweak('accent', v)} />
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
