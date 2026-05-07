// 模擬資料 — 台積電 2330 認購 60 天，目標 2800
window.WARRANT_DATA = (function () {
  const names = [
    ['08812P', '永豐2X 購03'], ['72174P', '凱基2H 購05'], ['09921P', '元大2J 購07'],
    ['74592P', '群益2A 購04'], ['08731P', '統一2K 購02'], ['09033P', '兆豐2N 購09'],
    ['74811P', '日盛2P 購01'], ['72356P', '富邦2X 購06'], ['08956P', '中信2H 購03'],
    ['09445P', '元富2C 購08'], ['74203P', '永豐2D 購04'], ['08623P', '凱基2L 購02'],
    ['72894P', '群益2M 購07'], ['09177P', '富邦2R 購05'], ['74628P', '元大2K 購09'],
    ['08344P', '兆豐2A 購03'], ['72591P', '統一2H 購06'], ['09782P', '中信2J 購01'],
    ['74416P', '凱基2X 購04'], ['08899P', '日盛2C 購08']
  ];

  const baseRet = [342.7, 287.4, 261.8, 248.3, 232.6, 218.9, 205.2, 198.6, 184.3, 178.9,
                   165.4, 158.7, 149.2, 142.6, 138.4, 132.1, 127.5, 119.8, 114.3, 108.6];

  const rows = names.map((n, i) => {
    const ret = baseRet[i];
    const px = (0.42 + Math.random() * 1.8).toFixed(2);
    const delta = (0.42 + Math.random() * 0.45).toFixed(3);
    const iv = (28 + Math.random() * 22).toFixed(1);
    const lev = (3.8 + Math.random() * 6.2).toFixed(2);
    const strike = (2350 + Math.random() * 380).toFixed(0);
    const ratio = (0.0015 + Math.random() * 0.008).toFixed(4);
    const moneyness = (((2310 - strike) / strike) * 100).toFixed(1);
    const days = Math.floor(78 + Math.random() * 90);
    const vol = Math.floor(120 + Math.random() * 4800);
    const be = (parseFloat(strike) + parseFloat(px) / parseFloat(ratio)).toFixed(0);
    const targetPx = (parseFloat(px) * (1 + ret / 100)).toFixed(2);
    const flatRet = (-22 - Math.random() * 38).toFixed(1);
    const d5 = (-45 - Math.random() * 30).toFixed(1);
    const d10 = (-68 - Math.random() * 25).toFixed(1);
    return {
      code: n[0], name: n[1], type: 'call',
      price: parseFloat(px), delta: parseFloat(delta), iv: parseFloat(iv),
      lev: parseFloat(lev), strike: parseFloat(strike), ratio: parseFloat(ratio),
      moneyness: parseFloat(moneyness), days, vol,
      be: parseFloat(be), targetPx: parseFloat(targetPx),
      ret, flatRet: parseFloat(flatRet), d5: parseFloat(d5), d10: parseFloat(d10)
    };
  });

  // candidates table — superset, more rows
  const candidates = [];
  for (let i = 0; i < 36; i++) {
    const cp = Math.random() > 0.25 ? 'call' : 'put';
    const px = (0.18 + Math.random() * 3.4).toFixed(2);
    const chg = (Math.random() * 0.24 - 0.10).toFixed(2);
    const chgPct = ((chg / px) * 100).toFixed(1);
    const vol = Math.floor(20 + Math.random() * 6800);
    const strike = (2100 + Math.random() * 800).toFixed(0);
    const ratio = (0.0010 + Math.random() * 0.012).toFixed(4);
    const days = Math.floor(35 + Math.random() * 240);
    const m = (((2310 - strike) / strike) * 100).toFixed(1);
    const spread = (0.5 + Math.random() * 7.5).toFixed(1);
    const lev = (1.8 + Math.random() * 8.5).toFixed(2);
    const iv = (24 + Math.random() * 28).toFixed(1);
    const delta = (0.22 + Math.random() * 0.65).toFixed(3);
    const out = (0.6 + Math.random() * 9.4).toFixed(1);
    const codes = ['087', '091', '721', '745', '728', '093', '097', '744'];
    const issuers = ['永豐', '凱基', '元大', '群益', '統一', '兆豐', '富邦', '中信', '日盛', '元富'];
    const code = codes[Math.floor(Math.random() * codes.length)] + Math.floor(10 + Math.random() * 90) + 'P';
    const issuer = issuers[Math.floor(Math.random() * issuers.length)];
    const month = '23456789'[Math.floor(Math.random() * 8)];
    const suffix = ('0' + Math.floor(Math.random() * 30)).slice(-2);
    candidates.push({
      code, name: `${issuer}2${month} ${cp === 'call' ? '購' : '售'}${suffix}`,
      type: cp,
      price: parseFloat(px), chg: parseFloat(chg), chgPct: parseFloat(chgPct),
      vol, strike: parseFloat(strike), ratio: parseFloat(ratio), days,
      moneyness: parseFloat(m), spread: parseFloat(spread), lev: parseFloat(lev),
      iv: parseFloat(iv), delta: parseFloat(delta), out: parseFloat(out)
    });
  }

  return { scenario: rows, candidates };
})();
