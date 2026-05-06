from twse_warrant.fetchers.csv_fetcher import CSVFetcher


CSV_SAMPLE = """權證代碼,權證名稱,認購售,成交價,漲跌,漲跌幅%,成交量,履約價,行使比例,剩餘天數,價內外,買賣價差比%,實質槓桿,成交價隱波%,流通在外比例%,Delta,Theta
081234,元大2330認購18,認購,3.50,0.10,2.95,500,1100,0.005,90,1.5,0.8,5.2,38.5,45.0,0.55,-0.005
081235,群益2330認售23,認售,2.80,-0.05,-1.75,300,1080,0.005,60,-2.0,1.2,7.0,42.0,55.0,-0.45,-0.008
"""


def test_csv_parses_basic():
    fetcher = CSVFetcher(CSV_SAMPLE)
    warrants = fetcher.fetch("2330")
    assert len(warrants) == 2
    w0 = warrants[0]
    assert w0.symbol == "081234"
    assert w0.direction == "call"
    assert w0.last_price == 3.5
    assert w0.iv_sell == 38.5
    assert w0.delta == 0.55


def test_csv_filters_by_direction():
    fetcher = CSVFetcher(CSV_SAMPLE)
    calls = fetcher.fetch("2330", direction="call")
    puts = fetcher.fetch("2330", direction="put")
    assert len(calls) == 1
    assert len(puts) == 1
    assert calls[0].direction == "call"
    assert puts[0].direction == "put"
